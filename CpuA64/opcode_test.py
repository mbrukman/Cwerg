#!/usr/bin/python3

"""
This test checks that we can assemble and disassemble all the instructions
found in `arm_test.dis` and similar dumps obtained via `objdump`
"""

import sys
import collections
from typing import List

# import CpuA64.disassembler as dis
import CpuA64.opcode_tab as a64

count_found = 0
count_total = 0

ALIASES = {
    "cmn": {"adds"},
    "cmp": {"subs"},
    "neg": {"sub"},
    "negs": {"subs"},
    "ngcs": {"sbcs"},
    #
    "cneg": {"csneg"},
    "cinc": {"csinc"},
    "cset": {"csinc"},
    "cinv": {"csinv"},
    "csetm": {"csinv"},
    #
    "tst": {"ands"},
    "mov": {"orr", "add", "movz", "movn"},
    "mvn": {"orn"},
    "mul": {"madd"},
    "mneg": {"msub"},
    #
    "lsl": {"lslv", "lsl", "ubfm"},
    "lsr": {"lsrv", "lsr", "ubfm"},
    "asr": {"asrv", "asr", "sbfm"},
    "ror": {"rorv", "ror", "extr"},
    "ubfiz": {"ubfm"},
    "ubfx": {"ubfm"},
    "sbfx": {"sbfm"},
    "sxtb": {"sbfm"},
    "sxth": {"sbfm"},
    "sxtw": {"sbfm"},
    "sbfiz": {"sbfm"},
    "bfxil": {"bfm"},
    "bfi": {"bfm"},
    "bfc": {"bfm"},
    #
    "smull": {"smaddl"},
    "umull": {"umaddl"},
    #
    "ldr": {"ldr", "fldr"},
    "ldp": {"ldp", "fldp"},
    "ldur": {"ldur", "fldur"},
    #
    "ldurb" : {"ldur"},
    "ldurh" : {"ldur"},
    "ldrb" : {"ldr"},
    "ldrb" : {"ldr"},
    "ldrh" : {"ldr"},
    "ldarb" : {"ldar"},
    "ldarh" : {"ldar"},
    "ldxrb": {"ldxr"},
    "ldxrh": {"ldxr"},
    "ldaxrb": {"ldaxr"},
    "ldaxrh": {"ldaxr"},
    "ldpsw": {"ldp"},

    #
    "sturb" : {"stur"},
    "sturh" : {"stur"},
    "strb" : {"str"},
    "strh" : {"str"},
    "stlxrb": {"stlxr"},
    "stlxrh": {"stlxr"},
    "stxrb": {"stxr"},
    "stxrh": {"stxr"},
    "stlrb": {"stlr"},
    "stlrh": {"stlr"},
    "stpw": {"stp"},
    #
    "str":  {"str",  "fstr"},
    "stp": {"stp", "fstp"},
    "stur": {"stur", "fstur"},
}

MISSED = collections.defaultdict(int)
EXAMPLE = {}


def HandleOneInstruction(count: int, line: str,
                         data: int,
                         actual_name: str, actual_ops: List):
    global count_found, count_total, count_mismatch
    count_total += 1
    opcode = a64.Opcode.FindOpcode(data)
    aliases = ALIASES.get(actual_name, {actual_name})
    if opcode:
        count_found += 1
        assert opcode.name in aliases, f"[{opcode.name}#{opcode.variant}] vs [{actual_name}]: {line}"
        #print (line, end="")
    else:
        EXAMPLE[actual_name] = line
        MISSED[actual_name] += 1

def main(argv):
    for fn in argv:
        with open(fn) as fp:
            # actual_XXX: derived from the text assembler listing
            # expected_XXX: derived from decoding the `data`
            count = 0
            for line in fp:
                count += 1
                token = line.split(None, 2)
                if not token or token[0].startswith("#"):
                    continue
                data = int(token[0], 16)
                actual_name = token[1]
                actual_ops = []
                if len(token) == 3:
                    actual_ops = [o.strip() for o in token[2].split(",")]
                HandleOneInstruction(
                    count, line, data, actual_name, actual_ops)
    for k, v in sorted(MISSED.items()):
        print(f"{k:10}: {v:5}     {EXAMPLE[k]}", end="")
    print(f"found {count_found}/{count_total}   {100 * count_found / count_total:3.1f}%")


if __name__ == "__main__":
    # import cProfile
    # cProfile.run("main(sys.argv[1:])")
    main(sys.argv[1:])