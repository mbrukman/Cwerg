#!/usr/bin/python3

"""
ARM 64bit assembler + disassembler + side-effects table



"""
from Util import cgen

from typing import List, Dict, Tuple, Optional, Set

import collections
import dataclasses
import enum
import re
import sys

_DEBUG = False

# ldr_reg requires 7 operands:  [PRED, DST, ADD_MODE, BASE, SHIFT_MODE, INDEX, OFFSET]
MAX_OPERANDS = 7

MAX_BIT_RANGES = 4


def Bits(*patterns) -> Tuple[int, int]:
    """
    combines are list of triples into a single triple
    """
    m = 0
    v = 0
    print("")
    for mask, val, pos in patterns:
        print(f"@@ {v:x}/{m:x}   - ({mask}, {val}, {pos})")
        mask <<= pos
        val <<= pos
        assert m & mask == 0, f"mask overlap {m:x} {mask:x}"
        m |= mask
        v |= val
    # print ("<- %x %x" % (m, v))
    return m, v


def ExtractBits(data, mask) -> int:
    out = 0
    pos = 1
    # print ("@@ %x %x" % (data, mask))
    while mask:
        new_mask = mask & (mask - 1)
        bit = mask ^ new_mask
        if bit & data:
            out |= pos
        pos <<= 1
        mask = new_mask
    # print ("@@ %x" % out)
    return out


def SignedIntFromBits(data, n_bits) -> int:
    mask = (1 << n_bits) - 1
    data &= mask
    if data & (1 << (n_bits - 1)):
        return data - (1 << n_bits)
    else:
        return data


def BitsFromSignedInt(n_bits, x) -> int:
    if x < 0:
        x = (1 << n_bits) + x
    assert x < (1 << n_bits)
    return x


# P/p: pre/post
# U/u: add/sub
# W/w: wb/-
# Note: post+wb no allowed
@enum.unique
class ADDR_MODE(enum.IntEnum):
    puw = 0
    puW = 1
    pUw = 2
    pUW = 3
    Puw = 4
    PuW = 5
    PUw = 6
    PUW = 7


@enum.unique
class SHIFT(enum.IntEnum):
    lsl = 0
    lsr = 1
    asr = 2
    ror_rrx = 3


############################################################
# OK (operand kind) denotes a set of bit in an instruction
# word the constitute an operand. The bits are not necessarily contiguous
# OK maybe further split up in bit ranges which are contiguous.
############################################################
@enum.unique
class OK(enum.Enum):
    Invalid = 0
    # registers
    WREG_0_4 = 1
    WREG_5_9 = 2
    WREG_10_14 = 3
    WREG_16_20 = 4

    XREG_0_4 = 5
    XREG_5_9 = 6
    XREG_10_14 = 7
    XREG_16_20 = 8

    # immediates
    IMM_5_23 = 20
    IMM_10_21 = 21
    IMM_10_21_22_23 = 22
    IMM_10_15 = 23
    IMM_12_20 = 24
    SIMM_12_20 = 25
    IMM_10_21_times_2 = 26
    IMM_10_21_times_4 = 27
    IMM_10_21_times_8 = 28

    # shifts
    SHIFT_22_23 = 30


############################################################
# effects of an opcode wrt the status registers
# Note, the for instructions with the fCC_UPDATE_20 the effect
# is gated on the "s" bit
############################################################
@enum.unique
class SR_UPDATE(enum.Enum):
    NONE = 0
    NZ = 1
    NCZ_PSR = 2
    NCZ = 4
    NCZV = 5


############################################################
# bit ranges are the building blocks of fields
# Each bit range specifies one or more consecutive bits
############################################################
@enum.unique
class BRK(enum.Enum):  # bit range kind

    Verbatim = 0
    Hi = 1
    Lo = 2
    Rotated = 3
    Signed = 4
    Times8 = 5
    Times4 = 6
    Times2 = 7
    Times2Plus4 = 8
    Force0 = 9
    Force1 = 10
    Force3 = 11
    Force6 = 12
    Force14 = 13
    U = 14
    W = 15
    P = 16


BIT_RANGE_MODIFIER_SINGLE: Set[BRK] = {
    BRK.Verbatim,
    BRK.Rotated,
    BRK.Signed,
    BRK.Times8,
    BRK.Times4,
    BRK.Times2,
    BRK.Times2Plus4,
    BRK.Force0,
    BRK.Force1,
    BRK.Force3,
    BRK.Force6,
    BRK.Force14,
}

BIT_RANGE_MODIFIER_HILO: Set[BRK] = {BRK.Hi, BRK.Lo}
BIT_RANGE_MODIFIER_ADDR: Set[BRK] = {BRK.P, BRK.U, BRK.W}
BIT_RANGE_MODIFIER = BIT_RANGE_MODIFIER_SINGLE | BIT_RANGE_MODIFIER_HILO | BIT_RANGE_MODIFIER_ADDR
BIT_RANGE = Tuple[BRK, int, int]

FIELDS_REG: Dict[OK, List[BIT_RANGE]] = {
    OK.WREG_0_4: [(BRK.Verbatim, 5, 0)],
    OK.WREG_5_9: [(BRK.Verbatim, 5, 5)],
    OK.WREG_10_14: [(BRK.Verbatim, 5, 10)],
    OK.WREG_16_20: [(BRK.Verbatim, 5, 16)],
    #
    OK.XREG_0_4: [(BRK.Verbatim, 5, 0)],
    OK.XREG_5_9: [(BRK.Verbatim, 5, 5)],
    OK.XREG_10_14: [(BRK.Verbatim, 5, 10)],
    OK.XREG_16_20: [(BRK.Verbatim, 5, 16)],
}

FIELDS_IMM: Dict[OK, List[BIT_RANGE]] = {
    OK.IMM_5_23: [(BRK.Verbatim, 19, 5)],
    OK.IMM_10_15: [(BRK.Verbatim, 6, 10)],
    OK.IMM_10_21: [(BRK.Verbatim, 12, 10)],
    OK.IMM_10_21_times_2: [(BRK.Verbatim, 12, 10)],
    OK.IMM_10_21_times_4: [(BRK.Verbatim, 12, 10)],
    OK.IMM_10_21_times_8: [(BRK.Verbatim, 12, 10)],

    OK.IMM_10_21_22_23: [(BRK.Verbatim, 14, 10)],
    OK.IMM_12_20: [(BRK.Verbatim, 9, 12)],
    OK.SIMM_12_20: [(BRK.Verbatim, 9, 12)],

}

FIELDS_SHIFT: Dict[OK, List[BIT_RANGE]] = {
    OK.SHIFT_22_23: [(BRK.Verbatim, 2, 22)],
}

# merge all dicts from above
FIELD_DETAILS: Dict[OK, List[BIT_RANGE]] = {
    **FIELDS_REG,
    **FIELDS_SHIFT,
    **FIELDS_IMM,
}

for details in FIELD_DETAILS.values():
    if len(details) == 1:
        assert details[0][0] in BIT_RANGE_MODIFIER_SINGLE
    elif len(details) == 2:
        assert details[0][0] in BIT_RANGE_MODIFIER_HILO
        assert details[1][0] in BIT_RANGE_MODIFIER_HILO
    elif len(details) == 3:
        assert details[0][0] in BIT_RANGE_MODIFIER_ADDR
        assert details[1][0] in BIT_RANGE_MODIFIER_ADDR
        assert details[2][0] in BIT_RANGE_MODIFIER_ADDR
    else:
        assert False

assert len(FIELD_DETAILS) <= 256


def DecodeOperand(operand_kind: OK, value: int) -> int:
    """ Decodes an operand into an int."""
    tmp = 0
    # hi before lo
    # p  before u before w
    for modifier, width, pos in FIELD_DETAILS[operand_kind]:
        mask = (1 << width) - 1
        x = (value >> pos) & mask
        if modifier is BRK.Verbatim:
            return x
        elif modifier is BRK.Hi or modifier is BRK.P:
            tmp = x
        elif modifier is BRK.Times8:
            return x * 8
        elif modifier is BRK.Times4:
            return x * 4
        elif modifier is BRK.Times2:
            return x * 2
        elif modifier is BRK.Times2Plus4:
            return x * 2 + 4
        elif modifier is BRK.U:
            tmp = (tmp << width) | x
        elif modifier is BRK.Lo or modifier is BRK.W:
            return (tmp << width) | x
        elif modifier is BRK.Force1:
            return 1
        elif modifier is BRK.Force0:
            return 0
        elif modifier is BRK.Force3:
            return 3
        elif modifier is BRK.Force6:
            return 6
        elif modifier is BRK.Force14:
            return 14
        elif modifier is BRK.Signed:
            return SignedIntFromBits(x, width)
        else:
            assert False, f"{modifier}"
    # occurs for operands with empty field lists, e.g. OK.REG_LINK
    return 0


def EncodeOperand(operand_kind, val) -> List[Tuple[int, int, int]]:
    """ Encodes an int into a list of bit-fields"""
    bits: List[Tuple[int, int, int]] = []
    # Note: going reverse is crucial to make Hi/Lo and P/U/W work
    for modifier, width, pos in reversed(FIELD_DETAILS[operand_kind]):
        mask = (1 << width) - 1
        if modifier is BRK.Verbatim:
            assert mask & val == val
            bits.append((mask, val, pos))
        elif modifier is BRK.Times8:
            assert val % 8 == 0
            bits.append((mask, val >> 3, pos))
        elif modifier is BRK.Times2:
            assert val % 2 == 0
            bits.append((mask, val >> 1, pos))
        elif modifier is BRK.Times2Plus4:
            assert val & 4 == 4
            assert val % 2 == 0
            bits.append((mask, (val - 4) >> 1, pos))
        elif modifier is BRK.Times4:
            assert val % 4 == 0
            bits.append((mask, val >> 2, pos))
        elif modifier is BRK.Lo or modifier is BRK.W:
            bits.append((mask, val & mask, pos))
            val = val >> width
        elif modifier is BRK.U:
            bits.append((mask, val & mask, pos))
            val = val >> width
        elif modifier is BRK.Hi or modifier is BRK.P:
            assert mask & val == val, f"{operand_kind} {val} {modifier} {mask:x}"
            bits.append((mask, val, pos))
        elif modifier in {BRK.Force0, BRK.Force1, BRK.Force3, BRK.Force6,
                          BRK.Force14}:
            pass
        elif modifier is BRK.Signed:
            bits.append((mask, BitsFromSignedInt(width, val), pos))
        else:
            assert False, f"unknown modifier {modifier}"
    return bits


############################################################
# opcode classes
# an opcode may belong to multiple classes
# TODO: these need a lot of love especially wrt side-effects
############################################################
@enum.unique
class OPC_FLAG(enum.Flag):
    RESULT_64BIT = 1 << 0
    SRC_DST_0_1 = 1 << 1
    DST_0_1 = 1 << 2

    DIV = 1 << 3
    MUL = 1 << 4
    MULACC = 1 << 5
    LOAD = 1 << 6
    STORE = 1 << 7
    ATOMIC = 1 << 8

    ALU = 1 << 9
    ALU1 = 1 << 10

    SIGNEXTEND = 1 << 11
    JUMP = 1 << 12
    LINK = 1 << 13
    THUMB = 1 << 14
    MOVETOSR = 1 << 15
    MOVEFROMSR = 1 << 16
    TEST = 1 << 17
    PREFETCH = 1 << 18
    MULTIPLE = 1 << 19
    VFP = 1 << 20
    SYSCALL = 1 << 21
    BYTEREORDER = 1 << 22
    MISC = 1 << 23
    X = 1 << 24
    W = 1 << 25
    # do not go above 31 as we want these to fit into a 32 bit word


# number of bytes accessed by a memory opcode (ld/st)
@enum.unique
class MEM_WIDTH(enum.Enum):
    NA = 0
    W1 = 1
    W2 = 2
    W4 = 3
    W8 = 4
    W12 = 5
    Variable = 6


_RE_OPCODE_NAME = re.compile(r"[a-z.0-9]+")

# We use the notion of variant to disambiguate opcodes with the same mnemonic
_VARIANTS = {
    "imm",
    "imm_32",
    "imm_64",
    "reg_32",
    "reg_64",
    "imm_pre",
    "imm_post",
    "imm_pre_64",
    "imm_post_64",
    "imm_pre_32",
    "imm_post_32",
    "32",
    "64",
}


class Opcode:
    """The primary purpose of of instantiating an Opcode is to register it with
    the class variable `name_to_opcode`
    """
    name_to_opcode: Dict[str, "Opcode"] = {}

    # the key in this map is what you get when you "and" and opcode with
    # _INS_CLASSIFIER
    # For FindOpcode to work the more specific patterns must precede
    # the less specific ones
    ordered_opcodes: List[List['Opcode']] = [[]] * 256

    def __init__(self, name: str, variant: str,
                 bits: List[Tuple[int, int, int]],
                 fields: List[OK],
                 classes: OPC_FLAG,
                 mem_width: MEM_WIDTH = MEM_WIDTH.NA,
                 sr_update: SR_UPDATE = SR_UPDATE.NONE):
        if _DEBUG:
            print(name)
        assert variant in _VARIANTS, f"bad variant [{variant}]"
        assert _RE_OPCODE_NAME.match(name)
        for f in fields:
            assert f in FIELD_DETAILS, f"miss field to mask entry {f}"

        assert len(fields) <= MAX_OPERANDS

        bit_mask, bit_value = Bits(*bits)
        self.bit_mask = bit_mask
        self.bit_value = bit_value

        all_bits = bits[:]
        for f in fields:
            all_bits += [((1 << t[1]) - 1, 0, t[2])
                         for t in FIELD_DETAILS[f]]
        mask = Bits(*all_bits)[0]
        # make sure all 32bits are accounted for
        assert 0xffffffff == mask, f"instruction word not entirely covered {mask:08x}"

        self.name = name
        self.variant = variant

        enum_name = self.NameForEnum()
        assert enum_name not in Opcode.name_to_opcode
        Opcode.name_to_opcode[enum_name] = self

        mask, value = Bits(*bits)

        assert (bit_mask >> 24) == 0xff, f"bad{name}"

        Opcode.ordered_opcodes[bit_value >> 24].append(self)

        self.fields: List[OK] = fields
        self.classes: OPC_FLAG = classes
        self.sr_update = sr_update
        self.mem_width = mem_width

    def __lt__(self, other):
        return (self.name, self.variant) < (other.name, other.variant)

    def NameForEnum(self):
        name = self.name
        if self.variant:
            name += "_" + self.variant
        return name.replace(".", "_")

    def AssembleOperands(self, operands: List[int]):
        assert len(operands) == len(
            self.fields), f"not enough operands for {self.NameForEnum()}"
        bits = [(self.bit_mask, self.bit_value, 0)]
        for f, o in zip(self.fields, operands):
            bits += EncodeOperand(f, o)
        bit_mask, bit_value = Bits(*bits)
        assert bit_mask == 0xffffffff, f"{self.name} BAD MASK {bit_mask:08x}"
        return bit_value

    def DisassembleOperands(self, data: int) -> List[int]:
        assert data & self.bit_mask == self.bit_value
        return [DecodeOperand(f, data)
                for f in self.fields]

    @classmethod
    def FindOpcode(cls, data: int) -> Optional["Opcode"]:
        for opcode in Opcode.ordered_opcodes[data >> 24]:
            if data & opcode.bit_mask == opcode.bit_value:
                return opcode
        return None


########################################
root010 = (7, 2, 26)
########################################
for w_ext, w_flag, w_bit in [("32", OPC_FLAG.W, (1, 0, 31)), ("64", OPC_FLAG.X, (1, 0, 31))]:
    dst_reg = OK.XREG_0_4 if w_bit else OK.WREG_0_4
    src1_reg = OK.XREG_5_9 if w_bit else OK.WREG_5_9
    src2_reg = OK.XREG_16_20 if w_bit else OK.WREG_16_20

    for name, bits, sr_update in [
        ("add", [(3, 0, 29), (3, 3, 24), (1, 0, 21)], SR_UPDATE.NONE),
        ("adds", [(3, 1, 29), (3, 3, 24), (1, 0, 21)], SR_UPDATE.NZ),
        ("and", [(3, 0, 29), (3, 2, 24), (1, 0, 21)], SR_UPDATE.NONE),
        ("ands", [(3, 3, 29), (3, 2, 24), (1, 0, 21)], SR_UPDATE.NZ),
        ("bic", [(3, 0, 29), (3, 2, 24), (1, 1, 21)], SR_UPDATE.NONE),
        ("bics", [(3, 3, 29), (3, 2, 24), (1, 1, 21)], SR_UPDATE.NZ),
        ("sub", [(3, 2, 29), (3, 3, 24), (1, 0, 21)], SR_UPDATE.NONE),
        ("subs", [(3, 3, 29), (3, 3, 24), (1, 0, 21)], SR_UPDATE.NZ),
        ("orr", [(3, 1, 29), (3, 2, 24), (1, 0, 21)], SR_UPDATE.NONE),
    ]:
        Opcode(name, "reg_" + w_ext, [root010, w_bit] + bits,
               [dst_reg, src1_reg, OK.SHIFT_22_23, src2_reg, OK.IMM_10_15], w_flag, sr_update=sr_update)

########################################
root100 = (7, 4, 26)
########################################
for w_ext, w_flag, w_bit in [("32", OPC_FLAG.W, (1, 0, 31)), ("64", OPC_FLAG.X, (1, 0, 31))]:
    dst_reg = OK.XREG_0_4 if w_bit else OK.WREG_0_4
    src1_reg = OK.XREG_5_9 if w_bit else OK.WREG_5_9
    src2_reg = OK.XREG_16_20 if w_bit else OK.WREG_16_20

    for name, bits, sr_update in [
        ("add", [(3, 0, 29), (3, 1, 24)], SR_UPDATE.NONE),
        ("adds", [(3, 1, 29), (3, 1, 24)], SR_UPDATE.NZ),
        ("sub", [(3, 2, 29), (3, 1, 24)], SR_UPDATE.NONE),
        ("subs", [(3, 3, 29), (3, 1, 24)], SR_UPDATE.NZ),

    ]:
        Opcode(name, "imm_" + w_ext, [root100, w_bit] + bits,
               [dst_reg, src1_reg, OK.IMM_10_21_22_23], w_flag, sr_update=sr_update)

########################################
root110 = (7, 6, 26)
########################################
for w_ext, w_flag, w_bit in [("32", OPC_FLAG.W, (1, 0, 31)), ("64", OPC_FLAG.X, (1, 0, 31))]:
    dst_reg = OK.XREG_0_4 if w_bit else OK.WREG_0_4
    src1_reg = OK.XREG_5_9 if w_bit else OK.WREG_5_9
    src2_reg = OK.XREG_16_20 if w_bit else OK.WREG_16_20
    src3_reg = OK.XREG_10_14 if w_bit else OK.WREG_10_14

    for name, bits in [
        ("madd", [(3, 0, 29), (3, 3, 24), (1, 0, 15)]),
        ("msub", [(3, 0, 29), (3, 3, 24), (1, 1, 15)]),
    ]:
        Opcode(name, w_ext, [root110, w_bit, (7, 0, 21)] + bits,
               [dst_reg, src1_reg, src3_reg, src2_reg], w_flag)

# 64 bit

Opcode("ldr", "imm_64", [root110, (7, 7, 29), (0xf, 5, 22)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.IMM_10_21_times_8], OPC_FLAG(0))
Opcode("ldr", "imm_pre_64", [root110, (7, 7, 29), (0x1f, 2, 21), (3, 3, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldr", "imm_post_64", [root110, (7, 7, 29), (0x1f, 2, 21), (3, 1, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldur", "imm_64", [root110, (7, 7, 29), (0x1f, 2, 21), (3, 0, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))

# 32 bit

Opcode("ldr", "imm_32", [root110, (7, 5, 29), (0xf, 5, 22)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.IMM_10_21_times_4], OPC_FLAG(0))
Opcode("ldr", "imm_pre_32", [root110, (7, 5, 29), (0x1f, 2, 21), (3, 3, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldr", "imm_post_32", [root110, (7, 5, 29), (0x1f, 2, 21), (3, 1, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldur", "imm_32", [root110, (7, 5, 29), (0x1f, 2, 21), (3, 0, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))

Opcode("ldrsw", "imm_64", [root110, (7, 5, 29), (0xf, 6, 22)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.IMM_10_21_times_4], OPC_FLAG(0))
Opcode("ldrsw", "imm_pre_64", [root110, (7, 5, 29), (0x1f, 4, 21), (3, 3, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldrsw", "imm_post_64", [root110, (7, 5, 29), (0x1f, 4, 21), (3, 1, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldursw", "imm_post_64", [root110, (7, 5, 29), (0x1f, 4, 21), (3, 0, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
# 16 bit

Opcode("ldrh", "imm_32", [root110, (7, 3, 29), (0xf, 5, 22)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.IMM_10_21_times_2], OPC_FLAG(0))
Opcode("ldrh", "imm_pre", [root110, (7, 3, 29), (0x1f, 2, 21), (3, 3, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldrh", "imm_post", [root110, (7, 3, 29), (0x1f, 2, 21), (3, 1, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldurh", "imm_32", [root110, (7, 3, 29), (0x1f, 2, 21), (3, 0, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))

Opcode("ldrsh", "imm_32", [root110, (7, 3, 29), (0xf, 7, 22)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.IMM_10_21_times_2], OPC_FLAG(0))
Opcode("ldrsh", "imm_pre_32", [root110, (7, 3, 29), (0x1f, 6, 21), (3, 3, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldrsh", "imm_post_32", [root110, (7, 3, 29), (0x1f, 6, 21), (3, 1, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldursh", "imm_32", [root110, (7, 3, 29), (0x1f, 4, 21), (3, 0, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))

Opcode("ldrsh", "imm_64", [root110, (7, 3, 29), (0xf, 6, 22)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.IMM_10_21_times_2], OPC_FLAG(0))
Opcode("ldrsh", "imm_pre_64", [root110, (7, 3, 29), (0x1f, 4, 21), (3, 3, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldrsh", "imm_post_64", [root110, (7, 3, 29), (0x1f, 4, 21), (3, 1, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldursh", "imm_64", [root110, (7, 3, 29), (0x1f, 6, 21), (3, 0, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))

# 8 bit

Opcode("ldrb", "imm", [root110, (7, 1, 29), (0xf, 5, 22)],
          [OK.WREG_0_4, OK.XREG_5_9, OK.IMM_10_21], OPC_FLAG(0))
Opcode("ldrb", "imm_pre", [root110, (7, 1, 29), (0x1f, 2, 21), (3, 3, 10)],
            [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldrb", "imm_post", [root110, (7, 1, 29), (0x1f, 2, 21), (3, 1, 10)],
            [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldurb", "imm_32", [root110, (7, 1, 29), (0x1f, 2, 21), (3, 0, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))

Opcode("ldrsb", "imm_32", [root110, (7, 1, 29), (0xf, 7, 22)],
          [OK.XREG_0_4, OK.XREG_5_9, OK.IMM_10_21], OPC_FLAG(0))
Opcode("ldrsb", "imm_pre_32", [root110, (7, 1, 29), (0x1f, 6, 21), (3, 3, 10)],
            [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldrsb", "imm_post_32", [root110, (7, 1, 29), (0x1f, 6, 21), (3, 1, 10)],
            [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldursb", "imm_32", [root110, (7, 1, 29), (0x1f, 4, 21), (3, 0, 10)],
       [OK.WREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))

Opcode("ldrsb", "imm_64", [root110, (7, 1, 29), (0xf, 6, 22)],
          [OK.XREG_0_4, OK.XREG_5_9, OK.IMM_10_21], OPC_FLAG(0))
Opcode("ldrsb", "imm_pre_64", [root110, (7, 1, 29), (0x1f, 4, 21), (3, 3, 10)],
            [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldrsb", "imm_post_64", [root110, (7, 1, 29), (0x1f, 4, 21), (3, 1, 10)],
            [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))
Opcode("ldursb", "imm_64", [root110, (7, 1, 29), (0x1f, 6, 21), (3, 0, 10)],
       [OK.XREG_0_4, OK.XREG_5_9, OK.SIMM_12_20], OPC_FLAG(0))




class Ins:
    """Arm flavor of an Instruction

    There can be at most one relocation associated with an Ins
    """
    opcode: Opcode
    operands: List[int] = dataclasses.field(default_factory=list)
    #
    # Note the addend is store in `operands[reloc_pos]
    reloc_symbol: str = ""
    reloc_kind: int = 0
    reloc_pos = 0
    is_local_sym = False


def Disassemble(data: int) -> Optional[Ins]:
    opcode = Opcode.FindOpcode(data)
    if opcode is None:
        return None
    operands = opcode.DisassembleOperands(data)
    if operands is None:
        return None
    return Ins(opcode, operands)


def Assemble(ins: Ins) -> int:
    assert ins.reloc_kind == 0, "reloc has not been resolved"
    return ins.opcode.AssembleOperands(ins.operands)


############################################################
# code below is only used if this file is run as an executable
############################################################
def Query(opcode: str):
    count = 0
    for opc_list in Opcode.ordered_opcodes.values():
        for opc in opc_list:
            if opc.name != opcode:
                continue
            print(f"name={opc.name} variant={opc.variant}")
            print(f"mask={opc.bit_mask:08x} value={opc.bit_value:08x}")
            print("fields with bit ranges:")
            for f in opc.fields:
                print("\t", f.name, FIELD_DETAILS[f])
                count += 1
            print()
    if count:
        print("bit range tuples have the form (modifier, bit-width, start-pos)")


def _get_grouped_opcodes(mask: int) -> List[Opcode]:
    """Preserves the order of the Opcode.ordered_opcodes"""
    d = collections.defaultdict(list)
    for lst in Opcode.ordered_opcodes.values():
        for opc in lst:
            d[opc.bit_value & mask].append(opc)
    out = []
    for k, v in sorted(d.items()):
        out += v
    return out


def _find_mask_matches(mask: int, val: int, opcodes: List[Opcode]) -> Tuple[int, int]:
    first = -1
    last = -1
    for n, opc in enumerate(opcodes):
        if (opc.bit_value & mask) == val & opc.bit_mask:
            if first == -1: first = n
            last = n
    return first, last


def _render_enum_simple(symbols, name):
    print("\n%s {" % name)
    for sym in symbols:
        print(f"    {sym},")
    print("};")


def hash_djb2(x: str):
    """ Simple string hash function for mnemonics

     see http://www.cse.yorku.ca/~oz/hash.html"""
    h = 5381
    for c in x:
        h = (h << 5) + h + ord(c)
    return h & 0xffff


def _EmitCodeH(fout):
    cgen.RenderEnum(cgen.NameValues(OK), "class OK : uint8_t", fout)
    cgen.RenderEnum(cgen.NameValues(SR_UPDATE), "class SR_UPDATE : uint8_t", fout)
    cgen.RenderEnum(cgen.NameValues(BRK), "class BitRangeKind : uint8_t", fout)
    cgen.RenderEnum(cgen.NameValues(MEM_WIDTH), "class MEM_WIDTH : uint8_t", fout)
    cgen.RenderEnum(cgen.NameValues(OPC_FLAG), "OPC_FLAG", fout)
    # cgen.RenderEnum(cgen.NameValues(PRED), "class PRED : uint8_t", fout)
    # cgen.RenderEnum(cgen.NameValues(REG), "class REG : uint8_t", fout)
    # cgen.RenderEnum(cgen.NameValues(SREG), "class SREG : uint8_t", fout)
    # cgen.RenderEnum(cgen.NameValues(DREG), "class DREG : uint8_t", fout)
    # cgen.RenderEnum(cgen.NameValues(ADDR_MODE), "class ADDR_MODE : uint8_t", fout)
    cgen.RenderEnum(cgen.NameValues(SHIFT), "class SHIFT : uint8_t", fout)
    opcodes = [opc.NameForEnum() for opc in _get_grouped_opcodes(_INS_CLASSIFIER)]
    # note we sneak in an invalid first entry
    _render_enum_simple(["invalid"] + opcodes, "enum class OPC : uint16_t")


def _RenderOpcodeTable():
    """Note: we sneak in an invalid first entry"""
    out = [
        '{"invalid", "invalid", 0, 0, 0, {}, 0, MEM_WIDTH::NA, SR_UPDATE::NONE},'
    ]
    opcodes = _get_grouped_opcodes(_INS_CLASSIFIER)
    last = ~0
    for opc in opcodes:
        key = opc.bit_value & _INS_CLASSIFIER
        if key != last:
            out += [
                f"/* {'=' * 60}*/",
                f"/* BLOCK {key:08x} */",
                f"/* {'=' * 60}*/",
            ]
            last = key
        flags = " | ".join([f.name for f in OPC_FLAG if opc.classes & f])
        assert len(opc.fields) <= MAX_OPERANDS
        fields = "{" + ", ".join(["OK::" + f.name for f in opc.fields]) + "}"
        out += [
            "{" +
            f'"{opc.name}", "{opc.NameForEnum()}", 0x{opc.bit_mask:08x}, 0x{opc.bit_value:08x},',
            f' {len(opc.fields)}, {fields},',
            f' {flags}, MEM_WIDTH::{opc.mem_width.name}, SR_UPDATE::{opc.sr_update.name}',
            '},']
    return out


def _RenderOpcodeTableJumper() -> List[str]:
    out = []
    opcodes = _get_grouped_opcodes(_INS_CLASSIFIER)
    for i in range(8):
        first, last = _find_mask_matches(_INS_CLASSIFIER, i * 0x2000000, opcodes)
        # the +1 compensates for the invalid first entry we have snuck in
        out.append(f"{first + 1}, {last + 1}")
    return out


def _RenderFieldTable():
    out = []
    for n, ok in enumerate(OK):
        assert n == ok.value
        if ok is OK.Invalid:
            bit_ranges = []
        else:
            bit_ranges = FIELD_DETAILS[ok]
        assert len(bit_ranges) <= MAX_BIT_RANGES
        out += ["{" + f"   // {ok.name} = {ok.value}"]
        out += [f"    {len(bit_ranges)}," + " {"]
        out += ["    {BitRangeKind::%s, %d, %d}," % (brk.name, a, b)
                for (brk, a, b) in bit_ranges]
        out += ["}}, "]
    return out


_MNEMONIC_HASH_LOOKUP_SIZE = 512


def _RenderMnemonicHashLookup():
    table = ["invalid"] * _MNEMONIC_HASH_LOOKUP_SIZE
    for name, opc in Opcode.name_to_opcode.items():
        h = hash_djb2(name)
        for d in range(64):
            hh = (h + d) % _MNEMONIC_HASH_LOOKUP_SIZE
            if table[hh] == "invalid":
                table[hh] = name
                break
        else:
            assert False, f"probing distance exceeded {name}"
    items = [f"OPC::{t}," for t in table]
    return ["   " + " ".join(items[i:i + 4]) for i in range(0, len(items), 4)]


def _EmitCodeC(fout):
    print("// Indexed by OPC which in turn are organize to help with disassembly", file=fout)
    print("const Opcode OpcodeTable[] = {", file=fout)
    print("\n".join(_RenderOpcodeTable()), file=fout)
    print("};\n", file=fout)

    print("const int16_t OpcodeTableJumper[] = {", file=fout)
    print(",\n".join(_RenderOpcodeTableJumper()), file=fout)
    print("};\n", file=fout)

    print("// Indexed by FieldKind", file=fout)
    print("static const Field FieldTable[] = {", file=fout)
    print("\n".join(_RenderFieldTable()), file=fout)
    print("};\n", file=fout)

    print("// Indexed by djb2 hash of mnemonic. Collisions are resolved via linear probing",
          file=fout)
    print("static const OPC MnemonicHashTable[512] = {", file=fout)
    print("\n".join(_RenderMnemonicHashLookup()), file=fout)
    print("};\n", file=fout)

    # what about REG/SREG/DREG
    cgen.RenderEnumToStringMap(cgen.NameValues(PRED), "PRED", fout)
    cgen.RenderEnumToStringFun("PRED", fout)
    cgen.RenderEnumToStringMap(cgen.NameValues(ADDR_MODE), "ADDR_MODE", fout)
    cgen.RenderEnumToStringFun("ADDR_MODE", fout)
    cgen.RenderEnumToStringMap(cgen.NameValues(SHIFT), "SHIFT", fout)
    cgen.RenderEnumToStringFun("SHIFT", fout)


def _OpcodeDisassemblerExperiments():
    """Some failed experiments for making the disassembler even faster"""
    print("opcode distribution")
    for k, v in Opcode.ordered_opcodes.items():
        submask = ~0
        for x in v:
            submask &= x.bit_mask
        print(f"{k:08x} {len(v):2}  {submask:08x}")
        d = collections.defaultdict(list)
        for x in v:
            d[x.bit_value & submask].append(x)
        for k2, v2 in sorted(d.items()):
            print(f"  {k2:08x} {len(v2):2}")
    # print(f"magic mask {_INS_MAGIC_CLASSIFIER:08x}")
    # d = collections.defaultdict(list)
    # for x in Opcode.name_to_opcode.values():
    #     d[x.bit_value & _INS_MAGIC_CLASSIFIER].append(x)
    # for k, v in sorted(d.items()):
    #     print(f"  {k:08x} {len(v):2}")
    # print("")
    for opc in sorted(Opcode.name_to_opcode.values()):
        print(f"{opc.name:12s} {opc.variant:6s} {opc.fields}")
    print("OK")


def _MnemonicHashingExperiments():
    # experiment for near perfect hashing
    buckets = [[] for _ in range(_MNEMONIC_HASH_LOOKUP_SIZE)]
    table = [""] * _MNEMONIC_HASH_LOOKUP_SIZE
    distance = [0] * 128
    for opc in Opcode.name_to_opcode.values():
        s = opc.NameForEnum()
        h = hash_djb2(s)
        print(f"{s}: {h:x}")
        buckets[h % _MNEMONIC_HASH_LOOKUP_SIZE].append(s)
        for d in range(len(distance)):
            hh = (h + d) % _MNEMONIC_HASH_LOOKUP_SIZE
            if table[hh] == "":
                table[hh] = s
                distance[d] += 1
                break
        else:
            assert False, f"probing distance exceeded {s}"
    print("hash collisions")
    for n, opcodes in enumerate(buckets):
        if opcodes:
            print(f"{n:2x} {len(opcodes)}  {opcodes}")
    print("linear probing distances")
    for n, count in enumerate(distance):
        if count > 0:
            print(f"{n} {count}")


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("no argument provided")
        sys.exit(1)
    if sys.argv[1] == "dist":
        _OpcodeDisassemblerExperiments()
    elif sys.argv[1] == "hash":
        _MnemonicHashingExperiments()
    elif sys.argv[1] == "gen_c":
        cgen.ReplaceContent(_EmitCodeC, sys.stdin, sys.stdout)
    elif sys.argv[1] == "gen_h":
        cgen.ReplaceContent(_EmitCodeH, sys.stdin, sys.stdout)
    else:
        Query(sys.argv[1])
