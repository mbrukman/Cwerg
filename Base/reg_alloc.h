#pragma once
// (c) Robert Muth - see LICENSE for more info

#include "Base/ir.h"
#include "Base/liveness.h"
#include "Base/opcode_gen.h"

#include <functional>
#include <vector>

namespace cwerg::base {

// PreAllocation track ranges where a register has been assigned and which
// must not change. It is usually used as a component inside RegPools.
class PreAllocation {
 public:
  PreAllocation() = default;

  void add(const LiveRange* lr);
  bool has_conflict(const LiveRange& lr);

 private:
  std::vector<const LiveRange*> ranges_;
  unsigned current_ = 0;
};

class RegPool {
 public:
  virtual CpuReg get_available_reg(const LiveRange& lr) = 0;

  virtual void give_back_available_reg(CpuReg reg) = 0;

  virtual int get_cpu_reg_family(DK dk) = 0;
};

using RegAllocLoggerFun =
    std::function<void(const LiveRange& lr, std::string_view msg)>;

extern void RegisterAssignerLinearScan(const std::vector<LiveRange*>& ordered,
                                       std::vector<LiveRange>* ranges,
                                       RegPool* pool,
                                       RegAllocLoggerFun debug = nullptr);

extern void RegisterAssignerLinearScanFancy(const std::vector<LiveRange*>& ordered,
                                            std::vector<LiveRange>* ranges,
                                            RegPool* pool,
                                            RegAllocLoggerFun debug = nullptr);

extern Stk RegCreateSpillSlot(Reg reg, Fun fun);

// assumes RegSpillSlot() has been initialized
extern void BblSpillRegs(Bbl bbl,
                         Fun fun,
                         DK offset_kind,
                         std::vector<Ins>* inss);

// * Clobbers RegSpillSlot(reg) - but will clear if with InvalidHandle
extern void FunSpillRegs(Fun fun,
                         DK offset_kind,
                         const std::vector<Reg>& regs,
                         std::vector<Ins>* inss);
}  // namespace cwerg::base
