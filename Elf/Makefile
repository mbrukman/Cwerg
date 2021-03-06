tests: tests_py tests_c
	@echo

tests_py: clone_x64_test  clone_a32_test gen_x64_test gen_a32_test

tests_c: clone_a32_test_c  clone_x64_test_c gen_x64_test_c gen_a32_test_c

############################################################
# Python Port
############################################################

clone_x64_test:
	@echo "[$@]"
	$(PYPY) ./elfhelper.py clone TestData/hello-x64 hello-x64.clone.out> $@.out 2>&1
	cmp -l  TestData/hello-x64 hello-x64.clone.out

clone_a32_test:
	@echo "[$@]"
	$(PYPY) ./elfhelper.py clone TestData/hello_barebones-a32 hello_barebones-a32.clone.out > $@.out 2>&1
	cmp -l TestData/hello_barebones-a32 hello_barebones-a32.clone.out


gen_x64_test:
	@echo "[$@]"
	$(PYPY) ./gen_elf_test.py genx64 gen.x64.exe.out > $@.out 2>&1
	chmod a+rx gen.x64.exe.out
	./gen.x64.exe.out > gen.x64.actual.out
	diff  TestData/gen.x64.golden  gen.x64.actual.out

gen_a32_test:
	@echo "[$@]"
	$(PYPY) ./gen_elf_test.py gena32 $@.exe  > $@.log.out 2>&1
	chmod a+rx $@.exe
	./$@.exe > $@.out
	diff  TestData/gen.a32.golden  $@.out

############################################################
# C++ Port
############################################################
BUILD_DIR=../build

enum_gen.h: enum_tab.py
	@echo "[$@]"
	$(PYPY) ./enum_tab.py gen_h < enum_gen.h > $@.tmp
	@mv $@.tmp $@

enum_gen.cc: enum_tab.py enum_gen.h
	@echo "[$@]"
	$(PYPY) ./enum_tab.py gen_c  < enum_gen.cc > $@.tmp
	@mv $@.tmp $@

clone_a32_test_c:
	@echo "[$@]"
	@cd $(BUILD_DIR); $(MAKE) -s elf_tool.exe
	$(BUILD_DIR)/elf_tool.exe TestData/hello_barebones-a32

clone_x64_test_c:
	@echo "[$@]"
	@cd $(BUILD_DIR); $(MAKE) -s elf_tool.exe
	$(BUILD_DIR)/elf_tool.exe TestData/hello-x64

gen_a32_test_c:
	@echo "[$@]"
	@cd $(BUILD_DIR); $(MAKE) -s gen_elf_test.exe
	$(BUILD_DIR)/gen_elf_test.exe gena32 $@.exe  > $@.log.out 2>&1
	chmod a+rx $@.exe
	./$@.exe > $@.out
	diff  TestData/gen.a32.golden  $@.out

gen_x64_test_c:
	@echo "[$@]"
	@cd $(BUILD_DIR); $(MAKE) -s gen_elf_test.exe
	$(BUILD_DIR)/gen_elf_test.exe genx64 $@.exe  > $@.log.out 2>&1
	chmod a+rx $@.exe
	./$@.exe > $@.out
	diff  TestData/gen.x64.golden  $@.out

############################################################
# Misc
############################################################

clean:
	rm -f *.out *.exe

