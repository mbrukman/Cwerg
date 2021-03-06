// (c) Robert Muth - see LICENSE for more info

#include "Base/ir.h"
#include "Util/assert.h"
#include "Util/immutable.h"
#include "Util/parse.h"

#include <cstring>

namespace cwerg::base {
// =======================================
// All Stripes
// =======================================

struct Stripe<EdgCore, Edg> gEdgCore("EdgCore");
StripeBase* const gAllStripesEdg[] = {&gEdgCore, nullptr};
struct StripeGroup gStripeGroupEdg("EDG", gAllStripesEdg, 64* 1024);

struct Stripe<InsCore, Ins> gInsCore("InsCore");
StripeBase* const gAllStripesIns[] = {&gInsCore, nullptr};
struct StripeGroup gStripeGroupIns("INS", gAllStripesIns, 256 * 1024);

struct Stripe<BblCore, Bbl> gBblCore("BblCore");
struct Stripe<BblBst, Bbl> gBblBst("BblBst");
struct Stripe<BblEdg, Bbl> gBblEdg("BblEdg");
struct Stripe<BblLiveness, Bbl> gBblLiveness("BblLiveness");
struct Stripe<BblReachingDefs, Bbl> gBblReachingDefs("BblDefs");

StripeBase* const gAllStripesBbl[] = {
    &gBblCore, &gBblBst, &gBblEdg, &gBblLiveness, &gBblReachingDefs, nullptr};
struct StripeGroup gStripeGroupBbl("BBL", gAllStripesBbl, 32  * 1024);

struct Stripe<FunCore, Fun> gFunCore("FunCore");
struct Stripe<FunBst, Fun> gFunBst("FunBst");
struct Stripe<FunSig, Fun> gFunSig("FunSig");
StripeBase* const gAllStripesFun[] = {&gFunCore, &gFunBst, &gFunSig, nullptr};
struct StripeGroup gStripeGroupFun("FUN", gAllStripesFun, 4 * 1024);

struct Stripe<UnitCore, Unit> gUnitCore("UnitCore");
StripeBase* const gAllStripesUnit[] = {&gUnitCore, nullptr};
struct StripeGroup gStripeGroupUnit("UNIT", gAllStripesUnit, 16);

struct Stripe<CpuRegCore, CpuReg> gCpuRegCore("CpuRegCore");
StripeBase* const gAllStripesCpuReg[] = {&gCpuRegCore, nullptr};
struct StripeGroup gStripeGroupCpuReg("CPU_REG", gAllStripesCpuReg, 512);

struct Stripe<RegCore, Reg> gRegCore("RegCore");
struct Stripe<RegBst, Reg> gRegBst("RegBst");
StripeBase* const gAllStripesReg[] = {&gRegBst, &gRegCore, nullptr};
struct StripeGroup gStripeGroupReg("REG", gAllStripesReg, 256 * 1024);

struct Stripe<StkCore, Stk> gStkCore("StkCore");
struct Stripe<StkBst, Stk> gStkBst("StkBst");
StripeBase* const gAllStripesStk[] = {&gStkCore, &gStkBst, nullptr};
struct StripeGroup gStripeGroupStk("STK", gAllStripesStk, 64 * 1024);

struct Stripe<JenBst, Jen> gJenBst("JenBst");
StripeBase* const gAllStripesJen[] = {&gJenBst, nullptr};
struct StripeGroup gStripeGroupJen("JEN", gAllStripesJen, 4 * 1024);

struct Stripe<JtbCore, Jtb> gJtbCore("JtbCore");
struct Stripe<JtbBst, Jtb> gJtbBst("JtbBst");
StripeBase* const gAllStripesJtb[] = {&gJtbCore, &gJtbBst, nullptr};
struct StripeGroup gStripeGroupJtb("JTB", gAllStripesJtb, 512);

struct Stripe<MemCore, Mem> gMemCore("MemCore");
struct Stripe<MemBst, Mem> gMemBst("MemBst");
StripeBase* const gAllStripesMem[] = {&gMemCore, &gMemBst, nullptr};
struct StripeGroup gStripeGroupMem("MEM", gAllStripesMem, 8 * 1024);

struct Stripe<DataCore, Data> gDataCore("DataCore");
StripeBase* const gAllStripesData[] = {&gDataCore, nullptr};
struct StripeGroup gStripeGroupData("DATA", gAllStripesData, 64 * 1024);

// =======================================
// Str Helpers
// =======================================

ImmutablePool StringPool(4);

Str StrNew(std::string_view s) {
  // we want a null byte at the end
  return Str(StringPool.Intern(s, 1));
}

const char* StrData(Str str) { return StringPool.Data(str.index()); }

int StrCmp(Str a, Str b) {
  if (a == b) return 0;
  return strcmp(StringPool.Data(a.index()), StringPool.Data(b.index()));
}

int StrCmpLt(Str a, Str b) {
  if (a == b) return 0;
  return strcmp(StringPool.Data(a.index()), StringPool.Data(b.index())) < 0;
}

// =======================================
// Const Helpers
// =======================================

// Note this struct is designed so that for a const of bytewidth x, we
// can take the first x bytes to get the concrete representation for the
// constant. Note, that this exploits little endianess
struct ConstCore {
  union {
    float val_f32;
    double val_f64;
    uint64_t val_u64;   // little endian byte order also make this suitable
    int64_t val_acs64;  // for smaller bitwidths
  };
  DK kind;
};

ImmutablePool ConstantPool(alignof(ConstCore));

bool ConstIsShort(Const num) { return int32_t(num.value) < 0; }

uint64_t ConstValueU(Const num) {
  if (ConstIsShort(num)) {
    return (num.value << 1) >> 17;
  }
  return ((ConstCore*)ConstantPool.Data(num.index()))->val_u64;
}

int64_t ConstValueACS(Const num) {
  if (ConstIsShort(num)) {
    // force sign extension
    return (int32_t(num.value << 1) >> 17);
  }
  return ((ConstCore*)ConstantPool.Data(num.index()))->val_acs64;
}

int32_t ConstValueInt32(Const num) {
  int32_t  val;
  switch (DKFlavor(ConstKind(num))) {
    case DK_FLAVOR_U:
      val = ConstValueU(num);
      ASSERT (val == ConstValueU(num), "out of range " << num);
      return val;
    case DK_FLAVOR_A:
    case DK_FLAVOR_C:
    case DK_FLAVOR_S:
        val = ConstValueACS(num);
      ASSERT (val == ConstValueACS(num), "out of range " << num);
      return val;
    default:
      ASSERT(false, "bad const " << num);
      return 0;
  }
}

double ConstValueF(Const num) {
  switch (ConstKind(num)) {
    case DK::F32:
      return ((ConstCore*)ConstantPool.Data(num.index()))->val_f32;
    case DK::F64:
      return ((ConstCore*)ConstantPool.Data(num.index()))->val_f64;
    default:
      ASSERT(false, "unexpected");
      return 0.0;
  }
}

DK ConstKind(Const num) {
  if (ConstIsShort(num)) {
    return DK(num.index() & 0xff);
  }
  return ((ConstCore*)ConstantPool.Data(num.index()))->kind;
}

Const ConstNewF(DK kind, double v) {
  ConstCore num;
  num.kind = kind;
  if (kind == DK::F32) {
    num.val_f32 = v;
  } else {
    ASSERT(kind == DK::F64, "");
    num.val_f64 = v;
  }
  return Const(ConstantPool.Intern({(char*)&num, sizeof(num)}));
}

Const ConstNewU(DK kind, uint64_t v) {
  if (v < 1 << 15) {
    return Const(Handle(1 << 23 | (v << 8) | uint32_t(kind), RefKind::CONST));
  }
  ConstCore num;
  num.kind = kind;
  num.val_u64 = v;
  return Const(ConstantPool.Intern({(char*)&num, sizeof(num)}));
}

Const ConstNewACS(DK kind, int64_t v) {
  if (-(1 << 14) <= v && v < (1 << 14)) {
    return Const(Handle(1 << 23 | (v << 8) | uint32_t(kind), RefKind::CONST));
  }
  ConstCore num;
  num.kind = kind;
  num.val_acs64 = v;
  return Const(ConstantPool.Intern({(char*)&num, sizeof(num)}));
}

Const ConstNewUint(uint64_t val) {
  if (val < (1LL << 8)) return ConstNewU(DK::U8, val);
  if (val < (1LL << 16)) return ConstNewU(DK::U16, val);
  if (val < (1LL << 32)) return ConstNewU(DK::U32, val);
  return ConstNewU(DK::U64, val);
}

Const ConstNewOffset(int64_t val) {
  if (val >= 0) {
    if (val < (1LL << 7)) return ConstNewACS(DK::S8, val);
    if (val < (1LL << 15)) return ConstNewACS(DK::S16, val);
    if (val < (1LL << 31)) return ConstNewACS(DK::S32, val);
    return ConstNewACS(DK::S64, val);
  } else {
    if (val >= -(1LL << 7)) return ConstNewACS(DK::S8, val);
    if (val >= -(1LL << 15)) return ConstNewACS(DK::S16, val);
    if (val >= -(1LL << 31)) return ConstNewACS(DK::S32, val);
    return ConstNewACS(DK::S64, val);
  }
}

Const ConstNewOffset(std::string_view v_str) {
  if (v_str[0] != '-') {
    return ConstNewUint(v_str);
  }
  // Must be negative
  auto val = ParseInt<int64_t>(v_str);
  ASSERT(val.has_value(), "");
  return ConstNewOffset(val.value());
}

Const ConstNewUint(std::string_view v_str) {
  auto val = ParseInt<uint64_t>(v_str);
  ASSERT(val.has_value(), "");
  return ConstNewUint(val.value());
}

Const ConstNew(DK kind, std::string_view v_str) {
  // std::cerr << "@@@ConstNew [" << RKToString(kind) <<  " " << v_str << "]\n";
  if (DKFlavor(kind) == DK_FLAVOR_F) {
    std::optional<double> val = ParseDouble(v_str);
    if (!val) return Const(0);
    return ConstNewF(kind, val.value());
  } else if (DKFlavor(kind) == DK_FLAVOR_U) {
    std::optional<uint64_t> val = ParseInt<uint64_t>(v_str);
    if (!val) return Const(0);
    return ConstNewU(kind, val.value());
  } else {
    std::optional<int64_t> val = ParseInt<int64_t>(v_str);
    if (!val) return Const(0);
    return ConstNewACS(kind, val.value());
  }
}

std::ostream& operator<<(std::ostream& os, Const num) {
  const DK kind = ConstKind(num);
  const int flavor = DKFlavor(kind);
  switch (flavor) {
    default:
      os << "InvalidConstFlavor";
      return os;
    case DK_FLAVOR_U:
      os << ConstValueU(num);
      return os;
    case DK_FLAVOR_F:
      os << ConstValueF(num);
      return os;
    case DK_FLAVOR_A:
    case DK_FLAVOR_C:
    case DK_FLAVOR_S:
      os << ConstValueACS(num);
      return os;
  }
}

bool ConstIsZero(Const num) {
  switch (ConstKind(num)) {
    default:
      ASSERT(false,
             "invalid zero test for Const " << EnumToString(ConstKind(num)));
      return false;
      //
    case DK::U8:
    case DK::U16:
    case DK::U32:
    case DK::U64:
      return ConstValueU(num) == 0;
    case DK::S8:
    case DK::S16:
    case DK::S32:
    case DK::S64:
      return ConstValueACS(num) == 0;
    case DK::F32:
    case DK::F64:
      return ConstValueF(num) == 0.0;
  }
}

bool ConstIsOne(Const num) {
  switch (ConstKind(num)) {
    default:
      ASSERT(false,
             "invalid zero test for Const " << EnumToString(ConstKind(num)));
      return false;
      //
    case DK::U8:
    case DK::U16:
    case DK::U32:
    case DK::U64:
      return ConstValueU(num) == 1;
    case DK::S8:
    case DK::S16:
    case DK::S32:
    case DK::S64:
      return ConstValueACS(num) == 1;

    case DK::F32:
    case DK::F64:
      return ConstValueF(num) == 1.0;
  }
}

std::string_view ConstToBytes(Const num) {
  ASSERT(!ConstIsShort(num), "NYI");
  const char* data = ConstantPool.Data(num.index());
  return std::string_view(data, DKBitWidth(ConstKind(num)) / 8);
}

// =======================================
// FunHelpers
// =======================================
std::string_view MaybeSkipCountPrefix(std::string_view s) {
  const char* cp = s.data();
  if (*cp == '$') {
    ++cp;
    while (*cp++ != '_')
      ;
  }
  return {cp, size_t(s.data() + s.size() - cp)};
}

Reg FunGetScratchReg(Fun fun,
                     DK kind,
                     std::string_view purpose,
                     bool add_kind_to_name) {
  ++gFunCore[fun].scratch_reg_id;
  char decbuf[32];
  auto dec = ToDecString(gFunCore[fun].scratch_reg_id, decbuf);
  ASSERT(purpose[0] != '$', "bad purpose " << purpose);

  char buf[kMaxIdLength];
  std::string_view name;
  if (add_kind_to_name) {
    name = StrCat(buf, sizeof(buf), "$", dec, "_", purpose, "_",
                  EnumToString(kind));
  } else {
    name = StrCat(buf, sizeof(buf), "$", dec, "_", purpose);
  }
  Str reg_name = StrNew(name);
  Reg reg = RegNew(kind, reg_name);
  FunRegAdd(fun, reg);
  return reg;
}

Reg FunFindOrAddCpuReg(Fun fun, CpuReg cpu_reg, DK kind) {
  char buf[kMaxIdLength];
  Str name = StrNew(StrCat(buf, sizeof(buf), "$", StrData(Name(cpu_reg)), "_",
                           EnumToString(kind)));
  Reg reg = FunRegFind(fun, name);
  if (reg.isnull()) {
    reg = RegNew(kind, name, cpu_reg);
    FunRegAdd(fun, reg);
  }
  return reg;
}

Bbl FunBblFindOrForwardDeclare(Fun fun, Str bbl_name) {
  Bbl bbl = FunBblFind(fun, bbl_name);
  if (bbl.isnull()) {
    bbl = BblNew(bbl_name);
    FunBblAdd(fun, bbl);  // We intentionally to do call FunBblAppend() here
  }
  return bbl;
}

void FunFinalizeStackSlots(Fun fun) {
  uint32_t slot = 0;
  for (Stk stk : FunStkIter(fun)) {
    auto align = StkAlignment(stk);
    slot += align - 1;
    slot = slot / align * align;
    StkSlot(stk) = slot;
    slot += StkSize(stk);
  }
  FunStackSize(fun) = slot;
}

// =======================================
// UnitHelpers
// =======================================

Str StrNewMemConstName(std::string_view data, DK kind) {
  ASSERT(data.size() < 32, "");
  char hexbuf[32 * 3];
  auto hex = ToHexDataStringWithSep(data, '_', hexbuf, sizeof(hexbuf));
  char buf[kMaxIdLength];
  return StrNew(
      StrCat(buf, sizeof(buf), "$const_", EnumToString(kind), "_", hex));
}

Mem UnitFindOrAddConstMem(Unit unit, Const num) {
  std::string_view data = ConstToBytes(num);
  Str name = StrNewMemConstName(data, ConstKind(num));
  Mem mem = UnitMemFind(unit, name);
  if (mem.isnull()) {
    mem = MemNew(MEM_KIND::RO, data.size(), name);
    MemDataAppend(mem, DataNew(StrNew(data), data.size(), 1));
    UnitMemAdd(unit, mem);
    UnitMemAppend(unit, mem);
  }
  return mem;
}

}  // namespace cwerg::base
