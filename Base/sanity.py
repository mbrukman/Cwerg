"""This file contains integrity checking code for the IR"""
from typing import Optional, List

from Base import cfg
from Base import ir
from Base import opcode_tab as o


class ParseError(Exception):
    pass


def InsCheckConstraints(ins: ir.Ins):
    last_type = o.DK.INVALID
    for n, (ok, tc, op) in enumerate(zip(ins.opcode.operand_kinds,
                                         ins.opcode.constraints,
                                         ins.operands)):
        if isinstance(op, ir.Reg):
            assert ok in {o.OP_KIND.REG, o.OP_KIND.REG_OR_CONST}
            rk = op.kind
            if not o.CheckTypeConstraint(last_type, tc, rk):
                raise ParseError(
                    f"bad reg operand {rk} {rk.name} expected: {tc.name}  [{ins} {ins.operands}]")
            last_type = rk
        elif isinstance(op, ir.Const):
            assert ok in {o.OP_KIND.CONST,
                          o.OP_KIND.REG_OR_CONST}, f"unexpected {op} in {ins} {ins.operands}"
            rk = op.kind
            if not o.CheckTypeConstraint(last_type, tc, rk):
                raise ParseError(
                    f"bad reg operand {rk} {rk.name}  expected: {tc.name} in {ins} {ins.operands}")
            last_type = rk
        else:
            assert ok not in {o.OP_KIND.REG, o.OP_KIND.CONST,
                              o.OP_KIND.REG_OR_CONST}, f"{ins} {ins.operands}"


# check_fallthroughs ensures that the next bbl is a fallthrough
def FunCheckCFG(fun: ir.Fun, check_fallthroughs):
    assert len(
        fun.bbls) == len(
        fun.bbl_syms), f"bbl mismatch {len(fun.bbls)} {fun.bbl_syms}"
    for n, bbl in enumerate(fun.bbls):
        assert bbl.name in fun.bbl_syms
        for x in bbl.edge_out:
            assert x.name in fun.bbl_syms, f"missing {x}"
        for x in bbl.edge_in:
            assert x.name in fun.bbl_syms, f"missing {x}"
        # check everything but the last Ins
        for ins in bbl.inss[:-1]:
            assert not ins.opcode.is_bbl_terminator(), f"{fun.name} {bbl} {ins} {bbl.inss[-1]}"
            InsCheckConstraints(ins)
        if not bbl.inss:
            assert len(bbl.edge_out) == 1, f"{bbl} {bbl.edge_out}"
            succ = bbl.edge_out[0]
            assert bbl in succ.edge_in
        else:
            last_ins = bbl.inss[-1]
            last_ins_kind = last_ins.opcode.kind
            InsCheckConstraints(last_ins)
            if last_ins_kind == o.OPC_KIND.SWITCH:
                # TODO
                pass
            elif last_ins_kind is o.OPC_KIND.COND_BRA:
                assert len(bbl.edge_out) == 2
                succ1 = bbl.edge_out[0]
                assert bbl in succ1.edge_in
                succ2 = bbl.edge_out[1]
                assert bbl in succ2.edge_in
                assert last_ins.operands[2] in bbl.edge_out, last_ins
                if check_fallthroughs:
                    assert fun.bbls[n + 1] in bbl.edge_out

            elif last_ins_kind == o.OPC_KIND.BRA:
                assert len(bbl.edge_out) == 1
                succ = bbl.edge_out[0]
                assert bbl in succ.edge_in
                assert last_ins.operands[0] == succ
            elif last_ins_kind == o.OPC_KIND.RET:
                assert len(bbl.edge_out) == 0
            else:
                assert len(bbl.edge_out) == 1
                succ = bbl.edge_out[0]
                assert bbl in succ.edge_in
                if check_fallthroughs:
                    assert succ == fun.bbls[n + 1]


def _CheckIns(ins, fun, unit):
    for n, op in enumerate(ins.operands):
        ot = ins.opcode.operand_kinds[n]
        if isinstance(op, ir.Reg):
            assert ot is o.OP_KIND.REG or ot is o.OP_KIND.REG_OR_CONST
            assert op.name in fun.reg_syms, f"{ins} {op} {fun.reg_syms}"
        elif isinstance(op, ir.Fun):
            assert ot is o.OP_KIND.FUN
            assert (op.kind in {o.FUN_KIND.BUILTIN, o.FUN_KIND.SIGNATURE} or
                    op.bbls), f"undefined call to {op.name} in {fun.name}"
            if unit:
                assert op.name in unit.fun_syms
        elif isinstance(op, ir.Bbl):
            assert ot is o.OP_KIND.BBL
            assert op.name in fun.bbl_syms
        elif isinstance(op, ir.Mem):
            assert ot is o.OP_KIND.MEM
        elif isinstance(op, ir.Stk):
            assert ot is o.OP_KIND.STK
            assert op.name in fun.stk_syms
        elif isinstance(op, ir.Jtb):
            assert ot is o.OP_KIND.JTB
            assert op.name in fun.jtb_syms
        elif isinstance(op, ir.Const):
            assert ot is o.OP_KIND.CONST or ot is o.OP_KIND.REG_OR_CONST
        else:
            raise ir.ParseError(f"cannot read op type: {op} {ot}")


class FunArgState:

    def __init__(self, fun):
        self.push_args: List[o.DK] = []
        self.pop_args: List[o.DK] = fun.input_types.copy()
        self.callee = "input args"

    def handle_poparg(self, ins, bbl, fun):
        assert self.pop_args, (f"stray poparg while processing {self.callee} "
                               f"in {fun.name}:{bbl.name}: {ins.operands}")
        a = self.pop_args.pop(0)
        assert a == ins.operands[0].kind, (f"wrong poparg type while processing {self.callee}"
                                           f"{fun.name}:{bbl.name} {self.pop_args} "
                                           f"{a} vs {ins.operands[0]}")

    def handle_pusharg(self, ins, bbl, fun):
        self.push_args.append(ins.operands[0].kind)  # kind works for both regs ans consts

    def handle_call(self, ins, bbl, fun):
        callee: ir.Fun = cfg.InsCallee(ins)
        assert not self.pop_args, (f"unconsumed popargs from {self.callee} "
                                   f"in {fun.name}:{bbl.name}: {self.pop_args}")
        self.pop_args = callee.output_types.copy()
        self.callee = f"{callee.name} results"
        self.push_args.reverse()
        assert self.push_args == callee.input_types, (f"parameter mismatch for {callee.name} "
                                                      f"in {fun.name}:{bbl.name} "
                                                      f"{self.push_args} vs {callee.input_types}")
        self.push_args = []

    def handle_ret(self, ins, bbl, fun):
        self.push_args.reverse()
        assert self.push_args == fun.output_types, (f"return signature mismatch in "
                                                    f"{fun.name}:{bbl.name}: "
                                                    f"{self.push_args} vs {fun.output_types}")
        self.push_args = []

    def check_ins(self, ins, bbl, fun):
        if ins.opcode is o.POPARG:
            self.handle_poparg(ins, bbl, fun)
        else:
            assert not self.pop_args, f"stray poparg in {fun.name}:{bbl.name}: {ins.operands}"

        if ins.opcode is o.PUSHARG:
            self.handle_pusharg(ins, bbl, fun)
        elif ins.opcode is o.RET:
            self.handle_ret(ins, bbl, fun)
        elif ins.opcode.is_call():
            self.handle_call(ins, bbl, fun)
        else:
            assert not self.push_args, (f"unprocessed pushargs in {fun.name}:{bbl.name}: "
                                        f"{self.push_args} at {ins}")


def FunCheck(fun: ir.Fun, unit: Optional[ir.Unit], check_cfg=True,
             check_push_pop=False,
             check_fallthroughs=False):
    """This is main consistency checker

    check_cfg enable cfg related consistency checks
    check_fallthroughs will only work after FunAddUnconditionalBranches has been
    called
    """
    assert len(fun.bbls) == len(fun.bbl_syms)
    assert len(fun.regs) == len(fun.reg_syms)
    assert len(fun.jtbs) == len(fun.jtb_syms)

    if not fun.bbls:
        assert fun.kind in {o.FUN_KIND.EXTERN, o.FUN_KIND.BUILTIN,
                            o.FUN_KIND.SIGNATURE}, f"undefined fun {fun.name}"
        return

    if check_cfg:
        FunCheckCFG(fun, check_fallthroughs)
    fun_arg_state = FunArgState(fun)
    for bbl in fun.bbls:
        for ins in bbl.inss:
            _CheckIns(ins, fun, unit)
            if check_push_pop:
                fun_arg_state.check_ins(ins, bbl, fun)

