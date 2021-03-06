// (c) Robert Muth - see LICENSE for more info

#include "CodeGenA32/codegen.h"

#include "Base/serialize.h"
#include "CodeGenA32/isel_gen.h"
#include "CodeGenA32/regs.h"
#include "CpuA32/disassembler.h"
#include "CpuA32/opcode_gen.h"
#include "Util/parse.h"

namespace cwerg::code_gen_a32 {

using namespace cwerg;
using namespace cwerg::base;

namespace {

void JtbCodeGen(Jtb jtb, std::ostream* output) {
  std::vector<Bbl> table(JtbSize(jtb), JtbDefBbl(jtb));
  for (Jen jen : JtbJenIter(jtb)) {
    table[JenPos(jen)] = JenBbl(jen);
  }
  *output << ".localmem " << Name(jtb) << " 4 rodata\n";
  for (Bbl bbl : table) {
    *output << "    .addr.bbl 4 " << Name(bbl) << "\n";
  }
  *output << ".endmem\n";
}

void FunCodeGenArm32(Fun fun, std::ostream* output) {
  *output << "# sig: IN: ";
  EmitParamList(FunNumInputTypes(fun), FunInputTypes(fun), output);
  *output << " -> OUT: ";
  EmitParamList(FunNumOutputTypes(fun), FunOutputTypes(fun), output);
  *output << "  stk_size:" << FunStackSize(fun) << "\n";
  *output << ".fun " << Name(fun) << " 16\n";
  for (Jtb jtb : FunJtbIter(fun)) {
    JtbCodeGen(jtb, output);
  }

  std::vector<a32::Ins> inss;
  auto drain = [&]() {
    char buffer[128];
    for (const auto& ins : inss) {
      a32::RenderInsSystematic(ins, buffer);
      *output << "    " << buffer << "\n";
    }
    inss.clear();
  };

  EmitContext ctx = FunComputeEmitContext(fun);
  EmitFunProlog(ctx, &inss);
  drain();
  for (Bbl bbl : FunBblIter(fun)) {
    *output << ".bbl " << Name(bbl) << " 4\n";
    for (Ins ins : BblInsIter(bbl)) {
      if (InsOPC(ins) == OPC::NOP1) {
        ctx.scratch_cpu_reg = RegCpuReg(Reg(InsOperand(ins, 0)));
      } else if (InsOPC(ins) == OPC::RET) {
        EmitFunEpilog(ctx, &inss);
      } else {
        const Pattern* pat = FindMatchingPattern(ins);
        ASSERT(pat != nullptr, "");
        for (unsigned i = 0; i < pat->length; ++i) {
          inss.push_back(MakeInsFromTmpl(pat->start[i], ins, ctx));
        }
      }
    }
    drain();
  }
  *output << ".endfun\n";
}

std::string_view MemKindToSectionName(MEM_KIND kind) {
  switch (kind) {
    case MEM_KIND::RO:
      return "rodata";
    case MEM_KIND::RW:
      return "data";
    default:
      ASSERT(false, "");
      return "";
  }
}

void MemCodeGenArm32(Mem mem, std::ostream* output) {
  *output << "# size " << MemSize(mem) << "\n"
          << ".mem " << Name(mem) << " " << MemAlignment(mem) << " "
          << MemKindToSectionName(MemKind(mem)) << "\n";
  for (Data data : MemDataIter(mem)) {
    uint32_t size = DataSize(data);
    Handle target = DataTarget(data);
    int32_t extra = DataExtra(data);
    if (target.kind() == RefKind::STR) {
      size_t len = size;
      char buffer[4096];
      if (len > 0) {
        len = BytesToEscapedString({StrData(Str(target)), len}, buffer);
      }
      buffer[len] = 0;
      *output << "    .data " << extra << " \"" << buffer << "\"\n";
    } else if (target.kind() == RefKind::FUN) {
      *output << "    .addr.fun " << size << " " << Name(Fun(target)) << "\n";
    } else {
      ASSERT(target.kind() == RefKind::MEM, "");
      *output << "    .addr.mem " << size << " " << Name(Mem(target))
              << std::hex << " 0x" << extra << std::dec << "\n";
    }
  }

  *output << ".endmem\n";
}

}  // namespace

void EmitUnitAsText(Unit unit, std::ostream* output) {
  for (Mem mem : UnitMemIter(unit)) {
    if (MemKind(mem) == MEM_KIND::EXTERN) continue;
    MemCodeGenArm32(mem, output);
  }
  for (Fun fun : UnitFunIter(unit)) {
    FunCodeGenArm32(fun, output);
  }
}

a32::Unit EmitUnitAsBinary(base::Unit unit, bool add_startup_code) {
  a32::Unit out;
  for (Mem mem : UnitMemIter(unit)) {
    if (MemKind(mem) == MEM_KIND::EXTERN) continue;
    out.MemStart(StrData(Name(mem)), MemAlignment(mem),
                 MemKindToSectionName(MemKind(mem)), false);
    for (Data data : MemDataIter(mem)) {
      uint32_t size = DataSize(data);
      Handle target = DataTarget(data);
      int32_t extra = DataExtra(data);
      if (target.kind() == RefKind::STR) {
        out.AddData(extra, StrData(Str(target)), size);
      } else if (target.kind() == RefKind::FUN) {
        out.AddFunAddr(size, StrData(Name(Fun(target))));
      } else {
        ASSERT(target.kind() == RefKind::MEM, "");
        out.AddMemAddr(size, StrData(Name(Mem(target))), extra);
      }
    }
    out.MemEnd();
  }

  std::vector<a32::Ins> inss;
  auto drain = [&]() {
    for (auto& ins : inss) {
      out.AddIns(&ins);
    }
    inss.clear();
  };

  for (Fun fun : UnitFunIter(unit)) {
    out.FunStart(StrData(Name(fun)), 16);
    for (Jtb jtb : FunJtbIter(fun)) {
      std::vector<Bbl> table(JtbSize(jtb), JtbDefBbl(jtb));
      for (Jen jen : JtbJenIter(jtb)) {
        table[JenPos(jen)] = JenBbl(jen);
      }
      out.MemStart(StrData(Name(jtb)), 4, "rodata", true);
      for (Bbl bbl : table) {
        out.AddBblAddr(4, StrData(Name(bbl)));
      }
      out.MemEnd();
    }
    EmitContext ctx = FunComputeEmitContext(fun);
    EmitFunProlog(ctx, &inss);
    drain();
    for (Bbl bbl : FunBblIter(fun)) {
      out.AddLabel(StrData(Name(bbl)), 4);
      for (Ins ins : BblInsIter(bbl)) {
        if (InsOPC(ins) == OPC::NOP1) {
          ctx.scratch_cpu_reg = RegCpuReg(Reg(InsOperand(ins, 0)));
        } else if (InsOPC(ins) == OPC::RET) {
          EmitFunEpilog(ctx, &inss);
        } else {
          const Pattern* pat = FindMatchingPattern(ins);
          ASSERT(pat != nullptr, "");
          for (unsigned i = 0; i < pat->length; ++i) {
            inss.push_back(MakeInsFromTmpl(pat->start[i], ins, ctx));
          }
        }
      }
      drain();
    }
    out.FunEnd();
  }
  out.AddLinkerDefs();
  if (add_startup_code) {
    out.AddStartupCode();
  }
  return out;
}

}  // namespace  cwerg::code_gen_a32
