#!/usr/bin/python3
"""Testing helper for table driven code selection"""

import CpuA32.opcode_tab as arm
from CpuA32 import disassembler
from Base import serialize
from Base import ir
from CodeGenA32 import isel_tab
from CodeGenA32 import regs

from typing import Any
import sys


def OpToStr(op: Any) -> str:
    if isinstance(op, (
            isel_tab.PARAM, arm.PRED, arm.REG, arm.ADDR_MODE, arm.SHIFT)):
        return op.name
    assert isinstance(op, int)
    return str(op)


def OpTypeStr(op: Any) -> str:
    if isinstance(op, ir.Reg):
        return op.kind.name
    elif isinstance(op, ir.Const):
        return op.kind.name
    else:
        return "_"


def HandleIns(ins: ir.Ins, ctx: regs.EmitContext):
    print("INS: " + serialize.InsRenderToAsm(
        ins).strip() + f"  [{' '.join(OpTypeStr(o) for o in ins.operands)}]")
    if ins.opcode in isel_tab.OPCODES_REQUIRING_SPECIAL_HANDLING:
        print(f"    SPECIAL")
        return
    mismatches = isel_tab.FindtImmediateMismatchesInBestMatchPattern(ins)
    if mismatches == isel_tab.MATCH_IMPOSSIBLE:
        print(f"    MATCH_IMPOSSIBLE")
    elif mismatches != 0:
        pattern = isel_tab.FindMatchingPattern(ins)
        assert pattern is None
        print(f"    mismatches: {mismatches:x}")
    else:
        pattern = isel_tab.FindMatchingPattern(ins)
        print(
            f"PAT: reg:[{' '.join(a.name for a in pattern.type_constraints)}]  "
            f"imm:[{' '.join(a.name for a in pattern.imm_constraints)}]")
        for tmpl in pattern.emit:
            armins = tmpl.MakeInsFromTmpl(ins, ctx)
            print(f"    {disassembler.RenderInstructionSystematic(armins)}")


def Translate(fin):
    scratch = regs.FLT_CALLEE_SAVE_REGS[0]
    ctx = regs.EmitContext(0xfc0, 0xfc0, 0xffff0000, 0xffff0000, 66, scratch)
    unit = serialize.UnitParseFromAsm(fin, cpu_regs=regs.CPU_REGS)
    for fun in unit.funs:
        for bbl in fun.bbls:
            for ins in bbl.inss:
                print()
                HandleIns(ins, ctx)


if __name__ == "__main__":
    Translate(sys.stdin)
