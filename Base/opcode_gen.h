#pragma once
// (c) Robert Muth - see LICENSE for more info
// NOTE: this file is PARTIALLY autogenerated via: ./opcode_tab.py gen_h

#include <cstdint>
#include <string_view>

namespace cwerg::base {

const unsigned MAX_OPERANDS = 5;
const unsigned MAX_PARAMETERS = 64;

/* @AUTOGEN-START@ */
enum class OPC : uint8_t {
    INVALID = 0x00,

    ADD = 0x10,
    SUB = 0x11,
    MUL = 0x12,
    DIV = 0x13,
    REM = 0x14,
    XOR = 0x18,
    AND = 0x19,
    OR = 0x1a,
    SHL = 0x1b,
    SHR = 0x1c,
    ROTL = 0x1d,

    BEQ = 0x20,
    BNE = 0x21,
    BLT = 0x22,
    BLE = 0x23,
    SWITCH = 0x28,
    BRA = 0x29,
    RET = 0x2a,
    BSR = 0x2b,
    JSR = 0x2c,
    SYSCALL = 0x2d,
    TRAP = 0x2e,

    PUSHARG = 0x30,
    POPARG = 0x31,
    CONV = 0x32,
    BITCAST = 0x33,
    MOV = 0x34,
    CMPEQ = 0x35,
    CMPLT = 0x36,
    LEA = 0x38,
    LEA_MEM = 0x39,
    LEA_STK = 0x3a,
    LEA_FUN = 0x3b,

    LD = 0x40,
    LD_MEM = 0x41,
    LD_STK = 0x42,
    ST = 0x48,
    ST_MEM = 0x49,
    ST_STK = 0x4a,

    NOP = 0xf1,
    NOP1 = 0xf2,

    DIR_MEM = 0x01,
    DIR_DATA = 0x02,
    DIR_ADDR_FUN = 0x03,
    DIR_ADDR_MEM = 0x04,
    DIR_FUN = 0x05,
    DIR_BBL = 0x06,
    DIR_REG = 0x07,
    DIR_STK = 0x08,
    DIR_JTB = 0x09,
};

enum class OPC_GENUS : uint8_t {
    INVALID = 0,
    BASE = 1,
    MISC = 2,
    STRUCT = 3,
    TBD = 4,
};

enum class FUN_KIND : uint8_t {
    INVALID = 0,
    BUILTIN = 1,
    EXTERN = 2,
    NORMAL = 3,
    SIGNATURE = 4,
};

enum class MEM_KIND : uint8_t {
    INVALID = 0,
    RO = 1,
    RW = 2,
    TLS = 3,
    FIX = 4,
    EXTERN = 5,
};

enum class TC : uint8_t {
    INVALID = 0,
    ANY = 1,
    ADDR_NUM = 2,
    ADDR_INT = 3,
    NUM = 4,
    FLT = 5,
    INT = 6,
    ADDR = 7,
    CODE = 8,
    UINT = 9,
    SINT = 10,
    OFFSET = 11,
    SAME_AS_PREV = 20,
    SAME_SIZE_AS_PREV = 22,
};

enum class OPC_KIND : uint8_t {
    INVALID = 0,
    ALU = 1,
    ALU1 = 2,
    MOV = 3,
    LEA = 4,
    LEA1 = 5,
    COND_BRA = 6,
    BRA = 7,
    BSR = 8,
    JSR = 9,
    SWITCH = 10,
    RET = 11,
    SYSCALL = 12,
    ST = 13,
    LD = 14,
    PUSHARG = 15,
    POPARG = 16,
    NOP = 17,
    NOP1 = 18,
    CONV = 19,
    CMP = 20,
    BCOPY = 21,
    BZERO = 22,
    DIRECTIVE = 23,
};

enum class DK : uint8_t {
    INVALID = 0,
    S8 = 32,
    S16 = 33,
    S32 = 34,
    S64 = 35,
    U8 = 64,
    U16 = 65,
    U32 = 66,
    U64 = 67,
    F8 = 96,
    F16 = 97,
    F32 = 98,
    F64 = 99,
    A32 = 130,
    A64 = 131,
    C32 = 162,
    C64 = 163,
};

enum class OP_KIND : uint8_t {
    INVALID = 0,
    REG = 1,
    CONST = 2,
    REG_OR_CONST = 3,
    BBL = 4,
    MEM = 5,
    STK = 6,
    FUN = 7,
    JTB = 8,
    TYPE_LIST = 20,
    DATA_KIND = 21,
    MEM_KIND = 23,
    FUN_KIND = 24,
    FIELD = 25,
    NAME = 26,
    NAME_LIST = 27,
    VALUE = 28,
    BBL_TAB = 29,
    BYTES = 30,
};

enum OA : uint16_t {
    BBL_TERMINATOR = 1,
    NO_FALL_THROUGH = 2,
    CALL = 4,
    COMMUTATIVE = 8,
    MEM_RD = 16,
    MEM_WR = 32,
    SPECIAL = 64,
};
/* @AUTOGEN-END@ */

constexpr const uint8_t DK_FLAVOR_S = 0x20;
constexpr const uint8_t DK_FLAVOR_U = 0x40;
constexpr const uint8_t DK_FLAVOR_F = 0x60;
constexpr const uint8_t DK_FLAVOR_A = 0x80;
constexpr const uint8_t DK_FLAVOR_C = 0xa0;

inline int DKFlavor(DK rk) { return uint8_t(rk) & 0xe0; }
inline int DKBitWidth(DK rk) { return 8 << (uint8_t(rk) & 0x7); }

struct Opcode {
  // layout optimized for usage
  const OP_KIND operand_kinds[MAX_OPERANDS];
  const OPC_KIND kind;
  const OPC_GENUS genus;
  const uint8_t num_operands;
  const uint8_t num_defs;  // defs are always the first few operands
  const TC constraints[MAX_OPERANDS];
  const char* const name;
  uint16_t attributes;

  bool HasAttribute(OA flags) const { return (attributes & flags) != 0; }

  bool IsCall() const { return HasAttribute(OA::CALL); }

  bool HasSideEffect() const {
    return HasAttribute(OA(OA::BBL_TERMINATOR | OA::CALL | OA::MEM_RD |
                        OA::MEM_WR | OA::SPECIAL)); }

  bool IsBblTerminator() const  { return HasAttribute(OA::BBL_TERMINATOR); }
  bool HasFallthrough() const  { return !HasAttribute(OA::NO_FALL_THROUGH); }

};

extern const Opcode GlobalOpcodes[256];

extern OPC OPCFromString(std::string_view  name);
extern OPC_GENUS OpcGenusFromString(std::string_view name);
extern FUN_KIND FKFromString(std::string_view name);
extern MEM_KIND MKFromString(std::string_view name);
extern TC TCFromString(std::string_view name);
extern DK DKFromString(std::string_view name);

template <typename Flag> const char* EnumToString(Flag f);

}  // namespace cwerg
