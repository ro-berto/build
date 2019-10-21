unit {
  v_name {
    corpus: "chromium-test"
    language: "c++"
  }
  required_input {
    v_name {
      corpus: "chromium-test"
      path: "src/test.cc"
    }
    info {
      path: "../../test.cc"
      digest: "5c441f31fbcdfdf56cef22dcf78c09ec9c94135cc9801cd5e79936c8043dde4c"
    }
  }
  required_input {
    v_name {
      corpus: "chromium-test"
      path: "src/test.h"
    }
    info {
      path: "../../test.h"
      digest: "15eb6f9f2a579f75704015777f71c7ca3cff623cc8290ab2aa468f33125e64f0"
    }
  }
  required_input {
    v_name {
      corpus: "chromium-test"
      path: "src/test2.h"
    }
    info {
      path: "../../test2.h"
      digest: "b0c58bbe20b8057dd165a8e212231b321f0d01c17ac144386af44ed0103ce785"
    }
  }
  required_input {
    v_name {
      corpus: "winsdk"
      root: "src/third_party/depot_tools/win_toolchain"
      path: "sdk_header.h"
    }
    info {
      path: "../../third_party/depot_tools/win_toolchain/sdk_header.h"
      digest: "d00a30539b38a598d89f113998c1f2fa7924052a4b11b88ef7ead3692576d81d"
    }
  }
  argument: "clang++"
  argument: "-fsyntax-only"
  argument: "-DFOO=\"foo bar\""
  argument: "-std=c++11"
  argument: "-Wno-c++11-narrowing"
  argument: "-Wall"
  argument: "-c"
  argument: "test.cc"
  argument: "-o"
  argument: "test.o"
  argument: "-DKYTHE_IS_RUNNING=1"
  argument: "-w"
  source_file: "../../test.cc"
  output_key: "test.o"
  working_directory: "package_index_testdata/input/src/out/Debug"
  details {
    [kythe.io/proto/kythe.proto.BuildDetails] {
      build_config: "linux"
    }
  }
}
