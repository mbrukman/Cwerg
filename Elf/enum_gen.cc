// (c) Robert Muth - see LICENSE for more info
// NOTE: this file is PARTIALLY autogenerated via: ./enum_tab.py gen_c

#include "Elf/enum_gen.h"
#include "Util//assert.h"

namespace cwerg::elf {

/* @AUTOGEN-START@ */

const char* const EI_CLASS_ToStringMap[] = {
    "NONE", // 0
    "X_32", // 1
    "X_64", // 2
};

template<>  // template specialization for EI_CLASS
const char* EnumToString<EI_CLASS>(EI_CLASS x) { return EI_CLASS_ToStringMap[unsigned(x)]; }


const char* const EI_DATA_ToStringMap[] = {
    "NONE", // 0
    "LSB2", // 1
    "MSB2", // 2
};

template<>  // template specialization for EI_DATA
const char* EnumToString<EI_DATA>(EI_DATA x) { return EI_DATA_ToStringMap[unsigned(x)]; }


const char* const EI_VERSION_ToStringMap[] = {
    "NONE", // 0
    "CURRENT", // 1
};

template<>  // template specialization for EI_VERSION
const char* EnumToString<EI_VERSION>(EI_VERSION x) { return EI_VERSION_ToStringMap[unsigned(x)]; }


const char* const EI_OSABI_ToStringMap[] = {
    "SYSV", // 0
    "HPUX", // 1
    "NETBSD", // 2
    "LINUX", // 3
    "HURD", // 4
    "", // 5
    "SOLARIS", // 6
    "AIX", // 7
    "IRIX", // 8
    "FREEBSD", // 9
    "TRU64", // 10
    "MODESTO", // 11
    "OPENBSD", // 12
    "OPENVMS", // 13
    "NSK", // 14
    "AROS", // 15
    "FENIXOS", // 16
    "CLOUD", // 17
    "", // 18
    "", // 19
    "", // 20
    "", // 21
    "", // 22
    "", // 23
    "", // 24
    "", // 25
    "", // 26
    "", // 27
    "", // 28
    "", // 29
    "", // 30
    "", // 31
    "", // 32
    "", // 33
    "", // 34
    "", // 35
    "", // 36
    "", // 37
    "", // 38
    "", // 39
    "", // 40
    "", // 41
    "", // 42
    "", // 43
    "", // 44
    "", // 45
    "", // 46
    "", // 47
    "", // 48
    "", // 49
    "", // 50
    "", // 51
    "", // 52
    "SORTIX", // 53
    "", // 54
    "", // 55
    "", // 56
    "", // 57
    "", // 58
    "", // 59
    "", // 60
    "", // 61
    "", // 62
    "", // 63
    "ARM_AEABI", // 64
    "", // 65
    "", // 66
    "", // 67
    "", // 68
    "", // 69
    "", // 70
    "", // 71
    "", // 72
    "", // 73
    "", // 74
    "", // 75
    "", // 76
    "", // 77
    "", // 78
    "", // 79
    "", // 80
    "", // 81
    "", // 82
    "", // 83
    "", // 84
    "", // 85
    "", // 86
    "", // 87
    "", // 88
    "", // 89
    "", // 90
    "", // 91
    "", // 92
    "", // 93
    "", // 94
    "", // 95
    "", // 96
    "ARM", // 97
};

template<>  // template specialization for EI_OSABI
const char* EnumToString<EI_OSABI>(EI_OSABI x) { return EI_OSABI_ToStringMap[unsigned(x)]; }


const char* const E_TYPE_ToStringMap[] = {
    "NONE", // 0
    "REL", // 1
    "EXEC", // 2
    "DYN", // 3
    "CORE", // 4
};

template<>  // template specialization for E_TYPE
const char* EnumToString<E_TYPE>(E_TYPE x) { return E_TYPE_ToStringMap[unsigned(x)]; }


const char* const E_MACHINE_ToStringMap[] = {
    "NONE", // 0
    "M32", // 1
    "SPARC", // 2
    "X_386", // 3
    "X_68K", // 4
    "X_88K", // 5
    "IAMCU", // 6
    "X_860", // 7
    "MIPS", // 8
    "S370", // 9
    "MIPS_RS3_LE", // 10
    "", // 11
    "", // 12
    "", // 13
    "", // 14
    "PARISC", // 15
    "", // 16
    "VPP500", // 17
    "SPARC32PLUS", // 18
    "X_960", // 19
    "PPC", // 20
    "PPC64", // 21
    "S390", // 22
    "SPU", // 23
    "", // 24
    "", // 25
    "", // 26
    "", // 27
    "", // 28
    "", // 29
    "", // 30
    "", // 31
    "", // 32
    "", // 33
    "", // 34
    "", // 35
    "V800", // 36
    "FR20", // 37
    "RH32", // 38
    "RCE", // 39
    "ARM", // 40
    "ALPHA", // 41
    "SH", // 42
    "SPARCV9", // 43
    "TRICORE", // 44
    "ARC", // 45
    "H8_300", // 46
    "H8_300H", // 47
    "H8S", // 48
    "H8_500", // 49
    "IA_64", // 50
    "MIPS_X", // 51
    "COLDFIRE", // 52
    "X_68HC12", // 53
    "MMA", // 54
    "PCP", // 55
    "NCPU", // 56
    "NDR1", // 57
    "STARCORE", // 58
    "ME16", // 59
    "ST100", // 60
    "TINYJ", // 61
    "X86_64", // 62
    "PDSP", // 63
    "PDP10", // 64
    "PDP11", // 65
    "FX66", // 66
    "ST9PLUS", // 67
    "ST7", // 68
    "X_68HC16", // 69
    "X_68HC11", // 70
    "X_68HC08", // 71
    "X_68HC05", // 72
    "SVX", // 73
    "ST19", // 74
    "VAX", // 75
    "CRIS", // 76
    "JAVELIN", // 77
    "FIREPATH", // 78
    "ZSP", // 79
    "MMIX", // 80
    "HUANY", // 81
    "PRISM", // 82
    "AVR", // 83
    "FR30", // 84
    "D10V", // 85
    "D30V", // 86
    "V850", // 87
    "M32R", // 88
    "MN10300", // 89
    "MN10200", // 90
    "PJ", // 91
    "OPENRISC", // 92
    "ARC_COMPACT", // 93
    "XTENSA", // 94
    "VIDEOCORE", // 95
    "TMM_GPP", // 96
    "NS32K", // 97
    "TPC", // 98
    "SNP1K", // 99
    "ST200", // 100
    "IP2K", // 101
    "MAX", // 102
    "CR", // 103
    "F2MC16", // 104
    "MSP430", // 105
    "BLACKFIN", // 106
    "SE_C33", // 107
    "SEP", // 108
    "ARCA", // 109
    "UNICORE", // 110
    "EXCESS", // 111
    "DXP", // 112
    "ALTERA_NIOS2", // 113
    "CRX", // 114
    "XGATE", // 115
    "C166", // 116
    "M16C", // 117
    "DSPIC30F", // 118
    "CE", // 119
    "M32C", // 120
    "", // 121
    "", // 122
    "", // 123
    "", // 124
    "", // 125
    "", // 126
    "", // 127
    "", // 128
    "", // 129
    "", // 130
    "TSK3000", // 131
    "RS08", // 132
    "SHARC", // 133
    "ECOG2", // 134
    "SCORE7", // 135
    "DSP24", // 136
    "VIDEOCORE3", // 137
    "LATTICEMICO32", // 138
    "SE_C17", // 139
    "TI_C6000", // 140
    "TI_C2000", // 141
    "TI_C5500", // 142
    "TI_ARP32", // 143
    "TI_PRU", // 144
    "", // 145
    "", // 146
    "", // 147
    "", // 148
    "", // 149
    "", // 150
    "", // 151
    "", // 152
    "", // 153
    "", // 154
    "", // 155
    "", // 156
    "", // 157
    "", // 158
    "", // 159
    "MMDSP_PLUS", // 160
    "CYPRESS_M8C", // 161
    "R32C", // 162
    "TRIMEDIA", // 163
    "QDSP6", // 164
    "X_8051", // 165
    "STXP7X", // 166
    "NDS32", // 167
    "ECOG1", // 168
    "MAXQ30", // 169
    "XIMO16", // 170
    "MANIK", // 171
    "CRAYNV2", // 172
    "RX", // 173
    "METAG", // 174
    "MCST_ELBRUS", // 175
    "ECOG16", // 176
    "CR16", // 177
    "ETPU", // 178
    "SLE9X", // 179
    "L10M", // 180
    "K10M", // 181
    "", // 182
    "AARCH64", // 183
    "", // 184
    "AVR32", // 185
    "STM8", // 186
    "TILE64", // 187
    "TILEPRO", // 188
    "MICROBLAZE", // 189
    "CUDA", // 190
    "TILEGX", // 191
    "CLOUDSHIELD", // 192
    "COREA_1ST", // 193
    "COREA_2ND", // 194
    "ARC_COMPACT2", // 195
    "OPEN8", // 196
    "RL78", // 197
    "VIDEOCORE5", // 198
    "X_78KOR", // 199
    "X_56800EX", // 200
    "BA1", // 201
    "BA2", // 202
    "XCORE", // 203
    "MCHP_PIC", // 204
    "INTEL205", // 205
    "INTEL206", // 206
    "INTEL207", // 207
    "INTEL208", // 208
    "INTEL209", // 209
    "KM32", // 210
    "KMX32", // 211
    "KMX16", // 212
    "KMX8", // 213
    "KVARC", // 214
    "CDP", // 215
    "COGE", // 216
    "COOL", // 217
    "NORC", // 218
    "CSR_KALIMBA", // 219
    "Z80", // 220
    "VISIUM", // 221
    "FT32", // 222
    "MOXIE", // 223
    "AMDGPU", // 224
    "", // 225
    "", // 226
    "", // 227
    "", // 228
    "", // 229
    "", // 230
    "", // 231
    "", // 232
    "", // 233
    "", // 234
    "", // 235
    "", // 236
    "", // 237
    "", // 238
    "", // 239
    "", // 240
    "", // 241
    "", // 242
    "RISCV", // 243
};

template<>  // template specialization for E_MACHINE
const char* EnumToString<E_MACHINE>(E_MACHINE x) { return E_MACHINE_ToStringMap[unsigned(x)]; }


const char* const E_FLAGS_ARM_ToStringMap[] = {
    "RELEXEC", // 1,
    "HASENTRY", // 2,
    "SYMSARESORTED", // 4,
    "DYNSYMSUSESEGIDX", // 8,
    "MAPSYMSFIRST", // 16,
    "ABI_FLOAT_SOFT", // 0x200,
    "ABI_FLOAT_HARD", // 0x400,
    "LE8", // 0x400000,
    "BE8", // 0x800000,
    "EABI_VER1", // 0x1000000,
    "EABI_VER2", // 0x2000000,
    "EABI_VER4", // 0x4000000,
};

template<>  // template specialization for E_FLAGS_ARM
const char* EnumToString<E_FLAGS_ARM>(E_FLAGS_ARM x) { return E_FLAGS_ARM_ToStringMap[unsigned(x)]; }


const char* const SH_TYPE_0_ToStringMap[] = {
    "X_NULL", // 0
    "PROGBITS", // 1
    "SYMTAB", // 2
    "STRTAB", // 3
    "RELA", // 4
    "HASH", // 5
    "DYNAMIC", // 6
    "NOTE", // 7
    "NOBITS", // 8
    "REL", // 9
    "SHLIB", // 10
    "DYNSYM", // 11
    "", // 12
    "", // 13
    "INIT_ARRAY", // 14
    "FINI_ARRAY", // 15
    "PREINIT_ARRAY", // 16
    "GROUP", // 17
    "SYMTAB_SHNDX", // 18
    "NUM", // 19
};

const char* const SH_TYPE_6ffffff5_ToStringMap[] = {
    "GNU_ATTRIBUTES", // 0x6ffffff5
    "GNU_HASH", // 0x6ffffff6
    "GNU_LIBLIST", // 0x6ffffff7
    "", // 1879048184
    "", // 1879048185
    "", // 1879048186
    "", // 1879048187
    "", // 1879048188
    "GNU_verdef", // 0x6ffffffd
    "GNU_verneed", // 0x6ffffffe
    "GNU_versym", // 0x6fffffff
    "", // 1879048192
    "ARM_EXIDX", // 0x70000001
    "ARM_PREEMPTMAP", // 0x70000002
    "ARM_ATTRIBUTES", // 0x70000003
    "ARM_DEBUGOVERLAY", // 0x70000004
};

const char* const SH_FLAGS_ToStringMap[] = {
    "WRITE", // 1,
    "ALLOC", // 2,
    "EXECINSTR", // 4,
    "MERGE", // 16,
    "STRINGS", // 32,
    "INFO_LINK", // 64,
    "LINK_ORDER", // 128,
    "OS_NONCONFORMING", // 0x100,
    "GROUP", // 0x200,
    "TLS", // 0x400,
    "COMPRESSED", // 0x800,
};

template<>  // template specialization for SH_FLAGS
const char* EnumToString<SH_FLAGS>(SH_FLAGS x) { return SH_FLAGS_ToStringMap[unsigned(x)]; }


const char* const P_TYPE_0_ToStringMap[] = {
    "X_NULL", // 0
    "LOAD", // 1
    "DYNAMIC", // 2
    "INTERP", // 3
    "NOTE", // 4
    "SHLIB", // 5
    "PHDR", // 6
    "TLS", // 7
};

const char* const P_TYPE_6474e550_ToStringMap[] = {
    "GNU_EH_FRAME", // 0x6474e550
    "GNU_STACK", // 0x6474e551
    "GNU_RELRO", // 0x6474e552
    "GNU_PROPERTY", // 0x6474e553
};

const char* const P_TYPE_70000000_ToStringMap[] = {
    "ARM_ARCHEXT", // 0x70000000
    "ARM_EXIDX", // 0x70000001
    "", // 1879048194
    "ABIFLAGS", // 0x70000003
};

const char* const P_FLAGS_ToStringMap[] = {
    "X", // 1,
    "W", // 2,
    "R", // 4,
};

template<>  // template specialization for P_FLAGS
const char* EnumToString<P_FLAGS>(P_FLAGS x) { return P_FLAGS_ToStringMap[unsigned(x)]; }


const char* const ST_INFO_BIND_ToStringMap[] = {
    "LOCAL", // 0
    "GLOBAL", // 1
    "WEAK", // 2
    "NUM", // 3
};

template<>  // template specialization for ST_INFO_BIND
const char* EnumToString<ST_INFO_BIND>(ST_INFO_BIND x) { return ST_INFO_BIND_ToStringMap[unsigned(x)]; }


const char* const ST_INFO_TYPE_ToStringMap[] = {
    "NOTYPE", // 0
    "OBJECT", // 1
    "FUNC", // 2
    "SECTION", // 3
    "FILE", // 4
    "COMMON", // 5
    "TLS", // 6
    "NUM", // 7
    "RELC", // 8
    "SRELC", // 9
    "LOOS", // 10
    "", // 11
    "HIOS", // 12
    "LOPROC", // 13
    "", // 14
    "HIPROC", // 15
};

template<>  // template specialization for ST_INFO_TYPE
const char* EnumToString<ST_INFO_TYPE>(ST_INFO_TYPE x) { return ST_INFO_TYPE_ToStringMap[unsigned(x)]; }


const char* const ST_VISIBILITY_ToStringMap[] = {
    "DEFAULT", // 0
    "INTERNAL", // 1
    "HIDDEN", // 2
    "PROTECTED", // 3
    "EXPORTED", // 4
    "SINGLETON", // 5
    "ELIMINATE", // 6
};

template<>  // template specialization for ST_VISIBILITY
const char* EnumToString<ST_VISIBILITY>(ST_VISIBILITY x) { return ST_VISIBILITY_ToStringMap[unsigned(x)]; }


const char* const RELOC_TYPE_ARM_ToStringMap[] = {
    "NONE", // 0
    "PC24", // 1
    "ABS32", // 2
    "REL32", // 3
    "LDR_PC_G0", // 4
    "ABS16", // 5
    "ABS12", // 6
    "THM_ABS5", // 7
    "ABS8", // 8
    "SBREL32", // 9
    "THM_CALL", // 10
    "THM_PC8", // 11
    "BREL_ADJ", // 12
    "SWI24", // 13
    "THM_SWI8", // 14
    "XPC25", // 15
    "THM_XPC22", // 16
    "TLS_DTPMOD32", // 17
    "TLS_DTPOFF32", // 18
    "TLS_TPOFF32", // 19
    "COPY", // 20
    "GLOB_DAT", // 21
    "JUMP_SLOT", // 22
    "RELATIVE", // 23
    "GOTOFF32", // 24
    "BASE_PREL", // 25
    "GOT_BREL", // 26
    "PLT32", // 27
    "CALL", // 28
    "JUMP24", // 29
    "THM_JUMP24", // 30
    "BASE_ABS", // 31
    "ALU_PCREL_7_0", // 32
    "ALU_PCREL_15_8", // 33
    "ALU_PCREL_23_15", // 34
    "LDR_SBREL_11_0_NC", // 35
    "ALU_SBREL_19_12_NC", // 36
    "ALU_SBREL_27_20_CK", // 37
    "TARGET1", // 38
    "SBREL31", // 39
    "V4BX", // 40
    "TARGET2", // 41
    "PREL31", // 42
    "MOVW_ABS_NC", // 43
    "MOVT_ABS", // 44
    "MOVW_PREL_NC", // 45
    "MOVT_PREL", // 46
    "THM_MOVW_ABS_NC", // 47
    "THM_MOVT_ABS", // 48
    "THM_MOVW_PREL_NC", // 49
    "THM_MOVT_PREL", // 50
    "THM_JUMP19", // 51
    "THM_JUMP6", // 52
    "THM_ALU_PREL_11_0", // 53
    "THM_PC12", // 54
    "ABS32_NOI", // 55
    "REL32_NOI", // 56
    "ALU_PC_G0_NC", // 57
    "ALU_PC_G0", // 58
    "ALU_PC_G1_NC", // 59
    "ALU_PC_G1", // 60
    "ALU_PC_G2", // 61
    "LDR_PC_G1", // 62
    "LDR_PC_G2", // 63
    "LDRS_PC_G0", // 64
    "LDRS_PC_G1", // 65
    "LDRS_PC_G2", // 66
    "LDC_PC_G0", // 67
    "LDC_PC_G1", // 68
    "LDC_PC_G2", // 69
    "ALU_SB_G0_NC", // 70
    "ALU_SB_G0", // 71
    "ALU_SB_G1_NC", // 72
    "ALU_SB_G1", // 73
    "ALU_SB_G2", // 74
    "LDR_SB_G0", // 75
    "LDR_SB_G1", // 76
    "LDR_SB_G2", // 77
    "LDRS_SB_G0", // 78
    "LDRS_SB_G1", // 79
    "LDRS_SB_G2", // 80
    "LDC_SB_G0", // 81
    "LDC_SB_G1", // 82
    "LDC_SB_G2", // 83
    "MOVW_BREL_NC", // 84
    "MOVT_BREL", // 85
    "MOVW_BREL", // 86
    "THM_MOVW_BREL_NC", // 87
    "THM_MOVT_BREL", // 88
    "THM_MOVW_BREL", // 89
    "", // 90
    "", // 91
    "", // 92
    "", // 93
    "PLT32_ABS", // 94
    "GOT_ABS", // 95
    "GOT_PREL", // 96
    "GOT_BREL12", // 97
    "GOTOFF12", // 98
    "GOTRELAX", // 99
    "GNU_VTENTRY", // 100
    "GNU_VTINHERIT", // 101
    "THM_JUMP11", // 102
    "THM_JUMP8", // 103
    "TLS_GD32", // 104
    "TLS_LDM32", // 105
    "TLS_LDO32", // 106
    "TLS_IE32", // 107
    "TLS_LE32", // 108
    "TLS_LDO12", // 109
    "TLS_LE12", // 110
    "TLS_IE12GP", // 111
    "PRIVATE_0", // 112
    "PRIVATE_1", // 113
    "PRIVATE_2", // 114
    "PRIVATE_3", // 115
    "PRIVATE_4", // 116
    "PRIVATE_5", // 117
    "PRIVATE_6", // 118
    "PRIVATE_7", // 119
    "PRIVATE_8", // 120
    "PRIVATE_9", // 121
    "PRIVATE_10", // 122
    "PRIVATE_11", // 123
    "PRIVATE_12", // 124
    "PRIVATE_13", // 125
    "PRIVATE_14", // 126
    "PRIVATE_15", // 127
    "ME_TOO", // 128
    "THM_TLS_DESCSEQ16", // 129
    "THM_TLS_DESCSEQ32", // 130
    "THM_GOT_BREL12", // 131
    "", // 132
    "", // 133
    "", // 134
    "", // 135
    "", // 136
    "", // 137
    "", // 138
    "", // 139
    "IRELATIVE", // 140
};

template<>  // template specialization for RELOC_TYPE_ARM
const char* EnumToString<RELOC_TYPE_ARM>(RELOC_TYPE_ARM x) { return RELOC_TYPE_ARM_ToStringMap[unsigned(x)]; }

/* @AUTOGEN-END@ */

template<>
const char* EnumToString<P_TYPE>(P_TYPE x) {
  if (x < P_TYPE::GNU_EH_FRAME) {
    return P_TYPE_0_ToStringMap[unsigned(x)];
  } else if (x < P_TYPE::ARM_ARCHEXT) {
    return P_TYPE_6474e550_ToStringMap[unsigned(x) - 0x6474e550];
  } else {
    return P_TYPE_70000000_ToStringMap[unsigned(x) - 0x70000000];
  }
}

template<>
const char* EnumToString<SH_TYPE>(SH_TYPE x) {
  if (x < SH_TYPE::GNU_ATTRIBUTES) {
    return SH_TYPE_0_ToStringMap[unsigned(x)];
  } else {
    return SH_TYPE_6ffffff5_ToStringMap[unsigned(x) - 0x6ffffff5];
  }
}

}  // namespace cwerg