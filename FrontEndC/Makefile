ALL_TESTS = \
TestData/20000523-1.c \
TestData/20020129-1.c \
TestData/2002-05-02-CastTest.c \
TestData/2002-12-13-MishaTest.c \
TestData/2003-04-22-Switch.c \
TestData/2003-05-14-initialize-string.c \
TestData/2003-05-22-LocalTypeTest.c \
TestData/2003-07-08-BitOpsTest.c \
TestData/2003-10-12-GlobalVarInitializers.c \
TestData/2005-05-12-Int64ToFP.c \
TestData/2005-05-13-SDivTwo.c \
TestData/2005-11-29-LongSwitch.c \
TestData/2006-01-29-SimpleIndirectCall.c \
TestData/2006-02-04-DivRem.c \
TestData/20080424-1.c \
TestData/990127-1.c \
TestData/arrays_decl_ref.c \
TestData/corner_cases.c \
TestData/nqueen.c \
TestData/pr19606.c \
TestData/rename.c \
TestData/struct2.c \
TestData/sumarray.c


META_TESTS = \
TestData/20000523-1.c \
TestData/2002-05-02-CastTest.c \
TestData/2002-12-13-MishaTest.c \
TestData/2003-04-22-Switch.c \
TestData/2003-05-14-initialize-string.c \
TestData/2003-05-22-LocalTypeTest.c \
TestData/2003-07-08-BitOpsTest.c \
TestData/2003-10-12-GlobalVarInitializers.c \
TestData/2005-05-12-Int64ToFP.c \
TestData/2005-05-13-SDivTwo.c \
TestData/2005-11-29-LongSwitch.c \
TestData/2006-01-29-SimpleIndirectCall.c \
TestData/2006-02-04-DivRem.c \
TestData/20080424-1.c \
TestData/990127-1.c \
TestData/arrays_decl_ref.c \
TestData/corner_cases.c \
TestData/nqueen.c \
TestData/pr19606.c \
TestData/rename.c \
TestData/struct2.c \
TestData/sumarray.c
#TestData/20020129-1.c

EASY_TESTS = \
TestData/20000523-1.c \
TestData/20020129-1.c \
TestData/2005-05-12-Int64ToFP.c \
TestData/corner_cases.c \
TestData/2002-05-02-CastTest.c \
TestData/2005-05-13-SDivTwo.c \
TestData/nqueen.c \
TestData/pr19606.c \
TestData/2003-04-22-Switch.c \
TestData/sumarray.c \
TestData/2003-05-22-LocalTypeTest.c \
TestData/20080424-1.c \
TestData/2003-07-08-BitOpsTest.c
# TestData/2006-01-29-SimpleIndirectCall.c 
# TestData/2003-05-14-initialize-string.c 

tests: tests_py tests_c
	@echo

tests_py:  meta_tests translate_tests

tests_c: canonicalize_tests TestData/nano

# exercise meta data generation
%.meta_test : %.c
	@echo "[meta $@]"
	$(PYPY)	./meta.py  $< >$@.out


meta_tests:: $(META_TESTS:.c=.meta_test)

# make sure we can translation without crashing
%.translate_test : %.c
	@echo "[translate $@]"
	$(PYPY)	./translate.py  32 $< >$@.out

translate_tests:: $(EASY_TESTS:.c=.translate_test)


%.canonicalize_test : %.c
	@echo "[compile $@]"
	$(PYPY)	./canonicalize.py  $< >$@.out.c
	$(CC) -Wno-builtin-declaration-mismatch $@.out.c -o $@.exe
	./$@.exe > $@.run.out
	diff $@.run.out $*.reference_output

canonicalize_tests: $(ALL_TESTS:.c=.canonicalize_test)


TestData/nano: TestData/nanojpeg.c
	@echo "[compile $@]"
	$(PYPY)	./canonicalize.py TestData/nanojpeg.c > $@.out.c
	$(CC) -Wno-builtin-declaration-mismatch $@.out.c -o $@.exe
	./$@.exe TestData/ash_tree.jpg $@.ppm
	cmp  $@.ppm TestData/ash_tree.ppm


clean:
	rm -f *.exe *_gen.c TestData/*exe TestData/*out   TestData/*.out.c TestData/*.asm
