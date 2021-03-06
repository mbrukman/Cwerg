#pragma once
// (c) Robert Muth - see LICENSE for more info

#include "Base/ir.h"

#include <functional>

namespace cwerg::base {


// maps one DK to another - used for simplifying register allocation
using DK_MAP = std::array<DK, 256>;

// reg count per DK
using DK_COUNTS = std::array<uint16_t , 256>;

struct DK_LAC_COUNTS {
  DK_COUNTS lac = DK_COUNTS();       // force zero  initialization
  DK_COUNTS not_lac = DK_COUNTS();
};

extern DK_LAC_COUNTS FunComputeBblRegUsageStats(Fun fun, const DK_MAP& rk_map);

extern std::ostream& operator<<(std::ostream& os,
                                const DK_LAC_COUNTS& usage);

extern void FunComputeRegStatsExceptLAC(Fun fun);

extern void FunComputeRegStatsLAC(Fun fun);

extern int FunDropUnreferencedRegs(Fun fun);

struct FunRegStats {
  int32_t global_lac = 0;
  int32_t global_not_lac = 0;
  int32_t local_lac = 0;
  int32_t local_not_lac = 0;
};

extern FunRegStats FunCalculateRegStats(Fun fun);

std::ostream& operator<<(std::ostream& os, const FunRegStats& stats);

extern int FunSeparateLocalRegUsage(Fun fun);

}  // namespace cwerg::base
