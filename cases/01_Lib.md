# Librarie audtoring

## Scenario

El cliente nos solicita validar que sus librerias desarrolladas no tengan vulnerabilidades.

## Frame
- **Access:** White box
- **Environment:** Static/Offline Analysis

## Execution
```shell
╭─[NULLDOGS-seecwinter | 192.168.0.20] ~/Tools/osdlp on (codex/afl-ccsds-fuzzing)✘✘✘                                             12:55:03
╰─(ﾉ˚Д˚)ﾉ make fuzz-libfuzzer
/Applications/Xcode.app/Contents/Developer/usr/bin/make -C fuzz libfuzzer
/Applications/Xcode.app/Contents/Developer/usr/bin/make build/libfuzzer/libfuzzer_spp build/libfuzzer/libfuzzer_tc_receive build/libfuzzer/libfuzzer_tc_receive_crc build/libfuzzer/libfuzzer_tc_stream build/libfuzzer/libfuzzer_tm_stream CC=clang \
		BUILD_DIR=build/libfuzzer
make[2]: `build/libfuzzer/libfuzzer_spp' is up to date.
make[2]: `build/libfuzzer/libfuzzer_tc_receive' is up to date.
make[2]: `build/libfuzzer/libfuzzer_tc_receive_crc' is up to date.
make[2]: `build/libfuzzer/libfuzzer_tc_stream' is up to date.
make[2]: `build/libfuzzer/libfuzzer_tm_stream' is up to date.

╭─[NULLDOGS-seecwinter | 192.168.0.20] ~/Tools/osdlp on (codex/afl-ccsds-fuzzing)✘✘✘                                             12:55:37
╰─(ﾉ˚Д˚)ﾉ mkdir -p fuzz/out/libfuzzer-tc

fuzz/build/libfuzzer/libfuzzer_tc_receive \
  fuzz/out/libfuzzer-tc fuzz/corpus/tc_receive \
  -dict=fuzz/ccsds.dict \
  -max_total_time=60
libfuzzer_tc_receive(37910,0x20cbbe240) malloc: nano zone abandoned due to inability to reserve vm space.
Dictionary: 19 entries
INFO: Running with entropic power schedule (0xFF, 100).
INFO: Seed: 1893701643
INFO: Loaded 1 modules   (8382 inline 8-bit counters): 8382 [0x1005a4000, 0x1005a60be), 
INFO: Loaded 1 PC tables (8382 PCs): 8382 [0x1005a60c0,0x1005c6ca0), 
INFO:        0 files found in fuzz/out/libfuzzer-tc
INFO:        3 files found in fuzz/corpus/tc_receive
INFO: -max_len is not provided; libFuzzer will not generate inputs larger than 4096 bytes
=================================================================
==37910==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x602000000472 at pc 0x00010051a3d8 bp 0x00016f8eddf0 sp 0x00016f8edde8
READ of size 1 at 0x602000000472 thread T0
    #0 0x00010051a3d4 in osdlp_tc_receive osdlp_tc.c:190
    #1 0x000100510b24 in osdlp_fuzz_tc_receive_one_input fuzz_tc_receive.c:19
    #2 0x00010057a0b4 in fuzzer::Fuzzer::ExecuteCallback(unsigned char const*, unsigned long) FuzzerLoop.cpp:619
    #3 0x00010057b9f0 in fuzzer::Fuzzer::ReadAndExecuteSeedCorpora(std::__1::vector<fuzzer::SizedFile, std::__1::allocator<fuzzer::SizedFile>>&) FuzzerLoop.cpp:812
    #4 0x00010057c054 in fuzzer::Fuzzer::Loop(std::__1::vector<fuzzer::SizedFile, std::__1::allocator<fuzzer::SizedFile>>&) FuzzerLoop.cpp:872
    #5 0x00010056bd10 in fuzzer::FuzzerDriver(int*, char***, int (*)(unsigned char const*, unsigned long)) FuzzerDriver.cpp:923
    #6 0x000100596700 in main FuzzerMain.cpp:20
    #7 0x00019e886b94 in start+0x17b8 (dyld:arm64e+0x6b94)

0x602000000472 is located 1 bytes after 1-byte region [0x602000000470,0x602000000471)
allocated by thread T0 here:
    #0 0x000100da8e24 in malloc+0x70 (libclang_rt.asan_osx_dynamic.dylib:arm64+0x54e24)
    #1 0x000100510adc in fuzz_copy_exact fuzz_input.h:18
    #2 0x000100510adc in osdlp_fuzz_tc_receive_one_input fuzz_tc_receive.c:16
    #3 0x00010057a0b4 in fuzzer::Fuzzer::ExecuteCallback(unsigned char const*, unsigned long) FuzzerLoop.cpp:619
    #4 0x00010057b9f0 in fuzzer::Fuzzer::ReadAndExecuteSeedCorpora(std::__1::vector<fuzzer::SizedFile, std::__1::allocator<fuzzer::SizedFile>>&) FuzzerLoop.cpp:812
    #5 0x00010057c054 in fuzzer::Fuzzer::Loop(std::__1::vector<fuzzer::SizedFile, std::__1::allocator<fuzzer::SizedFile>>&) FuzzerLoop.cpp:872
    #6 0x00010056bd10 in fuzzer::FuzzerDriver(int*, char***, int (*)(unsigned char const*, unsigned long)) FuzzerDriver.cpp:923
    #7 0x000100596700 in main FuzzerMain.cpp:20
    #8 0x00019e886b94 in start+0x17b8 (dyld:arm64e+0x6b94)

SUMMARY: AddressSanitizer: heap-buffer-overflow osdlp_tc.c:190 in osdlp_tc_receive
Shadow bytes around the buggy address:
  0x602000000180: fa fa 06 fa fa fa 02 fa fa fa 02 fa fa fa 02 fa
  0x602000000200: fa fa 02 fa fa fa 02 fa fa fa 01 fa fa fa 01 fa
  0x602000000280: fa fa 01 fa fa fa 01 fa fa fa 01 fa fa fa 02 fa
  0x602000000300: fa fa 02 fa fa fa 02 fa fa fa 02 fa fa fa 02 fa
  0x602000000380: fa fa 01 fa fa fa 00 00 fa fa 00 fa fa fa 00 fa
=>0x602000000400: fa fa 00 00 fa fa 00 fa fa fa fa fa fa fa[01]fa
  0x602000000480: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000000500: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000000580: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000000600: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000000680: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==37910==ABORTING
MS: 0 ; base unit: 0000000000000000000000000000000000000000


artifact_prefix='./'; Test unit written to ./crash-da39a3ee5e6b4b0d3255bfef95601890afd80709
Base64: 
[1]    37910 abort      fuzz/build/libfuzzer/libfuzzer_tc_receive fuzz/out/libfuzzer-tc                                          exit:134 

╭─[NULLDOGS-seecwinter | 192.168.0.20] ~/Tools/osdlp on (codex/afl-ccsds-fuzzing)✘✘✘                                             12:55:43
╰─(ﾉ˚Д˚)ﾉ fuzz/build/libfuzzer/libfuzzer_tc_stream \ 
  fuzz/out/libfuzzer-tc fuzz/corpus/tc_stream \                        
  -dict=fuzz/ccsds.dict \
  -max_total_time=60
libfuzzer_tc_stream(44762,0x20cbbe240) malloc: nano zone abandoned due to inability to reserve vm space.
Dictionary: 19 entries
INFO: Running with entropic power schedule (0xFF, 100).
INFO: Seed: 2534128027
INFO: Loaded 1 modules   (8392 inline 8-bit counters): 8392 [0x100a80000, 0x100a820c8), 
INFO: Loaded 1 PC tables (8392 PCs): 8392 [0x100a820c8,0x100aa2d48), 
INFO:        0 files found in fuzz/out/libfuzzer-tc
INFO:        1 files found in fuzz/corpus/tc_stream
INFO: -max_len is not provided; libFuzzer will not generate inputs larger than 4096 bytes
INFO: seed corpus: files: 1 min: 106b max: 106b total: 106b rss: 42Mb
#2	INITED cov: 329 ft: 329 corp: 1/106b exec/s: 0 rss: 43Mb
#6	NEW    cov: 331 ft: 429 corp: 2/178b lim: 106 exec/s: 0 rss: 43Mb L: 72/106 MS: 4 ChangeBit-ChangeASCIIInt-CMP-EraseBytes- DE: "\001\000\000\000\000\000\000\000"-
#9	NEW    cov: 331 ft: 526 corp: 3/284b lim: 106 exec/s: 0 rss: 43Mb L: 106/106 MS: 3 ChangeBinInt-ManualDict-ChangeBit- DE: "\377\377"-
#10	NEW    cov: 331 ft: 623 corp: 4/340b lim: 106 exec/s: 0 rss: 43Mb L: 56/106 MS: 1 EraseBytes-
#11	REDUCE cov: 331 ft: 623 corp: 4/286b lim: 106 exec/s: 0 rss: 44Mb L: 52/106 MS: 1 CrossOver-
#12	NEW    cov: 332 ft: 624 corp: 5/392b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 1 PersAutoDict- DE: "\001\000\000\000\000\000\000\000"-
#18	REDUCE cov: 336 ft: 628 corp: 6/486b lim: 106 exec/s: 0 rss: 44Mb L: 94/106 MS: 1 CopyPart-
#20	REDUCE cov: 336 ft: 628 corp: 6/483b lim: 106 exec/s: 0 rss: 44Mb L: 49/106 MS: 2 PersAutoDict-EraseBytes- DE: "\001\000\000\000\000\000\000\000"-
#23	NEW    cov: 337 ft: 629 corp: 7/582b lim: 106 exec/s: 0 rss: 44Mb L: 99/106 MS: 3 ChangeBinInt-ChangeBit-InsertRepeatedBytes-
#27	REDUCE cov: 337 ft: 629 corp: 7/559b lim: 106 exec/s: 0 rss: 44Mb L: 71/106 MS: 4 ManualDict-ChangeByte-CrossOver-EraseBytes- DE: "\030\000"-
#40	REDUCE cov: 368 ft: 660 corp: 8/632b lim: 106 exec/s: 0 rss: 44Mb L: 73/106 MS: 3 PersAutoDict-ChangeByte-ShuffleBytes- DE: "\030\000"-
#48	NEW    cov: 368 ft: 661 corp: 9/703b lim: 106 exec/s: 0 rss: 44Mb L: 71/106 MS: 3 CrossOver-ChangeBit-InsertByte-
#54	REDUCE cov: 368 ft: 663 corp: 10/774b lim: 106 exec/s: 0 rss: 44Mb L: 71/106 MS: 1 ChangeBit-
#55	REDUCE cov: 368 ft: 663 corp: 10/768b lim: 106 exec/s: 0 rss: 44Mb L: 43/106 MS: 1 EraseBytes-
#78	NEW    cov: 370 ft: 665 corp: 11/841b lim: 106 exec/s: 0 rss: 44Mb L: 73/106 MS: 3 ChangeBit-ChangeBit-ManualDict- DE: "\020\001\300\000\000\000"-
#80	NEW    cov: 437 ft: 732 corp: 12/913b lim: 106 exec/s: 0 rss: 44Mb L: 72/106 MS: 2 ShuffleBytes-ManualDict- DE: "\037\375"-
#93	REDUCE cov: 437 ft: 732 corp: 12/898b lim: 106 exec/s: 0 rss: 44Mb L: 57/106 MS: 3 ManualDict-ManualDict-EraseBytes- DE: "\037\377"-"\037\376"-
#97	NEW    cov: 437 ft: 736 corp: 13/1004b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 4 CrossOver-CrossOver-CMP-InsertRepeatedBytes- DE: "\000\000\000\000"-
#117	NEW    cov: 437 ft: 737 corp: 14/1105b lim: 106 exec/s: 0 rss: 44Mb L: 101/106 MS: 5 InsertByte-ChangeByte-InsertRepeatedBytes-ChangeBit-PersAutoDict- DE: "\001\000\000\000\000\000\000\000"-
#119	NEW    cov: 442 ft: 742 corp: 15/1179b lim: 106 exec/s: 0 rss: 44Mb L: 74/106 MS: 2 InsertByte-ChangeByte-
#158	NEW    cov: 463 ft: 763 corp: 16/1247b lim: 106 exec/s: 0 rss: 44Mb L: 68/106 MS: 4 EraseBytes-ChangeASCIIInt-ChangeBinInt-CrossOver-
#165	REDUCE cov: 467 ft: 767 corp: 17/1317b lim: 106 exec/s: 0 rss: 44Mb L: 70/106 MS: 2 CopyPart-ChangeByte-
#197	NEW    cov: 467 ft: 768 corp: 18/1416b lim: 106 exec/s: 0 rss: 44Mb L: 99/106 MS: 2 ChangeASCIIInt-PersAutoDict- DE: "\377\377"-
#208	NEW    cov: 467 ft: 799 corp: 19/1522b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 1 CopyPart-
#244	NEW    cov: 467 ft: 807 corp: 20/1628b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 1 ManualDict- DE: " \001"-
#249	REDUCE cov: 467 ft: 807 corp: 20/1576b lim: 106 exec/s: 0 rss: 44Mb L: 22/106 MS: 5 ManualDict-InsertByte-InsertByte-ChangeBinInt-CrossOver- DE: "\000\001\300\000\000\000"-
#265	REDUCE cov: 467 ft: 807 corp: 20/1559b lim: 106 exec/s: 0 rss: 44Mb L: 56/106 MS: 1 EraseBytes-
#266	REDUCE cov: 467 ft: 807 corp: 20/1558b lim: 106 exec/s: 0 rss: 44Mb L: 42/106 MS: 1 EraseBytes-
#272	REDUCE cov: 467 ft: 807 corp: 20/1525b lim: 106 exec/s: 0 rss: 44Mb L: 37/106 MS: 1 EraseBytes-
#314	REDUCE cov: 467 ft: 807 corp: 20/1499b lim: 106 exec/s: 0 rss: 44Mb L: 42/106 MS: 2 ManualDict-EraseBytes- DE: "\300"-
#318	REDUCE cov: 467 ft: 807 corp: 20/1449b lim: 106 exec/s: 0 rss: 44Mb L: 21/106 MS: 4 InsertByte-CopyPart-InsertByte-CrossOver-
#344	REDUCE cov: 467 ft: 807 corp: 20/1436b lim: 106 exec/s: 0 rss: 44Mb L: 24/106 MS: 1 EraseBytes-
#360	REDUCE cov: 467 ft: 807 corp: 20/1401b lim: 106 exec/s: 0 rss: 44Mb L: 71/106 MS: 1 EraseBytes-
#412	NEW    cov: 499 ft: 843 corp: 21/1482b lim: 106 exec/s: 0 rss: 44Mb L: 81/106 MS: 2 EraseBytes-ManualDict- DE: "\000\000"-
#418	NEW    cov: 507 ft: 855 corp: 22/1588b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 1 ChangeBinInt-
#423	REDUCE cov: 508 ft: 856 corp: 23/1666b lim: 106 exec/s: 0 rss: 44Mb L: 78/106 MS: 5 CrossOver-InsertByte-CMP-ChangeBinInt-InsertRepeatedBytes- DE: "\000\000\000\000\000\000\000\000"-
#440	REDUCE cov: 508 ft: 856 corp: 23/1656b lim: 106 exec/s: 0 rss: 44Mb L: 89/106 MS: 2 InsertByte-EraseBytes-
#477	REDUCE cov: 508 ft: 856 corp: 23/1621b lim: 106 exec/s: 0 rss: 44Mb L: 38/106 MS: 2 ChangeBit-EraseBytes-
#484	NEW    cov: 508 ft: 888 corp: 24/1702b lim: 106 exec/s: 0 rss: 44Mb L: 81/106 MS: 2 ChangeByte-ShuffleBytes-
#496	REDUCE cov: 508 ft: 888 corp: 24/1664b lim: 106 exec/s: 0 rss: 44Mb L: 18/106 MS: 2 ShuffleBytes-CrossOver-
#514	NEW    cov: 508 ft: 920 corp: 25/1770b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 3 ChangeBit-ChangeBit-CopyPart-
#535	REDUCE cov: 509 ft: 921 corp: 26/1788b lim: 106 exec/s: 0 rss: 44Mb L: 18/106 MS: 1 ChangeByte-
#540	NEW    cov: 510 ft: 922 corp: 27/1853b lim: 106 exec/s: 0 rss: 44Mb L: 65/106 MS: 5 ChangeBit-PersAutoDict-ShuffleBytes-EraseBytes-CMP- DE: " \001"-"\001\031"-
#572	NEW    cov: 510 ft: 925 corp: 28/1956b lim: 106 exec/s: 0 rss: 44Mb L: 103/106 MS: 2 InsertByte-InsertRepeatedBytes-
#589	REDUCE cov: 510 ft: 925 corp: 28/1952b lim: 106 exec/s: 0 rss: 44Mb L: 77/106 MS: 2 ChangeByte-EraseBytes-
#607	NEW    cov: 511 ft: 926 corp: 29/2058b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 3 ChangeByte-CrossOver-ChangeBinInt-
#625	NEW    cov: 511 ft: 927 corp: 30/2164b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 3 ShuffleBytes-ChangeASCIIInt-ChangeBit-
#641	REDUCE cov: 511 ft: 927 corp: 30/2159b lim: 106 exec/s: 0 rss: 44Mb L: 17/106 MS: 1 EraseBytes-
#664	REDUCE cov: 511 ft: 927 corp: 30/2155b lim: 106 exec/s: 0 rss: 44Mb L: 102/106 MS: 3 ChangeASCIIInt-CopyPart-EraseBytes-
#706	NEW    cov: 511 ft: 958 corp: 31/2261b lim: 106 exec/s: 0 rss: 44Mb L: 106/106 MS: 2 ChangeBit-ChangeBinInt-
#714	REDUCE cov: 511 ft: 958 corp: 31/2258b lim: 106 exec/s: 0 rss: 44Mb L: 53/106 MS: 3 CrossOver-CrossOver-EraseBytes-
#725	REDUCE cov: 511 ft: 958 corp: 31/2256b lim: 106 exec/s: 0 rss: 44Mb L: 19/106 MS: 1 EraseBytes-
#731	NEW    cov: 511 ft: 959 corp: 32/2361b lim: 106 exec/s: 0 rss: 44Mb L: 105/106 MS: 1 CrossOver-
#752	REDUCE cov: 511 ft: 959 corp: 32/2358b lim: 106 exec/s: 0 rss: 44Mb L: 39/106 MS: 1 EraseBytes-
#764	REDUCE cov: 511 ft: 959 corp: 32/2322b lim: 106 exec/s: 0 rss: 44Mb L: 69/106 MS: 2 InsertByte-EraseBytes-
#788	REDUCE cov: 511 ft: 959 corp: 32/2268b lim: 106 exec/s: 0 rss: 44Mb L: 17/106 MS: 4 CopyPart-InsertRepeatedBytes-CopyPart-CrossOver-
#794	REDUCE cov: 511 ft: 959 corp: 32/2259b lim: 106 exec/s: 0 rss: 44Mb L: 33/106 MS: 1 EraseBytes-
#795	REDUCE cov: 511 ft: 959 corp: 32/2256b lim: 106 exec/s: 0 rss: 44Mb L: 15/106 MS: 1 EraseBytes-
#843	REDUCE cov: 511 ft: 959 corp: 32/2235b lim: 106 exec/s: 0 rss: 44Mb L: 81/106 MS: 3 ChangeByte-CrossOver-EraseBytes-
#855	REDUCE cov: 511 ft: 959 corp: 32/2210b lim: 106 exec/s: 0 rss: 45Mb L: 44/106 MS: 2 ChangeBinInt-EraseBytes-
#881	REDUCE cov: 511 ft: 959 corp: 32/2196b lim: 106 exec/s: 0 rss: 45Mb L: 87/106 MS: 1 EraseBytes-
#917	REDUCE cov: 511 ft: 959 corp: 32/2188b lim: 106 exec/s: 0 rss: 45Mb L: 11/106 MS: 1 EraseBytes-
#933	REDUCE cov: 511 ft: 959 corp: 32/2158b lim: 106 exec/s: 0 rss: 45Mb L: 57/106 MS: 1 EraseBytes-
#945	REDUCE cov: 511 ft: 959 corp: 32/2152b lim: 106 exec/s: 0 rss: 45Mb L: 11/106 MS: 2 ChangeBit-EraseBytes-
#946	REDUCE cov: 511 ft: 959 corp: 32/2147b lim: 106 exec/s: 0 rss: 45Mb L: 66/106 MS: 1 EraseBytes-
#958	NEW    cov: 512 ft: 1018 corp: 33/2244b lim: 106 exec/s: 0 rss: 45Mb L: 97/106 MS: 2 ManualDict-CrossOver- DE: "\000"-
#1001	NEW    cov: 512 ft: 1019 corp: 34/2314b lim: 106 exec/s: 0 rss: 45Mb L: 70/106 MS: 3 ChangeBit-ShuffleBytes-InsertRepeatedBytes-
#1028	REDUCE cov: 512 ft: 1019 corp: 34/2309b lim: 106 exec/s: 0 rss: 45Mb L: 12/106 MS: 2 PersAutoDict-CrossOver- DE: "\300"-
#1050	REDUCE cov: 512 ft: 1019 corp: 34/2297b lim: 106 exec/s: 0 rss: 45Mb L: 54/106 MS: 2 ShuffleBytes-EraseBytes-
#1062	REDUCE cov: 512 ft: 1019 corp: 34/2266b lim: 106 exec/s: 0 rss: 45Mb L: 50/106 MS: 2 CopyPart-EraseBytes-
#1093	REDUCE cov: 512 ft: 1019 corp: 34/2264b lim: 106 exec/s: 0 rss: 45Mb L: 55/106 MS: 1 CrossOver-
#1174	REDUCE cov: 512 ft: 1019 corp: 34/2247b lim: 106 exec/s: 0 rss: 45Mb L: 38/106 MS: 1 EraseBytes-
#1180	REDUCE cov: 512 ft: 1021 corp: 35/2314b lim: 106 exec/s: 0 rss: 45Mb L: 67/106 MS: 1 InsertRepeatedBytes-
#1209	REDUCE cov: 512 ft: 1021 corp: 35/2302b lim: 106 exec/s: 0 rss: 45Mb L: 26/106 MS: 4 InsertByte-InsertByte-ManualDict-EraseBytes- DE: "\000"-
#1228	NEW    cov: 512 ft: 1053 corp: 36/2408b lim: 106 exec/s: 0 rss: 45Mb L: 106/106 MS: 4 ShuffleBytes-ChangeBinInt-CopyPart-ChangeBinInt-
#1254	NEW    cov: 534 ft: 1075 corp: 37/2509b lim: 106 exec/s: 0 rss: 45Mb L: 101/106 MS: 1 PersAutoDict- DE: " \001"-
#1276	NEW    cov: 534 ft: 1079 corp: 38/2615b lim: 106 exec/s: 0 rss: 45Mb L: 106/106 MS: 2 ChangeBinInt-ChangeByte-
#1330	REDUCE cov: 534 ft: 1079 corp: 38/2597b lim: 106 exec/s: 0 rss: 45Mb L: 59/106 MS: 4 PersAutoDict-ManualDict-ShuffleBytes-EraseBytes- DE: "\000\000\000\000"-"\037\375"-
#1344	REDUCE cov: 543 ft: 1088 corp: 39/2635b lim: 106 exec/s: 0 rss: 45Mb L: 38/106 MS: 4 InsertRepeatedBytes-EraseBytes-ChangeByte-ChangeByte-
#1365	REDUCE cov: 543 ft: 1088 corp: 39/2634b lim: 106 exec/s: 0 rss: 45Mb L: 105/106 MS: 1 EraseBytes-
#1456	NEW    cov: 551 ft: 1096 corp: 40/2737b lim: 106 exec/s: 0 rss: 45Mb L: 103/106 MS: 1 CopyPart-
#1472	REDUCE cov: 551 ft: 1096 corp: 40/2735b lim: 106 exec/s: 0 rss: 45Mb L: 104/106 MS: 1 EraseBytes-
#1483	NEW    cov: 551 ft: 1100 corp: 41/2841b lim: 106 exec/s: 0 rss: 45Mb L: 106/106 MS: 1 ChangeBit-
#1532	REDUCE cov: 551 ft: 1100 corp: 41/2837b lim: 106 exec/s: 0 rss: 45Mb L: 7/106 MS: 4 ManualDict-ShuffleBytes-PersAutoDict-EraseBytes- DE: "\037\375"-"\300"-
#1556	REDUCE cov: 551 ft: 1100 corp: 41/2807b lim: 106 exec/s: 0 rss: 45Mb L: 51/106 MS: 4 ManualDict-InsertByte-ManualDict-EraseBytes- DE: "\037\375"-"\000"-
#1619	REDUCE cov: 551 ft: 1100 corp: 41/2801b lim: 106 exec/s: 0 rss: 45Mb L: 32/106 MS: 3 CrossOver-CrossOver-EraseBytes-
#1621	REDUCE cov: 551 ft: 1100 corp: 41/2775b lim: 106 exec/s: 0 rss: 45Mb L: 77/106 MS: 2 CopyPart-EraseBytes-
#1624	REDUCE cov: 551 ft: 1100 corp: 41/2758b lim: 106 exec/s: 0 rss: 45Mb L: 40/106 MS: 3 ChangeASCIIInt-ManualDict-EraseBytes- DE: "\037\375"-
#1638	REDUCE cov: 551 ft: 1100 corp: 41/2757b lim: 106 exec/s: 0 rss: 45Mb L: 64/106 MS: 4 ChangeBinInt-ChangeBinInt-ChangeByte-EraseBytes-
#1673	NEW    cov: 568 ft: 1117 corp: 42/2863b lim: 106 exec/s: 0 rss: 45Mb L: 106/106 MS: 5 ChangeBinInt-ManualDict-ShuffleBytes-ChangeBit-ManualDict- DE: "\000"-"\000\000"-
#1730	REDUCE cov: 568 ft: 1117 corp: 42/2847b lim: 106 exec/s: 0 rss: 45Mb L: 43/106 MS: 2 ChangeByte-EraseBytes-
#1731	NEW    cov: 568 ft: 1121 corp: 43/2933b lim: 106 exec/s: 0 rss: 45Mb L: 86/106 MS: 1 CopyPart-
#1734	NEW    cov: 568 ft: 1122 corp: 44/3015b lim: 106 exec/s: 0 rss: 45Mb L: 82/106 MS: 3 ManualDict-EraseBytes-CopyPart- DE: "0\001"-
#2050	NEW    cov: 568 ft: 1126 corp: 45/3121b lim: 106 exec/s: 0 rss: 45Mb L: 106/106 MS: 1 CrossOver-
#2056	REDUCE cov: 568 ft: 1126 corp: 45/3112b lim: 106 exec/s: 0 rss: 45Mb L: 44/106 MS: 1 EraseBytes-
#2120	REDUCE cov: 568 ft: 1126 corp: 45/3109b lim: 106 exec/s: 0 rss: 45Mb L: 4/106 MS: 4 ChangeByte-ManualDict-ManualDict-EraseBytes- DE: "\300"-"\300"-
#2129	NEW    cov: 569 ft: 1127 corp: 46/3215b lim: 106 exec/s: 0 rss: 45Mb L: 106/106 MS: 4 PersAutoDict-ShuffleBytes-ChangeBit-ChangeBit- DE: "\020\001\300\000\000\000"-
#2165	REDUCE cov: 569 ft: 1127 corp: 46/3199b lim: 106 exec/s: 0 rss: 45Mb L: 38/106 MS: 1 EraseBytes-
#2169	REDUCE cov: 569 ft: 1127 corp: 46/3197b lim: 106 exec/s: 0 rss: 45Mb L: 104/106 MS: 4 ChangeByte-ChangeByte-PersAutoDict-EraseBytes- DE: "\000\000\000\000\000\000\000\000"-
#2170	REDUCE cov: 569 ft: 1127 corp: 46/3149b lim: 106 exec/s: 0 rss: 45Mb L: 51/106 MS: 1 EraseBytes-
#2178	REDUCE cov: 569 ft: 1127 corp: 46/3144b lim: 106 exec/s: 0 rss: 45Mb L: 21/106 MS: 3 InsertByte-ChangeBinInt-EraseBytes-
#2184	REDUCE cov: 569 ft: 1127 corp: 46/3141b lim: 106 exec/s: 0 rss: 45Mb L: 15/106 MS: 1 EraseBytes-
#2231	REDUCE cov: 569 ft: 1127 corp: 46/3113b lim: 106 exec/s: 0 rss: 45Mb L: 78/106 MS: 2 EraseBytes-ManualDict- DE: "@"-
#2289	NEW    cov: 573 ft: 1131 corp: 47/3219b lim: 106 exec/s: 0 rss: 45Mb L: 106/106 MS: 3 ChangeByte-ShuffleBytes-CMP- DE: "\000\000\000\010"-
#2312	NEW    cov: 573 ft: 1139 corp: 48/3325b lim: 106 exec/s: 0 rss: 45Mb L: 106/106 MS: 3 ChangeByte-ChangeBit-CrossOver-
#2400	NEW    cov: 573 ft: 1141 corp: 49/3407b lim: 106 exec/s: 0 rss: 45Mb L: 82/106 MS: 3 CopyPart-ChangeASCIIInt-ChangeBit-
#2421	REDUCE cov: 573 ft: 1141 corp: 49/3392b lim: 106 exec/s: 0 rss: 45Mb L: 89/106 MS: 1 EraseBytes-
#2423	REDUCE cov: 573 ft: 1141 corp: 49/3387b lim: 106 exec/s: 0 rss: 45Mb L: 33/106 MS: 2 ManualDict-EraseBytes- DE: "\000\000"-
#2478	REDUCE cov: 573 ft: 1141 corp: 49/3380b lim: 106 exec/s: 0 rss: 45Mb L: 44/106 MS: 5 InsertByte-ChangeByte-PersAutoDict-ShuffleBytes-EraseBytes- DE: "\001\000\000\000\000\000\000\000"-
#2487	REDUCE cov: 573 ft: 1141 corp: 49/3372b lim: 106 exec/s: 0 rss: 45Mb L: 42/106 MS: 4 InsertByte-ChangeBinInt-PersAutoDict-EraseBytes- DE: "\300"-
#2510	REDUCE cov: 573 ft: 1141 corp: 49/3369b lim: 106 exec/s: 0 rss: 45Mb L: 86/106 MS: 3 ShuffleBytes-ManualDict-EraseBytes- DE: "\037\375"-
#2518	REDUCE cov: 573 ft: 1141 corp: 49/3360b lim: 106 exec/s: 0 rss: 45Mb L: 62/106 MS: 3 ChangeBit-CrossOver-EraseBytes-
#2565	REDUCE cov: 573 ft: 1141 corp: 49/3359b lim: 106 exec/s: 0 rss: 45Mb L: 20/106 MS: 2 ManualDict-EraseBytes- DE: "\200"-
#2637	REDUCE cov: 573 ft: 1141 corp: 49/3351b lim: 106 exec/s: 0 rss: 45Mb L: 56/106 MS: 2 ChangeByte-EraseBytes-
#2703	REDUCE cov: 573 ft: 1141 corp: 49/3340b lim: 106 exec/s: 0 rss: 45Mb L: 27/106 MS: 1 EraseBytes-
#2721	REDUCE cov: 573 ft: 1141 corp: 49/3326b lim: 106 exec/s: 0 rss: 45Mb L: 18/106 MS: 3 ChangeBit-ChangeBit-EraseBytes-
#2727	REDUCE cov: 573 ft: 1141 corp: 49/3310b lim: 106 exec/s: 0 rss: 45Mb L: 62/106 MS: 1 EraseBytes-
#2813	REDUCE cov: 573 ft: 1141 corp: 49/3309b lim: 106 exec/s: 0 rss: 45Mb L: 10/106 MS: 1 EraseBytes-
#2903	REDUCE cov: 573 ft: 1141 corp: 49/3291b lim: 106 exec/s: 0 rss: 45Mb L: 88/106 MS: 5 ChangeBit-CopyPart-ChangeByte-CrossOver-EraseBytes-
#2984	REDUCE cov: 573 ft: 1141 corp: 49/3290b lim: 106 exec/s: 0 rss: 46Mb L: 19/106 MS: 1 EraseBytes-
#3035	REDUCE cov: 573 ft: 1141 corp: 49/3276b lim: 106 exec/s: 0 rss: 46Mb L: 74/106 MS: 1 EraseBytes-
#3081	REDUCE cov: 573 ft: 1141 corp: 49/3202b lim: 106 exec/s: 0 rss: 46Mb L: 32/106 MS: 1 CrossOver-
#3113	NEW    cov: 589 ft: 1157 corp: 50/3308b lim: 106 exec/s: 0 rss: 46Mb L: 106/106 MS: 2 ChangeBit-ChangeByte-
#3159	REDUCE cov: 589 ft: 1157 corp: 50/3300b lim: 106 exec/s: 0 rss: 46Mb L: 48/106 MS: 1 EraseBytes-
#3181	REDUCE cov: 589 ft: 1157 corp: 50/3296b lim: 106 exec/s: 0 rss: 46Mb L: 40/106 MS: 2 ManualDict-EraseBytes- DE: "@"-
#3182	REDUCE cov: 589 ft: 1157 corp: 50/3265b lim: 106 exec/s: 0 rss: 46Mb L: 12/106 MS: 1 CrossOver-
#3193	NEW    cov: 589 ft: 1158 corp: 51/3357b lim: 106 exec/s: 0 rss: 46Mb L: 92/106 MS: 1 CopyPart-
#3325	REDUCE cov: 590 ft: 1159 corp: 52/3403b lim: 106 exec/s: 0 rss: 46Mb L: 46/106 MS: 2 PersAutoDict-CrossOver- DE: "\000\000\000\000"-
#3341	REDUCE cov: 590 ft: 1159 corp: 52/3393b lim: 106 exec/s: 0 rss: 46Mb L: 41/106 MS: 1 EraseBytes-
#3394	REDUCE cov: 590 ft: 1159 corp: 52/3387b lim: 106 exec/s: 0 rss: 46Mb L: 98/106 MS: 3 CopyPart-ChangeByte-EraseBytes-
#3410	REDUCE cov: 590 ft: 1159 corp: 52/3364b lim: 106 exec/s: 0 rss: 46Mb L: 83/106 MS: 1 EraseBytes-
#3411	REDUCE cov: 590 ft: 1159 corp: 52/3357b lim: 106 exec/s: 0 rss: 46Mb L: 99/106 MS: 1 CrossOver-
#3428	REDUCE cov: 590 ft: 1159 corp: 52/3353b lim: 106 exec/s: 0 rss: 46Mb L: 14/106 MS: 2 CopyPart-EraseBytes-
#3464	REDUCE cov: 590 ft: 1159 corp: 52/3350b lim: 106 exec/s: 0 rss: 46Mb L: 41/106 MS: 1 EraseBytes-
#3502	REDUCE cov: 590 ft: 1159 corp: 52/3332b lim: 106 exec/s: 0 rss: 46Mb L: 24/106 MS: 3 ChangeBinInt-ShuffleBytes-EraseBytes-
#3578	REDUCE cov: 590 ft: 1159 corp: 52/3310b lim: 106 exec/s: 0 rss: 46Mb L: 55/106 MS: 1 EraseBytes-
#3629	REDUCE cov: 590 ft: 1159 corp: 52/3302b lim: 106 exec/s: 0 rss: 46Mb L: 16/106 MS: 1 EraseBytes-
#3751	NEW    cov: 590 ft: 1181 corp: 53/3408b lim: 106 exec/s: 0 rss: 46Mb L: 106/106 MS: 2 ChangeASCIIInt-ManualDict- DE: " \001"-
#3838	REDUCE cov: 590 ft: 1181 corp: 53/3382b lim: 106 exec/s: 0 rss: 46Mb L: 36/106 MS: 2 ChangeBinInt-EraseBytes-
	NEW_FUNC[1/1]: 0x0001009ed2d8 in osdlp_tc_rx_queue_enqueue_now tc_harness.c:78
#3954	NEW    cov: 602 ft: 1193 corp: 54/3488b lim: 106 exec/s: 0 rss: 48Mb L: 106/106 MS: 1 ShuffleBytes-
#3991	REDUCE cov: 602 ft: 1193 corp: 54/3484b lim: 106 exec/s: 0 rss: 48Mb L: 44/106 MS: 2 ManualDict-EraseBytes- DE: "\377\377"-
#3997	REDUCE cov: 602 ft: 1193 corp: 54/3480b lim: 106 exec/s: 0 rss: 48Mb L: 51/106 MS: 1 EraseBytes-
#4037	REDUCE cov: 602 ft: 1193 corp: 54/3463b lim: 106 exec/s: 0 rss: 48Mb L: 66/106 MS: 5 ChangeByte-ShuffleBytes-InsertByte-InsertRepeatedBytes-EraseBytes-
#4063	REDUCE cov: 602 ft: 1193 corp: 54/3459b lim: 106 exec/s: 0 rss: 48Mb L: 29/106 MS: 1 EraseBytes-
#4167	REDUCE cov: 602 ft: 1193 corp: 54/3428b lim: 106 exec/s: 0 rss: 48Mb L: 55/106 MS: 4 ShuffleBytes-ManualDict-ChangeBit-EraseBytes- DE: "\000\000"-
#4223	REDUCE cov: 602 ft: 1193 corp: 54/3423b lim: 106 exec/s: 0 rss: 48Mb L: 93/106 MS: 1 EraseBytes-
#4252	REDUCE cov: 602 ft: 1193 corp: 54/3422b lim: 106 exec/s: 0 rss: 48Mb L: 14/106 MS: 4 CrossOver-InsertByte-ChangeByte-EraseBytes-
#4403	REDUCE cov: 602 ft: 1193 corp: 54/3420b lim: 106 exec/s: 0 rss: 48Mb L: 14/106 MS: 1 EraseBytes-
#4477	REDUCE cov: 602 ft: 1193 corp: 54/3387b lim: 106 exec/s: 0 rss: 48Mb L: 73/106 MS: 4 ChangeByte-ManualDict-CrossOver-EraseBytes- DE: "\340"-
#4512	REDUCE cov: 602 ft: 1252 corp: 55/3450b lim: 106 exec/s: 0 rss: 48Mb L: 63/106 MS: 5 PersAutoDict-CopyPart-ChangeBinInt-ChangeBit-InsertByte- DE: "\037\375"-
#4551	REDUCE cov: 602 ft: 1252 corp: 55/3429b lim: 106 exec/s: 0 rss: 48Mb L: 30/106 MS: 4 ChangeBit-InsertByte-PersAutoDict-EraseBytes- DE: "\000\000"-
#4613	REDUCE cov: 602 ft: 1252 corp: 55/3426b lim: 106 exec/s: 0 rss: 48Mb L: 11/106 MS: 2 PersAutoDict-EraseBytes- DE: "\037\375"-
#4614	REDUCE cov: 602 ft: 1252 corp: 55/3418b lim: 106 exec/s: 0 rss: 48Mb L: 28/106 MS: 1 EraseBytes-
#4636	REDUCE cov: 602 ft: 1252 corp: 55/3409b lim: 106 exec/s: 0 rss: 48Mb L: 97/106 MS: 2 PersAutoDict-EraseBytes- DE: "\000"-
#4648	REDUCE cov: 602 ft: 1252 corp: 55/3408b lim: 106 exec/s: 0 rss: 48Mb L: 3/106 MS: 2 InsertByte-EraseBytes-
#5064	REDUCE cov: 602 ft: 1252 corp: 55/3403b lim: 106 exec/s: 0 rss: 48Mb L: 101/106 MS: 1 EraseBytes-
#5266	REDUCE cov: 609 ft: 1259 corp: 56/3418b lim: 106 exec/s: 0 rss: 48Mb L: 15/106 MS: 2 ManualDict-ChangeBit- DE: "\000"-
#5622	REDUCE cov: 609 ft: 1259 corp: 56/3410b lim: 106 exec/s: 0 rss: 48Mb L: 89/106 MS: 1 CrossOver-
#5674	REDUCE cov: 609 ft: 1259 corp: 56/3396b lim: 106 exec/s: 0 rss: 48Mb L: 48/106 MS: 2 PersAutoDict-EraseBytes- DE: "\037\375"-
#5711	REDUCE cov: 609 ft: 1259 corp: 56/3395b lim: 106 exec/s: 0 rss: 48Mb L: 28/106 MS: 2 ChangeBinInt-EraseBytes-
#5858	REDUCE cov: 609 ft: 1259 corp: 56/3394b lim: 106 exec/s: 0 rss: 48Mb L: 13/106 MS: 2 ShuffleBytes-EraseBytes-
=================================================================
==44762==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x602000030595 at pc 0x0001009eed90 bp 0x00016f411ca0 sp 0x00016f411c98
READ of size 1 at 0x602000030595 thread T0
    #0 0x0001009eed8c in osdlp_tc_unpack osdlp_tc.c:110
    #1 0x0001009f0fa8 in osdlp_tc_receive osdlp_tc.c:204
    #2 0x0001009ecc30 in osdlp_fuzz_tc_stream_one_input fuzz_tc_stream.c:41
    #3 0x000100a56330 in fuzzer::Fuzzer::ExecuteCallback(unsigned char const*, unsigned long) FuzzerLoop.cpp:619
    #4 0x000100a55ac0 in fuzzer::Fuzzer::RunOne(unsigned char const*, unsigned long, bool, fuzzer::InputInfo*, bool, bool*) FuzzerLoop.cpp:516
    #5 0x000100a578ec in fuzzer::Fuzzer::MutateAndTestOne() FuzzerLoop.cpp:765
    #6 0x000100a585f8 in fuzzer::Fuzzer::Loop(std::__1::vector<fuzzer::SizedFile, std::__1::allocator<fuzzer::SizedFile>>&) FuzzerLoop.cpp:910
    #7 0x000100a47f8c in fuzzer::FuzzerDriver(int*, char***, int (*)(unsigned char const*, unsigned long)) FuzzerDriver.cpp:923
    #8 0x000100a7297c in main FuzzerMain.cpp:20
    #9 0x00019e886b94 in start+0x17b8 (dyld:arm64e+0x6b94)

0x602000030595 is located 0 bytes after 5-byte region [0x602000030590,0x602000030595)
allocated by thread T0 here:
    #0 0x000101108e24 in malloc+0x70 (libclang_rt.asan_osx_dynamic.dylib:arm64+0x54e24)
    #1 0x0001009ecbe4 in osdlp_fuzz_tc_stream_one_input fuzz_tc_stream.c:36
    #2 0x000100a56330 in fuzzer::Fuzzer::ExecuteCallback(unsigned char const*, unsigned long) FuzzerLoop.cpp:619
    #3 0x000100a55ac0 in fuzzer::Fuzzer::RunOne(unsigned char const*, unsigned long, bool, fuzzer::InputInfo*, bool, bool*) FuzzerLoop.cpp:516
    #4 0x000100a578ec in fuzzer::Fuzzer::MutateAndTestOne() FuzzerLoop.cpp:765
    #5 0x000100a585f8 in fuzzer::Fuzzer::Loop(std::__1::vector<fuzzer::SizedFile, std::__1::allocator<fuzzer::SizedFile>>&) FuzzerLoop.cpp:910
    #6 0x000100a47f8c in fuzzer::FuzzerDriver(int*, char***, int (*)(unsigned char const*, unsigned long)) FuzzerDriver.cpp:923
    #7 0x000100a7297c in main FuzzerMain.cpp:20
    #8 0x00019e886b94 in start+0x17b8 (dyld:arm64e+0x6b94)

SUMMARY: AddressSanitizer: heap-buffer-overflow osdlp_tc.c:110 in osdlp_tc_unpack
Shadow bytes around the buggy address:
  0x602000030300: fa fa fd fa fa fa fd fa fa fa fd fa fa fa fd fa
  0x602000030380: fa fa fd fa fa fa fd fa fa fa fd fa fa fa fd fa
  0x602000030400: fa fa fd fa fa fa fd fa fa fa fd fa fa fa fd fa
  0x602000030480: fa fa fd fa fa fa fd fd fa fa fd fa fa fa fd fd
  0x602000030500: fa fa fd fa fa fa fd fd fa fa fd fd fa fa 00 02
=>0x602000030580: fa fa[05]fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000030600: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000030680: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000030700: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000030780: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x602000030800: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==44762==ABORTING
MS: 1 ChangeBit-; base unit: 51444eb99432c5de1c7381d2048c0a9654fb6ffc
0x1,0x0,0x5,0x0,0x8,0x0,0x0,0x7,0x1a,0x0,
\001\000\005\000\010\000\000\007\032\000
artifact_prefix='./'; Test unit written to ./crash-b32c221e6c807b39bfed6c0169f594cdae9da48a
Base64: AQAFAAgAAAcaAA==
[1]    44762 abort      fuzz/build/libfuzzer/libfuzzer_tc_stream fuzz/out/libfuzzer-tc                                           exit:134 


```


## Findings
La libreria cuenta con un DOS en varios paquetes
