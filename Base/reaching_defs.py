"""This file contains code for reaching definitions analysis
and optimization depending on it, e.g. constant propagation, etc."""

import dataclasses
from typing import Dict, Tuple, Any, Optional, List, Set

from Base import ir
from Base import opcode_tab as o
from Base import serialize


# ir.REG_DEF_MAP maps regs to location where it has been defined:
# * a missing entry indicates that the register has not been defined
# * an entry with value  ir.INS_INVALID indicated that we do not know
#   where the reg is defined
# * an entry with value of type ir.Ins indicated that the reg is defined
#   by the instruction pointed to
# * an entry with value of type ir.Bbl indicated that the reg is defined
#   by something "flowing" into that Bbl


def _BblComputeDefs(bbl: ir.Bbl) -> Tuple[ir.REG_DEF_MAP, Set[ir.Reg]]:
    defs: ir.REG_DEF_MAP = {}  # contains the latest definition of the given reg in the bbl
    uses = set()  # used contains uses flowing in from pred bbls
    for ins in bbl.inss:
        # if ins.opcode.is_call():
        #     callee: ir.Fun = cfg.InsCallee(ins)
        #     assert isinstance(callee, ir.Fun)
        #     for cpu_reg in callee.cpu_live_clobber:
        #         defs[cpu_reg] = ir.INS_INVALID
        #     for cpu_reg in callee.cpu_live_out:
        #         defs[cpu_reg] = ins
        num_defs = ins.opcode.def_ops_count()
        # we need reversed because we want to process the uses before the definitions
        for n, reg in reversed(list(enumerate(ins.operands))):
            if not isinstance(reg, ir.Reg): continue
            if n < num_defs:
                defs[reg] = ins
            else:
                if reg not in defs:
                    uses.add(reg)
    return defs, uses


@dataclasses.dataclass()
class ReachingDefs:
    defs_bbl: ir.REG_DEF_MAP
    defs_in: ir.REG_DEF_MAP = dataclasses.field(default_factory=dict)
    defs_out: ir.REG_DEF_MAP = dataclasses.field(default_factory=dict)


def _MergeReachingDefs(defs: ir.REG_DEF_MAP, other: ir.REG_DEF_MAP,
                       top) -> bool:
    change = False

    for k, v in other.items():
        if k not in defs:
            change = True
            defs[k] = v if v != ir.INS_INVALID else top
        else:
            v2 = defs[k]
            if v != v2:
                defs[k] = top
                change = True
    return change


def _BblPropagateDefs(bbl: ir.Bbl, defs_in: ir.REG_DEF_MAP):
    bbl.defs_in = {reg: ins for reg, ins in defs_in.items()
                   if ins is not ir.INS_INVALID}
    for ins in bbl.inss:
        # if ins.opcode.is_call():
        #     callee: ir.Fun = cfg.InsCallee(ins)
        #     assert isinstance(callee, ir.Fun)
        #     for cpu_reg in callee.cpu_live_clobber:
        #         defs_in[cpu_reg] = ir.INS_INVALID
        #     for cpu_reg in callee.cpu_live_out:
        #         defs_in[cpu_reg] = ins
        num_defs = ins.opcode.def_ops_count()
        # we need reversed because we want to process the uses before the definitions
        for n, reg in reversed(list(enumerate(ins.operands))):
            if not isinstance(reg, ir.Reg):
                ins.operand_defs[n] = ir.INS_INVALID
                continue
            if n < num_defs:
                defs_in[reg] = ins
                ins.operand_defs[n] = ir.INS_INVALID
            else:
                ins.operand_defs[n] = defs_in[reg]


def FunComputeReachingDefs(fun: ir.Fun):
    """
    Poor man's SSA we compute reaching defs at the Bbl beginning and
    for each operand use.

    This should be run after unreachable code has been removed/
    """
    # Step 1: Initialization
    all_defs: Dict[str, ReachingDefs] = {}
    all_uses = set()
    for bbl in fun.bbls:
        defs, uses = _BblComputeDefs(bbl)
        all_uses.update(uses)
        all_defs[bbl.name] = ReachingDefs(defs)

    first = fun.bbls[0]
    all_defs[first.name].defs_in = {r: first for r in all_uses}
    # Step 2: Fixpoint computation
    # Note, we look at the first bbl first
    active = list(reversed(fun.bbls))
    while active:
        bbl = active.pop(-1)
        defs: ReachingDefs = all_defs[bbl.name]
        new_out = defs.defs_in.copy()
        new_out.update(defs.defs_bbl)
        # dictionary comparison is element-wise
        if new_out == defs.defs_out:
            continue
        defs.defs_out = new_out
        for succ in bbl.edge_out:
            succ_in = all_defs[succ.name].defs_in
            change = _MergeReachingDefs(succ_in, new_out, succ)
            if change:
                active.append(succ)

    # Step 3: Make analysis results accessible
    for bbl in fun.bbls:
        _BblPropagateDefs(bbl, all_defs[bbl.name].defs_in.copy())


def FunCheckReachingDefs(fun: ir.Fun):
    for bbl in fun.bbls:
        for ins in bbl.inss:
            num_defs = ins.opcode.def_ops_count()
            for n, reg in enumerate(ins.operands):
                if n >= num_defs and isinstance(reg, ir.Reg):
                    assert isinstance(ins.operand_defs[n], (ir.Ins, ir.Bbl)), (
                        f"unexpected def in {ins} {ins.operands}  {ins.operand_defs}")
                else:
                    assert ins.operand_defs[n] == ir.INS_INVALID


def _InsPropagateConsts(ins: ir.Ins, _fun: ir.Fun):
    changes = 0
    for n, d in enumerate(ins.operand_defs):
        if d is ir.INS_INVALID or not isinstance(d,
                                                 ir.Ins) or d.opcode != o.MOV:
            continue
        value = d.operands[1]
        if not isinstance(value, ir.Const):
            continue
        ins.operands[n] = value
        ins.operand_defs[n] = ir.INS_INVALID
        changes += 1
    if changes == 0:
        return None
    else:
        return [ins]


def FunPropagateConsts(fun: ir.Fun) -> int:
    """Relies solely on the ins.operand_def info"""
    return ir.FunGenericRewrite(fun, _InsPropagateConsts)


def ConvertIntValue(kind_dst: o.DK, val: ir.Const) -> ir.Const:
    kind_src = val.kind
    width_dst = kind_dst.bitwidth()
    width_src = kind_src.bitwidth()
    # print ("@@@", kind_dst.name, width_dst, kind_src, width_src, num_kind, x)
    masked = val.value & ((1 << width_dst) - 1)
    if width_dst > width_src:
        if kind_dst.flavor() == kind_src.flavor() or kind_src.flavor() == o.DK_FLAVOR_U:
            return ir.Const(kind_dst, val.value)
        # kind_dst == RK_U, kind_src == RK_S
        return ir.Const(kind_dst, masked)
    elif kind_dst.flavor() == o.DK_FLAVOR_U:
        return ir.Const(kind_dst, masked)
    else:
        # kind_dst[0] == RK_S
        sign = val.value & (1 << (width_dst - 1))
        if sign == 0:
            return ir.Const(kind_dst, masked)
        return ir.Const(kind_dst, masked - (1 << width_dst))


# TODO: naive implementation -> needs a lot more scrutiny
_EVALUATORS_ALU = {
    o.ADD: lambda x, y: x + y,
    o.SUB: lambda x, y: x - y,
    o.MUL: lambda x, y: x * y,
    o.DIV: lambda x, y: x // y,
    o.SHL: lambda x, y: x << y,
    o.OR: lambda x, y: x | y,
    o.AND: lambda x, y: x & y,
    o.XOR: lambda x, y: x ^ y,
}

_EVALUATORS_COND_BRA = {
    o.BEQ: lambda x, y: x == y,
    o.BNE: lambda x, y: x != y,
    o.BLT: lambda x, y: x < y,
    o.BLE: lambda x, y: x <= y,
}


def _InsConstantFold(
        ins: ir.Ins, bbl: ir.Bbl, _fun: ir.Fun,
        allow_conv_conversion: bool) -> Optional[List[ir.Ins]]:
    """
    Try combining the constant from ins_def with the instruction in ins

    Return 1 iff a change was made

    Note: None of the transformations must change the def register - otherwise
    the reaching_defs will be stale
    """

    ops = ins.operands
    kind = ins.opcode.kind
    if kind is o.OPC_KIND.COND_BRA:
        if not isinstance(ops[0], ir.Const) or not isinstance(ops[1], ir.Const):
            return None
        # TODO: implement this, needs access to BBL for CFG changes
        evaluator = _EVALUATORS_COND_BRA.get(ins.opcode)
        assert evaluator, f"Evaluator NYI for: {ins} {ins.operands}"
        branch_taken = evaluator(ops[0].value, ops[1].value)
        target = ops[2]
        assert len(bbl.edge_out) == 2
        if branch_taken:
            succ_to_drop = bbl.edge_out[1] if bbl.edge_out[0] == target else \
                bbl.edge_out[0]
        else:
            succ_to_drop = target
        bbl.DelEdgeOut(succ_to_drop)
        return []
    elif kind is o.OPC_KIND.ALU1:
        if not isinstance(ops[1], ir.Const):
            return None
        assert False, f"Evaluator NYI for ALU1: {ins} {ins.operands}"

    elif kind is o.OPC_KIND.ALU:
        if not isinstance(ops[1], ir.Const) or not isinstance(ops[2], ir.Const):
            return None
        evaluator = _EVALUATORS_ALU.get(ins.opcode)
        assert evaluator, f"Evaluator NYI for: {ins} {ins.operands}"
        val = ir.Const(ops[1].kind, evaluator(ops[1].value, ops[2].value))
        ins.opcode = o.MOV
        ins.operands.pop(-1)
        ins.operands[1] = val
        ins.operand_defs.pop(-1)
        ins.operand_defs[1] = ir.INS_INVALID
        return [ins]
    elif ins.opcode is o.CONV:
        # TODO: this needs some  more thought generally but in
        # particular when we apply register widening
        # transformations, conv instructions end up being the only
        # ones with narrow width regs which simplifies
        # code generation. By allowing this to be converted into a
        # mov instruction we may leak the narrow register.
        if not allow_conv_conversion or not isinstance(ops[1], ir.Const):
            return None
        dst: ir.Reg = ops[0]
        src = ops[1]
        if not o.RegIsAddrInt(src.kind) or not o.RegIsAddrInt(dst.kind):
            return None
        new_val = ConvertIntValue(dst.kind, src)
        ins.Init(o.MOV, [dst, new_val])
        return [ins]
    else:
        return None


def FunConstantFold(fun: ir.Fun, allow_conv_conversion) -> int:
    """Relies solely on the ins.operand_def info"""
    return ir.FunGenericRewriteWithBbl(fun, _InsConstantFold,
                                       allow_conv_conversion=allow_conv_conversion)


def _CombinedOffset(ins: ir.Ins, base_ins: ir.Ins) -> Tuple[Any, Any]:
    """Returns the combine offset, where it was defined and its original type
     The second is relevant if the offset is a Reg and allows us
     to check that Reg's content is still available at the location
     using the combined offset.
     """
    off_pos = 1 if ins.opcode is o.ST else 2
    offset1 = ins.operands[off_pos]

    if base_ins.opcode is o.MOV:
        return offset1, ins.operand_defs[off_pos]
    if base_ins.opcode.kind != o.OPC_KIND.LEA:
        return None, None

    offset2 = base_ins.operands[2]

    if isinstance(offset1, ir.Const) and offset1.IsZero():
        return offset2, base_ins.operand_defs[2]
    if isinstance(offset2, ir.Const) and offset2.IsZero():
        return offset1, ins.operand_defs[off_pos]
    if isinstance(offset1, ir.Const) and isinstance(offset2, ir.Const):
        return ir.OffsetConst(offset1.value + offset2.value), None
    return None, None


_LOAD_STORE_BASE_REWRITE = {
    #  base         mem access ->  new mem access
    (o.LEA_MEM, o.LD): o.LD_MEM,
    (o.LEA_STK, o.LD): o.LD_STK,
    (o.LEA, o.LD): o.LD,
    (o.MOV, o.LD): o.LD,

    (o.LEA_MEM, o.ST): o.ST_MEM,
    (o.LEA_STK, o.ST): o.ST_STK,
    (o.LEA, o.ST): o.ST,
    (o.MOV, o.ST): o.ST,
    #
    (o.LEA_MEM, o.LEA): o.LEA_MEM,
    (o.LEA_STK, o.LEA): o.LEA_STK,
    (o.LEA, o.LEA): o.LEA,
    (o.MOV, o.LEA): o.LEA,
}


def _DefAvailable(op: Any, op_def: Any, defs: ir.REG_DEF_MAP) -> bool:
    if isinstance(op, (ir.Const, ir.Mem, ir.Stk)):
        return True
    assert isinstance(op, ir.Reg), f"unexpected operand {op}"
    if op_def is ir.INS_INVALID:
        return False
    return defs[op] == op_def


def _InsTryLoadStoreSimplify(ins: ir.Ins, defs: ir.REG_DEF_MAP) -> int:
    if ins.opcode not in {o.ST, o.LD, o.LEA}:
        return 0
    # do we have a suitable ins defining the base of the ld/st?
    base_pos = 0 if ins.opcode is o.ST else 1
    ins_base = ins.operand_defs[base_pos]

    if ins_base is ir.INS_INVALID or not isinstance(ins_base, ir.Ins):
        return 0

    new_opc = _LOAD_STORE_BASE_REWRITE.get((ins_base.opcode, ins.opcode))
    if new_opc is None:
        return 0
    # print ("")
    # print("#", serialize.InsRenderToAsm(ins))
    # print("#", serialize.InsRenderToAsm(ins_base))

    # is the original base still available at the ld/st
    base = ins_base.operands[1]
    base_def = ins_base.operand_defs[1]
    if not _DefAvailable(base, base_def, defs):
        # print ("#base not avail ", base, base_def)
        return 0

    # can the new offset be determined and is it available
    offset, offset_def = _CombinedOffset(ins, ins_base)
    if offset is None or not _DefAvailable(offset, offset_def, defs):
        return 0

    if base_pos == 0:  # store
        defs = [base_def, offset_def, ins.operand_defs[2]]
        ins.Init(new_opc, [base, offset, ins.operands[2]])
        ins.operand_defs = defs
    else:
        defs = [ins.operand_defs[0], base_def, offset_def]
        assert base_pos == 1
        ins.Init(new_opc, [ins.operands[0], base, offset])
        ins.operand_defs = defs
    # print("#>>>> ", serialize.InsRenderToAsm(ins))

    return 1


def _BblLoadStoreSimplify(bbl: ir.Bbl, _fun: ir.Fun) -> int:
    """

    Requires reaching definitions both per bbl and per ins
    """
    defs: ir.REG_DEF_MAP = bbl.defs_in.copy()
    count = 0
    for ins in bbl.inss:
        if ins.opcode in {o.ST, o.LD, o.LEA}:
            count += _InsTryLoadStoreSimplify(ins, defs)
        # if ins.opcode.is_call():
        #     callee: ir.Fun = cfg.InsCallee(ins)
        #     assert isinstance(callee, ir.Fun)
        #     for cpu_reg in callee.cpu_live_clobber:
        #         defs[cpu_reg] = ir.INS_INVALID
        #     for cpu_reg in callee.cpu_live_out:
        #         defs[cpu_reg] = ins
        num_defs = ins.opcode.def_ops_count()
        for n, reg in enumerate(ins.operands):
            if n < num_defs:
                assert isinstance(reg, ir.Reg)
                defs[reg] = ins
            else:
                break

    return count


def FunLoadStoreSimplify(fun: ir.Fun) -> int:
    return ir.FunGenericRewriteBbl(fun, _BblLoadStoreSimplify)


def _BblPropagateRegOperands(bbl: ir.Bbl, _fun: ir.Fun) -> int:
    """

    Requires reaching definitions both per bbl and per ins
    """
    defs: ir.REG_DEF_MAP = bbl.defs_in.copy()
    count = 0
    for ins in bbl.inss:
        for n, mov in enumerate(ins.operand_defs):
            if (mov is ir.INS_INVALID or not isinstance(mov, ir.Ins)
                    or mov.opcode is not o.MOV):
                continue
            src_reg = mov.operands[1]
            src_def = mov.operand_defs[1]
            # we do not want to extend live ranges for allocated regs
            if (not isinstance(src_reg, ir.Reg) or src_reg.cpu_reg or
                    defs[src_reg] != src_def):
                continue
            ins.operands[n] = src_reg
            ins.operand_defs[n] = src_def
            count += 1

        num_defs = ins.opcode.def_ops_count()
        for n, reg in enumerate(ins.operands):
            if n < num_defs:
                assert isinstance(reg, ir.Reg)
                defs[reg] = ins
            else:
                break

    return count


def FunPropagateRegs(fun: ir.Fun) -> int:
    """Relies solely on the ins.operand_def info"""
    return ir.FunGenericRewriteBbl(fun, _BblPropagateRegOperands)


def FunMoveElimination(fun: ir.Fun) -> int:
    """backwards move elimination"""
    count = 0
    for bbl in fun.bbls:
        for ins in bbl.inss:
            if ins.opcode is o.MOV and isinstance(ins.operands[1], ir.Reg):
                dst: ir.Reg = ins.operands[0]
                src: ir.Reg = ins.operands[1]
                if src.flags & ir.REG_FLAG.MULTI_DEF: continue
                if src.flags & ir.REG_FLAG.MULTI_READ: continue
                if src.flags & ir.REG_FLAG.LAC: continue

                src_def = ins.operand_defs[1]
                if src_def == ir.INS_INVALID: continue
                if not isinstance(src_def, ir.Ins): continue
                # print (f"@@BEFORE {ins} {ins.operands}")
                # print ("\n".join(serialize.BblRenderToAsm(bbl)))
                ins.operands[1] = dst  # This will be taken care of by nop removal
                # TODO: assumes at most one def per ins
                assert src_def.operands[0] == src
                src_def.operands[0] = dst
                # print ("@@AFTER")
                # print ("\n".join(serialize.BblRenderToAsm(bbl)))
                count += 1
                if count == 2: return count
    return count
