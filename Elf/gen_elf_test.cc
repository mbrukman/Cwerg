// (c) Robert Muth - see LICENSE for more info

#include "Elf/elfhelper.h"
#include "Elf/enum_gen.h"
#include "Util/assert.h"

#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fstream>
#include <iostream>
#include <string_view>

using namespace cwerg::elf;
using namespace cwerg;

// Unlike char[] this will not count the zero terminator which
// makes it match the python version.
const std::string_view RODATA_X64("Hello, world (asm)\n");

const unsigned char TEXT_X64[] = {
    0x48, 0xc7, 0xc0, 0x01, 0x00, 0x00, 0x00,  // mov  $0x1,%rax
    0x48, 0xc7, 0xc7, 0x01, 0x00, 0x00, 0x00,  // mov  $0x1,%rdi
    0x48, 0xc7, 0xc6, 0x00, 0x20, 0x40, 0x00,  // mov  $0x402000,%rsi
    0x48, 0xc7, 0xc2, 0x13, 0x00, 0x00, 0x00,  // mov  $0x13,%rdx
    0x0f, 0x05,                                // syscall
    0x48, 0xc7, 0xc0, 0x3c, 0x00, 0x00, 0x00,  // mov  $0x3c,%rax
    0x48, 0x31, 0xff,                          // xor    %rdi,%rdi
    0x0f, 0x05,                                // syscall
};

Executable<uint64_t> GenBareBonesX64() {
  auto* sec_rodata = new Section<uint64_t>();
  auto* sec_text = new Section<uint64_t>();
  auto* sec_shstrtab = new Section<uint64_t>();
  std::vector<Section<uint64_t>*> all_sections(
      {sec_rodata, sec_text, sec_shstrtab});

  sec_rodata->InitRodata(1);
  sec_rodata->AddData(RODATA_X64);

  sec_text->InitText(1);
  sec_text->AddData({(const char*)TEXT_X64, sizeof(TEXT_X64)});

  sec_shstrtab->InitStrTab(".shstrtab");
  sec_shstrtab->SetData(MakeShStrTabContents<uint64_t>(all_sections));

  auto seg_ro = new Segment<uint64_t>();
  auto seg_exe = new Segment<uint64_t>();
  auto seg_pseudo = new Segment<uint64_t>();
  std::vector<Segment<uint64_t>*> all_segments({seg_ro, seg_exe, seg_pseudo});

  seg_ro->InitRO(4096);
  seg_ro->sections.push_back(sec_rodata);

  seg_exe->InitExe(4096);
  seg_exe->sections.push_back(sec_text);

  seg_pseudo->InitPseudo();
  seg_pseudo->sections.push_back(sec_shstrtab);

  //  {sec_rodata, sec_text, sec_shstrtab}
  //..{seg_ro, seg_exe, seg_pseudo});
  Executable<uint64_t> exe =
      MakeExecutableX64(0x400000, all_sections, all_segments);

  exe.UpdateVaddrsAndOffsets();
  exe.ehdr.e_entry = sec_text->shdr.sh_addr;
  // patch the message address
  unsigned char* data = (unsigned char*)sec_text->data->data() + 17;
  for (unsigned i = 0; i < 4; ++i) {
    data[i] = (sec_rodata->shdr.sh_addr >> (i * 8)) & 0xff;
  }
  return exe;
}

uint32_t TEXT_A32[] = {
    0xe3a00001,  // mov	r0, #1
    0xe28f1014,  // add	r1, pc, #20
    0xe3a02013,  // mov	r2, #19
    0xe3a07004,  // mov	r7, #4
    0xef000000,  // svc	0x00000000
    0xe3a00000,  // mov	r0, #0
    0xe3a07001,  // mov	r7, #1
    0xef000000,  // svc	0x00000000

    0x6c6c6548,  // .word	0x6c6c6548
    0x6f77206f,  // .word	0x6f77206f
    0x20646c72,  // .word	0x20646c72
    0x6d736128,  // .word	0x6d736128
    0x00000a29,  // .short	0x0a29
};

Executable<uint32_t> GenBareBonesA32() {
  auto* sec_text = new Section<uint32_t>();
  auto* sec_shstrtab = new Section<uint32_t>();
  std::vector<Section<uint32_t>*> all_sections({sec_text, sec_shstrtab});

  sec_text->InitText(1);
  sec_text->AddData({(const char*)TEXT_A32, sizeof(TEXT_A32)});

  sec_shstrtab->InitStrTab(".shstrtab");
  sec_shstrtab->SetData(MakeShStrTabContents<uint32_t>(all_sections));

  auto seg_exe = new Segment<uint32_t>();
  auto seg_pseudo = new Segment<uint32_t>();
  std::vector<Segment<uint32_t>*> all_segments({seg_exe, seg_pseudo});

  seg_exe->InitExe(65536);
  seg_exe->sections.push_back(sec_text);

  seg_pseudo->InitPseudo();
  seg_pseudo->sections.push_back(sec_shstrtab);

  Executable<uint32_t> exe =
      MakeExecutableA32(0x20000, all_sections, all_segments);

  exe.UpdateVaddrsAndOffsets();
  exe.ehdr.e_entry = sec_text->shdr.sh_addr;
  return exe;
}

int main(int argc, char* argv[]) {
  if (argc <= 2) {
    std::cout << "Requires mode and out-file\n";
    return 1;
  }

  if (argv[1] == std::string_view{"genx64"}) {
    auto exe = GenBareBonesX64();
    std::vector<std::string_view> chunks = exe.Save();
    std::ofstream fout(argv[2], std::ios::out | std::ios::binary);
    ASSERT(fout, "Cannot open file " << argv[2]);
    for (const auto& c : chunks) {
      fout.write((const char*)c.data(), c.size());
    }
    fout.close();
  } else if (argv[1] == std::string_view{"gena32"}) {
    auto exe = GenBareBonesA32();
    std::vector<std::string_view> chunks = exe.Save();
    std::ofstream fout(argv[2], std::ios::out | std::ios::binary);
    ASSERT(fout, "Cannot open file " << argv[2]);
    for (const auto& c : chunks) {
      fout.write((const char*)c.data(), c.size());
    }
    fout.close();
  } else {
    ASSERT(false, "Unknown mode " << argv[1]);
    return 1;
  }
}
