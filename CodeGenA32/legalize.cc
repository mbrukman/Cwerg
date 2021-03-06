// (c) Robert Muth - see LICENSE for more info

#include "Base/canonicalize.h"
#include "Base/cfg.h"
#include "Base/liveness.h"
#include "Base/lowering.h"
#include "Base/optimize.h"
#include "Base/reg_alloc.h"
#include "Base/serialize.h"
#include "CodeGenA32/isel_gen.h"
#include "CodeGenA32/regs.h"

#include <algorithm>
#include <iomanip>

namespace cwerg::code_gen_a32 {
namespace {

using namespace cwerg;
using namespace cwerg::base;

// +-prefix converts an enum the underlying integer type
template <typename T>
constexpr auto operator+(T e) noexcept
    -> std::enable_if_t<std::is_enum<T>::value, std::underlying_type_t<T>> {
  return static_cast<std::underlying_type_t<T>>(e);
}

bool InsRequiresSpecialHandling(Ins ins) {
  const OPC opc = InsOPC(ins);
  return opc == OPC::ST_STK ||   // we compute stack offsets in a separate pass
         opc == OPC::LD_STK ||   // ditto
         opc == OPC::LEA_STK ||  // ditto
         opc == OPC::POPARG ||   // will be rewritten later
         opc == OPC::PUSHARG ||  // ditto
         opc == OPC::RET ||      // handled via special epilog code
         opc == OPC::NOP1;       // pseudo instruction
}

void FunAddNop1ForCodeSel(Fun fun, std::vector<Ins>* inss) {
  for (Bbl bbl : FunBblIter(fun)) {
    inss->clear();
    bool dirty = false;
    Reg tmp;
    for (Ins ins : BblInsIter(bbl)) {
      switch (InsOPC(ins)) {
        case OPC::SWITCH:
          tmp = FunGetScratchReg(fun, DK::C32, "switch", false);
          inss->push_back(InsNew(OPC::NOP1, tmp));
          inss->push_back(ins);
          dirty = true;
          break;

        case OPC::CONV:
          if (InsOperand(ins, 1).kind() == RefKind::REG) {
            DK src_kind = RegKind(Reg(InsOperand(ins, 1)));
            int src_fl = DKFlavor(src_kind);
            DK dst_kind = RegKind(Reg(InsOperand(ins, 0)));
            int dst_fl = DKFlavor(dst_kind);
            if (src_fl == DK_FLAVOR_F &&
                (dst_fl == DK_FLAVOR_S || dst_fl == DK_FLAVOR_U)) {
              tmp = FunGetScratchReg(fun, DK::F32, "ftoi", false);
              inss->push_back(InsNew(OPC::NOP1, tmp));
              inss->push_back(ins);
              dirty = true;
              break;
            } else if ((src_fl == DK_FLAVOR_S || src_fl == DK_FLAVOR_U) &&
                       dst_kind == DK::F64) {
              tmp = FunGetScratchReg(fun, DK::F32, "itof", false);
              inss->push_back(InsNew(OPC::NOP1, tmp));
              inss->push_back(ins);
              dirty = true;
              break;
            }
          }
          // fallthrough
        default:
          inss->push_back(ins);
          break;
      }
    }
    if (dirty) BblReplaceInss(bbl, *inss);
  }
}

void FunRewriteOutOfBoundsImmediates(Fun fun, std::vector<Ins>* inss) {
  for (Bbl bbl : FunBblIter(fun)) {
    inss->clear();
    bool dirty = false;
    for (Ins ins : BblInsIter(bbl)) {
      if (!InsRequiresSpecialHandling(ins)) {
        const uint8_t mismatches =
            code_gen_a32::FindtImmediateMismatchesInBestMatchPattern(ins);
        if (mismatches != 0) {
          ASSERT(mismatches != code_gen_a32::MATCH_IMPOSSIBLE,
                 "cannot match: " << ins);
          for (unsigned pos = 0; pos < a32::MAX_OPERANDS; ++pos) {
            if (mismatches & (1 << pos)) {
              inss->push_back(InsEliminateImmediate(ins, pos, fun));
              dirty = true;
            }
          }
        }
      }
      inss->push_back(ins);
    }
    if (dirty) BblReplaceInss(bbl, *inss);
  }
}

void FunPushargConversion(Fun fun) {
  std::vector<CpuReg> parameter;
  for (Bbl bbl : FunBblIter(fun)) {
    for (Ins ins : BblInsIterReverse(bbl)) {
      if (InsOPC(ins) == OPC::PUSHARG) {
        ASSERT(!parameter.empty(), "possible undefined fun call in " << Name(fun));
        Handle src = InsOperand(ins, 0);
        CpuReg cpu_reg = parameter.back();
        parameter.pop_back();
        Reg reg = FunFindOrAddCpuReg(fun, cpu_reg, RegOrConstKind(src));
        InsInit(ins, OPC::MOV, reg, src);
        continue;
      }

      if (InsOpcode(ins).IsCall()) {
        Fun callee = InsCallee(ins);
        parameter = GetCpuRegsForSignature(FunNumInputTypes(callee),
                                           FunInputTypes(callee));
        std::reverse(parameter.begin(), parameter.end());
      } else if (InsOPC(ins) == OPC::RET) {
        parameter =
            GetCpuRegsForSignature(FunNumOutputTypes(fun), FunOutputTypes(fun));
        std::reverse(parameter.begin(), parameter.end());
      }
    }
  }
}

void FunPopargConversion(Fun fun) {
  std::vector<CpuReg> parameter =
      GetCpuRegsForSignature(FunNumInputTypes(fun), FunInputTypes(fun));
  std::reverse(parameter.begin(), parameter.end());
  for (Bbl bbl : FunBblIter(fun)) {
    for (Ins ins : BblInsIter(bbl)) {
      if (InsOPC(ins) == OPC::POPARG) {
        ASSERT(!parameter.empty(), "");
        Reg dst = Reg(InsOperand(ins, 0));
        CpuReg cpu_reg = parameter.back();
        parameter.pop_back();
        Reg reg = FunFindOrAddCpuReg(fun, cpu_reg, RegKind(dst));
        InsInit(ins, OPC::MOV, dst, reg);
        continue;
      }

      if (InsOpcode(ins).IsCall()) {
        Fun callee = InsCallee(ins);
        parameter = GetCpuRegsForSignature(FunNumOutputTypes(callee),
                                           FunOutputTypes(callee));
        std::reverse(parameter.begin(), parameter.end());
      }
    }
  }
}

DK_LAC_COUNTS FunGlobalRegStats(Fun fun, const DK_MAP& rk_map) {
  DK_LAC_COUNTS out;
  for (Reg reg : FunRegIter(fun)) {
    if (!RegCpuReg(reg).isnull() || !RegHasFlag(reg, REG_FLAG::GLOBAL)) {
      continue;
    }
    DK rk = rk_map[+RegKind(reg)];
    ASSERT(rk != DK::INVALID, "");
    if (RegHasFlag(reg, REG_FLAG::LAC))
      ++out.lac[+rk];
    else
      ++out.not_lac[+rk];
  }
  return out;
}

void FunRewriteOutOfBoundsOffsetsStk(Fun fun, std::vector<Ins>* inss) {
  Const zero_offset = ConstNewU(DK::U32, 0);
  for (Bbl bbl : FunBblIter(fun)) {
    inss->clear();
    bool dirty = false;
    for (Ins ins : BblInsIter(bbl)) {
      OPC opc = InsOPC(ins);
      if (opc != OPC::ST_STK && opc != OPC::LD_STK) {
        inss->push_back(ins);
        continue;
      }
      const uint8_t mismatches =
          code_gen_a32::FindtImmediateMismatchesInBestMatchPattern(ins);
      ASSERT(mismatches != code_gen_a32::MATCH_IMPOSSIBLE,
             "cannot match: " << ins);
      if (mismatches == 0) {
        inss->push_back(ins);
        continue;
      }
      dirty = true;
      Reg tmp = FunGetScratchReg(fun, DK::A32, "imm_stk", false);
      if (opc == OPC::ST_STK) {
        ASSERT(mismatches == (1 << 1), "");
        Handle st_offset = InsOperand(ins, 1);
        Handle lea_offset = zero_offset;
        if (st_offset.kind() == RefKind::CONST) {
          std::swap(st_offset, lea_offset);
        }
        inss->push_back(
            InsNew(OPC::LEA_STK, tmp, InsOperand(ins, 0), lea_offset));
        InsInit(ins, OPC::ST, tmp, st_offset, InsOperand(ins, 2));
      } else {
        ASSERT(opc == OPC::LD_STK, "");
        ASSERT(mismatches == (1 << 2), "");
        Handle ld_offset = InsOperand(ins, 2);
        Handle lea_offset = zero_offset;
        if (ld_offset.kind() == RefKind::CONST) {
          std::swap(ld_offset, lea_offset);
        }
        inss->push_back(
            InsNew(OPC::LEA_STK, tmp, InsOperand(ins, 1), lea_offset));
        InsInit(ins, OPC::LD, InsOperand(ins, 0), tmp, ld_offset);
      }
      inss->push_back(ins);
    }

    if (dirty) BblReplaceInss(bbl, *inss);
  }
}

int FunMoveEliminationCpu(Fun fun, std::vector<Ins>* to_delete) {
  to_delete->clear();

  for (Bbl bbl : FunBblIter(fun)) {
    for (Ins ins : BblInsIter(bbl)) {
      OPC opc = InsOPC(ins);
      if (opc == OPC::MOV) {
        Reg dst(InsOperand(ins, 0));
        Reg src(InsOperand(ins, 1));
        if (src.kind() == RefKind::REG && RegCpuReg(src) == RegCpuReg(dst)) {
          to_delete->push_back(ins);
        }
      }
    }
  }

  for (Ins ins : *to_delete) {
    BblInsUnlink(ins);
    InsDel(ins);
  }
  return to_delete->size();
}

void FunSetInOutCpuRegs(Fun fun) {
  const std::vector<CpuReg> cpu_in =
      GetCpuRegsForSignature(FunNumInputTypes(fun), FunInputTypes(fun));
  FunNumCpuLiveIn(fun) = cpu_in.size();
  memcpy(FunCpuLiveIn(fun), cpu_in.data(), cpu_in.size() * sizeof(CpuReg));

  const std::vector<CpuReg> cpu_out =
      GetCpuRegsForSignature(FunNumOutputTypes(fun), FunOutputTypes(fun));
  FunNumCpuLiveOut(fun) = cpu_out.size();
  memcpy(FunCpuLiveOut(fun), cpu_out.data(), cpu_out.size() * sizeof(CpuReg));
}

constexpr DK A32RKMapping(uint8_t i) {
  const DK rk = DK(i);
  if (rk == DK::S8 || rk == DK::S16 || rk == DK::S32 || rk == DK::A32 ||
      rk == DK::U8 || rk == DK::U16 || rk == DK::U32 || rk == DK::C32) {
    return DK::S32;
  } else if (rk == DK::F32 || rk == DK::F64) {
    return rk;
  } else {
    return DK::INVALID;
  }
}

// based on:
// https://stackoverflow.com/questions/19019252/create-n-element-constexpr-array-in-c11
template <class Function, std::size_t... Indices>
constexpr auto make_array_helper(Function f, std::index_sequence<Indices...>)
    -> std::array<typename std::result_of<Function(std::size_t)>::type,
                  sizeof...(Indices)> {
  return {{f(Indices)...}};
}

// template magic above is so that we can compute this at compile time:
const DK_MAP kA32RKMap =
    make_array_helper(A32RKMapping, std::make_index_sequence<256>{});

void FunFilterGlobalRegs(Fun fun,
                         DK rk,
                         bool is_lac,
                         const DK_MAP& rk_map,
                         std::vector<Reg>* out) {
  for (Reg reg : FunRegIter(fun)) {
    if (RegHasFlag(reg, REG_FLAG::GLOBAL) && RegCpuReg(reg).isnull() &&
        RegHasFlag(reg, REG_FLAG::LAC) == is_lac &&
        rk_map[+RegKind(reg)] == rk) {
      out->push_back(reg);
    }
  }
}

bool SpillingNeeded(const FunRegStats& needed,
                    unsigned num_regs_lac,
                    unsigned num_regs_not_lac) {
  return needed.global_lac + needed.local_lac > num_regs_lac ||
         needed.global_lac + needed.local_lac + needed.global_not_lac +
                 needed.local_not_lac >
             num_regs_lac + num_regs_not_lac;
}

// This assumes that at least count bits are set.
uint32_t FindMaskCoveringTheLowOrderSetBits(uint32_t bits, unsigned count) {
  if (count == 0) return 0;
  uint32_t mask = 1;
  unsigned n = 0;
  while (n < count) {
    if ((mask & bits) != 0) ++n;
    mask <<= 1;
  }
  return mask - 1;
}

std::pair<uint32_t, uint32_t> GetRegPoolsForGlobals(
    const FunRegStats& needed,
    uint32_t regs_lac,
    uint32_t regs_not_lac,
    uint32_t regs_preallocated) {
  unsigned num_regs_lac = __builtin_popcount(regs_lac);
  unsigned num_regs_not_lac = __builtin_popcount(regs_not_lac);
  bool spilling_needed = SpillingNeeded(needed, num_regs_lac, num_regs_not_lac);

  uint32_t global_lac = regs_lac;
  uint32_t local_lac = 0;
  if (num_regs_lac > needed.global_lac) {
    const uint32_t mask =
        FindMaskCoveringTheLowOrderSetBits(global_lac, needed.global_lac);
    local_lac = global_lac & ~mask;
    global_lac = global_lac & mask;
  }

  uint32_t global_not_lac = 0;
  if (num_regs_not_lac > needed.local_not_lac) {
    const uint32_t mask = FindMaskCoveringTheLowOrderSetBits(
        regs_not_lac, needed.local_not_lac + spilling_needed);
    global_not_lac = regs_not_lac & ~(mask | regs_preallocated);
  }

  if (__builtin_popcount(local_lac) > needed.local_lac) {
    const uint32_t mask =
        FindMaskCoveringTheLowOrderSetBits(local_lac, needed.local_lac);
    global_not_lac |= local_lac & ~mask;
  }
  return std::make_pair(global_lac, global_not_lac);
}

std::pair<uint32_t, uint32_t> FunGetPreallocatedCpuRegs(Fun fun) {
  uint32_t gpr_mask = 0;
  uint32_t flt_mask = 0;
  for (Reg reg : FunRegIter(fun)) {
    CpuReg cpu_reg = RegCpuReg(reg);
    if (cpu_reg.isnull()) continue;
    if (DKFlavor(RegKind(reg)) == DK_FLAVOR_F) {
      flt_mask |= A32RegToAllocMask(cpu_reg);
    } else {
      gpr_mask |= A32RegToAllocMask(cpu_reg);
    }
  }
  return std::make_pair(gpr_mask, flt_mask);
}

}  // namespace

void PhaseLegalization(Fun fun, Unit unit, std::ostream* fout) {
  std::vector<Ins> inss;
  FunRegWidthWidening(fun, DK::U8, DK::U32, &inss);
  FunRegWidthWidening(fun, DK::S8, DK::S32, &inss);
  FunRegWidthWidening(fun, DK::U16, DK::U32, &inss);
  FunRegWidthWidening(fun, DK::S16, DK::S32, &inss);

  FunSetInOutCpuRegs(fun);

  if (FunKind(fun) != FUN_KIND::NORMAL) return;

  FunEliminateRem(fun, &inss);

  FunEliminateStkLoadStoreWithRegOffset(fun, DK::A32, DK::S32, &inss);
  FunMoveImmediatesToMemory(fun, unit, DK::F32, DK::U32, &inss);
  FunMoveImmediatesToMemory(fun, unit, DK::F64, DK::U32, &inss);
  FunEliminateMemLoadStore(fun, DK::A32, DK::S32, &inss);

  FunCanonicalize(fun);
  // We need to run this before massaging immediates because it changes
  // COND_RRA instruction possibly with immediates.
  FunCfgExit(fun);

  FunEliminateImmediateStores(fun, &inss);
  FunRewriteOutOfBoundsImmediates(fun, &inss);

  FunAddNop1ForCodeSel(fun, &inss);
}

void DumpRegStats(Fun fun, const DK_LAC_COUNTS& stats, std::ostream* output) {
  unsigned local_lac = 0;
  unsigned local_not_lac = 0;
  for (size_t i = 0; i < stats.lac.size(); ++i) {
    local_lac += stats.lac[i];
    local_not_lac += stats.not_lac[i];
  }
  std::vector<Reg> global_lac;
  std::vector<Reg> global_not_lac;
  std::vector<Reg> allocated_lac;
  std::vector<Reg> allocated_not_lac;
  for (Reg reg : FunRegIter(fun)) {
    if (!RegHasFlag(reg, REG_FLAG::GLOBAL)) continue;
    if (RegCpuReg(reg).isnull()) {
      if (RegHasFlag(reg, REG_FLAG::LAC))
        global_lac.push_back(reg);
      else
        global_not_lac.push_back(reg);
    } else {
      if (RegHasFlag(reg, REG_FLAG::LAC))
        allocated_lac.push_back(reg);
      else
        allocated_not_lac.push_back(reg);
    }
  }
  if (output != nullptr) {
    *output << "# REGSTATS " << std::left << std::setw(20) << Name(fun)
            << std::right
            << "   "
            //
            << "all: " << std::setw(2) << allocated_lac.size() << " "
            << std::setw(2) << allocated_not_lac.size()
            << "  "
            //
            << "glo: " << std::setw(2) << global_lac.size() << " "
            << std::setw(2) << global_not_lac.size()
            << "  "
            //
            << "loc: " << std::setw(2) << local_lac << " " << std::setw(2)
            << local_not_lac << "\n";
  }
}

void PhaseGlobalRegAlloc(Fun fun, Unit unit, std::ostream* fout) {
  if (fout != nullptr) {
    *fout << "############################################################\n"
          << "# GlobalRegAlloc " << Name(fun) << "\n"
          << "############################################################\n";
  }
  std::vector<Ins> inss;

  FunPushargConversion(fun);
  FunPopargConversion(fun);
  //
  FunComputeRegStatsExceptLAC(fun);
  FunDropUnreferencedRegs(fun);
  FunNumberReg(fun);
  FunComputeLivenessInfo(fun);
  FunComputeRegStatsLAC(fun);
  const DK_LAC_COUNTS local_reg_stats =
      FunComputeBblRegUsageStats(fun, kA32RKMap);
  const DK_LAC_COUNTS global_reg_stats = FunGlobalRegStats(fun, kA32RKMap);
  if (fout != nullptr) {
    DumpRegStats(fun, local_reg_stats, fout);
  }

  const auto [prealloc_gpr, prealloc_flt] = FunGetPreallocatedCpuRegs(fun);

  std::vector<Reg> to_be_spilled;
  std::vector<Reg> regs;
  auto reg_cmp = [](Reg a, Reg b) -> bool {
    return StrCmpLt(Name(a), Name(b));
  };

  {
    // GPR
    const FunRegStats needed_gpr{global_reg_stats.lac[+DK::S32],      //
                                 global_reg_stats.not_lac[+DK::S32],  //
                                 local_reg_stats.lac[+DK::S32],       //
                                 1 + local_reg_stats.not_lac[+DK::S32]};

    //*fout << "@@ GPR NEEDED " << needed_gpr.global_lac << " "
    //      << needed_gpr.global_not_lac << " " << needed_gpr.local_lac << " "
    //     << needed_gpr.local_not_lac << "\n";

    // const RegPools pools_gpr = FunComputeArmRegPoolsGPR(needed_gpr);
    const auto [global_lac, global_not_lac] =
        GetRegPoolsForGlobals(needed_gpr, GPR_CALLEE_SAVE_REGS_MASK,
                              GPR_NOT_LAC_REGS_MASK, prealloc_gpr);
    //*fout << "@@ GPR POOL " << std::hex << global_lac << " " << global_not_lac
    //      << "\n";

    regs.clear();
    FunFilterGlobalRegs(fun, DK::S32, true, kA32RKMap, &regs);
    std::sort(regs.begin(), regs.end(), reg_cmp);  // make things deterministic
    AssignCpuRegOrMarkForSpilling(regs, global_lac, 0, &to_be_spilled);
    regs.clear();
    FunFilterGlobalRegs(fun, DK::S32, false, kA32RKMap, &regs);
    std::sort(regs.begin(), regs.end(), reg_cmp);  // make things deterministic
    AssignCpuRegOrMarkForSpilling(regs, global_not_lac & GPR_NOT_LAC_REGS_MASK,
                                  global_not_lac & GPR_CALLEE_SAVE_REGS_MASK,
                                  &to_be_spilled);
  }
  {
    // FLT + DBL
    const FunRegStats needed_flt{
        global_reg_stats.lac[+DK::F32] + 2 * global_reg_stats.lac[+DK::F64],
        global_reg_stats.not_lac[+DK::F32] +
            2 * global_reg_stats.not_lac[+DK::F64],
        local_reg_stats.lac[+DK::F32] + 2 * local_reg_stats.lac[+DK::F64],
        2 + local_reg_stats.not_lac[+DK::F32] +
            2 * local_reg_stats.not_lac[+DK::F64]};

    const auto [global_lac, global_not_lac] =
        GetRegPoolsForGlobals(needed_flt, FLT_CALLEE_SAVE_REGS_MASK,
                              FLT_PARAM_REGS_REGS_MASK, prealloc_flt);
    regs.clear();
    FunFilterGlobalRegs(fun, DK::F64, true, kA32RKMap, &regs);
    FunFilterGlobalRegs(fun, DK::F32, true, kA32RKMap, &regs);
    std::sort(regs.begin(), regs.end(), reg_cmp);  // make things deterministic
    AssignCpuRegOrMarkForSpilling(regs, global_lac, 0, &to_be_spilled);
    regs.clear();
    FunFilterGlobalRegs(fun, DK::F64, false, kA32RKMap, &regs);
    FunFilterGlobalRegs(fun, DK::F32, false, kA32RKMap, &regs);
    std::sort(regs.begin(), regs.end(), reg_cmp);  // make things deterministic
    AssignCpuRegOrMarkForSpilling(regs, global_not_lac, 0, &to_be_spilled);
  }

  FunSpillRegs(fun, DK::U32, to_be_spilled, &inss);
  FunComputeRegStatsExceptLAC(fun);
  FunDropUnreferencedRegs(fun);
  FunNumberReg(fun);
  FunComputeLivenessInfo(fun);
  FunComputeRegStatsLAC(fun);
}

void PhaseFinalizeStackAndLocalRegAlloc(Fun fun,
                                        Unit unit,
                                        std::ostream* fout) {
  std::vector<Ins> inss;
  if (false) {
    std::vector<Reg> to_be_spilled;
    for (Reg reg : FunRegIter(fun)) {
      if (RegCpuReg(reg).isnull()) to_be_spilled.push_back(reg);
    }
    FunSpillRegs(fun, DK::U32, to_be_spilled, &inss);
  }
  FunFinalizeStackSlots(fun);
  FunRewriteOutOfBoundsOffsetsStk(fun, &inss);
  FunLocalRegAlloc(fun, &inss);
  FunMoveEliminationCpu(fun, &inss);
  FunFinalizeStackSlots(fun);
}

}  // namespace  cwerg::code_gen_a32
