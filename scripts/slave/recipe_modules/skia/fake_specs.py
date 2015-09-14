# This file is generated by the scripts/slave/skia/gen_buildbot_specs.py script.

FAKE_SPECS = {
  'Build-Mac10.8-Clang-Arm7-Debug-Android': {
    'build_targets': [
      'most',
    ],
    'builder_cfg': {
      'compiler': 'Clang',
      'configuration': 'Debug',
      'extra_config': 'Android',
      'is_trybot': False,
      'os': 'Mac10.8',
      'role': 'Build',
      'target_arch': 'Arm7',
    },
    'configuration': 'Debug',
    'device_cfg': 'arm_v7_neon',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': False,
    'do_test_steps': False,
    'env': {
      'CC': '/usr/bin/clang',
      'CXX': '/usr/bin/clang++',
      'GYP_DEFINES':
          'skia_arch_type=arm skia_clang_build=1 skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
  'Build-Ubuntu-GCC-Arm7-Debug-Android': {
    'build_targets': [
      'most',
    ],
    'builder_cfg': {
      'compiler': 'GCC',
      'configuration': 'Debug',
      'extra_config': 'Android',
      'is_trybot': False,
      'os': 'Ubuntu',
      'role': 'Build',
      'target_arch': 'Arm7',
    },
    'configuration': 'Debug',
    'device_cfg': 'arm_v7_neon',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': False,
    'do_test_steps': False,
    'env': {
      'GYP_DEFINES': 'skia_arch_type=arm skia_warnings_as_errors=1',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
  'Housekeeper-PerCommit': {
    'build_targets': [
      'most',
    ],
    'builder_cfg': {
      'frequency': 'PerCommit',
      'is_trybot': False,
      'role': 'Housekeeper',
    },
    'configuration': 'Release',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': False,
    'do_test_steps': False,
    'env': {
      'GYP_DEFINES': 'skia_shared_lib=1 skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
  'Housekeeper-PerCommit-Trybot': {
    'build_targets': [
      'most',
    ],
    'builder_cfg': {
      'frequency': 'PerCommit',
      'is_trybot': True,
      'role': 'Housekeeper',
    },
    'configuration': 'Release',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': False,
    'do_test_steps': False,
    'env': {
      'GYP_DEFINES': 'skia_shared_lib=1 skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
  'Perf-Android-GCC-Nexus5-CPU-NEON-Arm7-Release-Appurify': {
    'build_targets': [
      'VisualBenchTest_APK',
    ],
    'builder_cfg': {
      'arch': 'Arm7',
      'compiler': 'GCC',
      'configuration': 'Release',
      'cpu_or_gpu': 'CPU',
      'cpu_or_gpu_value': 'NEON',
      'extra_config': 'Appurify',
      'is_trybot': False,
      'model': 'Nexus5',
      'os': 'Android',
      'role': 'Perf',
    },
    'configuration': 'Release',
    'device_cfg': 'arm_v7',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': False,
    'env': {
      'GYP_DEFINES': 'skia_arch_type=arm skia_gpu=0 skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': True,
  },
  'Perf-Android-GCC-Nexus5-GPU-Adreno330-Arm7-Release-Appurify': {
    'build_targets': [
      'VisualBenchTest_APK',
    ],
    'builder_cfg': {
      'arch': 'Arm7',
      'compiler': 'GCC',
      'configuration': 'Release',
      'cpu_or_gpu': 'GPU',
      'cpu_or_gpu_value': 'Adreno330',
      'extra_config': 'Appurify',
      'is_trybot': False,
      'model': 'Nexus5',
      'os': 'Android',
      'role': 'Perf',
    },
    'configuration': 'Release',
    'device_cfg': 'arm_v7',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': False,
    'env': {
      'GYP_DEFINES': 'skia_arch_type=arm skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': True,
  },
  'Perf-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Release': {
    'build_targets': [
      'nanobench',
    ],
    'builder_cfg': {
      'arch': 'Arm7',
      'compiler': 'GCC',
      'configuration': 'Release',
      'cpu_or_gpu': 'GPU',
      'cpu_or_gpu_value': 'Tegra3',
      'is_trybot': False,
      'model': 'Nexus7',
      'os': 'Android',
      'role': 'Perf',
    },
    'configuration': 'Release',
    'device_cfg': 'nexus_7',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': False,
    'env': {
      'GYP_DEFINES': 'skia_arch_type=arm skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': True,
  },
  'Perf-Win8-MSVC-ShuttleB-GPU-HD4600-x86_64-Release-Trybot': {
    'build_targets': [
      'nanobench',
    ],
    'builder_cfg': {
      'arch': 'x86_64',
      'compiler': 'MSVC',
      'configuration': 'Release',
      'cpu_or_gpu': 'GPU',
      'cpu_or_gpu_value': 'HD4600',
      'is_trybot': True,
      'model': 'ShuttleB',
      'os': 'Win8',
      'role': 'Perf',
    },
    'configuration': 'Release_x64',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': False,
    'env': {
      'GYP_DEFINES':
          ('qt_sdk=C:/Qt/Qt5.1.0/5.1.0/msvc2012_64/ skia_arch_type=x86_64 ski'
           'a_warnings_as_errors=0 skia_win_debuggers_path=c:/DbgHelp'),
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': True,
  },
  'Test-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Debug': {
    'build_targets': [
      'dm',
      'nanobench',
    ],
    'builder_cfg': {
      'arch': 'Arm7',
      'compiler': 'GCC',
      'configuration': 'Debug',
      'cpu_or_gpu': 'GPU',
      'cpu_or_gpu_value': 'Tegra3',
      'is_trybot': False,
      'model': 'Nexus7',
      'os': 'Android',
      'role': 'Test',
    },
    'configuration': 'Debug',
    'device_cfg': 'nexus_7',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': True,
    'env': {
      'GYP_DEFINES': 'skia_arch_type=arm skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
  'Test-ChromeOS-GCC-Link-CPU-AVX-x86_64-Debug': {
    'build_targets': [
      'dm',
      'nanobench',
    ],
    'builder_cfg': {
      'arch': 'x86_64',
      'compiler': 'GCC',
      'configuration': 'Debug',
      'cpu_or_gpu': 'CPU',
      'cpu_or_gpu_value': 'AVX',
      'is_trybot': False,
      'model': 'Link',
      'os': 'ChromeOS',
      'role': 'Test',
    },
    'configuration': 'Debug',
    'device_cfg': 'link',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': True,
    'env': {
      'GYP_DEFINES':
          'skia_arch_type=x86_64 skia_gpu=0 skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
  'Test-Ubuntu-Clang-GCE-CPU-AVX2-x86_64-Coverage-Trybot': {
    'build_targets': [
      'dm',
    ],
    'builder_cfg': {
      'arch': 'x86_64',
      'compiler': 'Clang',
      'configuration': 'Coverage',
      'cpu_or_gpu': 'CPU',
      'cpu_or_gpu_value': 'AVX2',
      'is_trybot': True,
      'model': 'GCE',
      'os': 'Ubuntu',
      'role': 'Test',
    },
    'configuration': 'Coverage',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': False,
    'do_test_steps': True,
    'env': {
      'CC': '/usr/bin/clang-3.6',
      'CXX': '/usr/bin/clang++-3.6',
      'GYP_DEFINES':
          ('skia_arch_type=x86_64 skia_clang_build=1 skia_gpu=0 skia_warnings'
           '_as_errors=0'),
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': False,
    'upload_perf_results': False,
  },
  'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug': {
    'build_targets': [
      'dm',
      'nanobench',
    ],
    'builder_cfg': {
      'arch': 'x86_64',
      'compiler': 'GCC',
      'configuration': 'Debug',
      'cpu_or_gpu': 'CPU',
      'cpu_or_gpu_value': 'AVX2',
      'is_trybot': False,
      'model': 'GCE',
      'os': 'Ubuntu',
      'role': 'Test',
    },
    'configuration': 'Debug',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': True,
    'env': {
      'GYP_DEFINES':
          'skia_arch_type=x86_64 skia_gpu=0 skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
  'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Release-TSAN': {
    'build_targets': [
      'dm',
    ],
    'builder_cfg': {
      'arch': 'x86_64',
      'compiler': 'GCC',
      'configuration': 'Release',
      'cpu_or_gpu': 'CPU',
      'cpu_or_gpu_value': 'AVX2',
      'extra_config': 'TSAN',
      'is_trybot': False,
      'model': 'GCE',
      'os': 'Ubuntu',
      'role': 'Test',
    },
    'configuration': 'Release',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': False,
    'do_test_steps': True,
    'env': {
      'GYP_DEFINES':
          'skia_arch_type=x86_64 skia_gpu=0 skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': False,
    'upload_perf_results': False,
  },
  'Test-Ubuntu-GCC-ShuttleA-GPU-GTX550Ti-x86_64-Debug-ZeroGPUCache': {
    'build_targets': [
      'dm',
      'nanobench',
    ],
    'builder_cfg': {
      'arch': 'x86_64',
      'compiler': 'GCC',
      'configuration': 'Debug',
      'cpu_or_gpu': 'GPU',
      'cpu_or_gpu_value': 'GTX550Ti',
      'extra_config': 'ZeroGPUCache',
      'is_trybot': False,
      'model': 'ShuttleA',
      'os': 'Ubuntu',
      'role': 'Test',
    },
    'configuration': 'Debug',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': True,
    'env': {
      'GYP_DEFINES': 'skia_arch_type=x86_64 skia_warnings_as_errors=0',
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
  'Test-Ubuntu-GCC-ShuttleA-GPU-GTX550Ti-x86_64-Release-Valgrind': {
    'build_targets': [
      'dm',
    ],
    'builder_cfg': {
      'arch': 'x86_64',
      'compiler': 'GCC',
      'configuration': 'Release',
      'cpu_or_gpu': 'GPU',
      'cpu_or_gpu_value': 'GTX550Ti',
      'extra_config': 'Valgrind',
      'is_trybot': False,
      'model': 'ShuttleA',
      'os': 'Ubuntu',
      'role': 'Test',
    },
    'configuration': 'Release',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': True,
    'env': {
      'GYP_DEFINES':
          ('skia_arch_type=x86_64 skia_release_optimization_level=1 skia_warn'
           'ings_as_errors=0'),
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': False,
    'upload_perf_results': False,
  },
  'Test-iOS-Clang-iPad4-GPU-SGX554-Arm7-Debug': {
    'build_targets': [
      'iOSShell',
    ],
    'builder_cfg': {
      'arch': 'Arm7',
      'compiler': 'Clang',
      'configuration': 'Debug',
      'cpu_or_gpu': 'GPU',
      'cpu_or_gpu_value': 'SGX554',
      'is_trybot': False,
      'model': 'iPad4',
      'os': 'iOS',
      'role': 'Test',
    },
    'configuration': 'Debug',
    'dm_flags': [
      '--dummy-flags',
    ],
    'do_perf_steps': True,
    'do_test_steps': True,
    'env': {
      'CC': '/usr/bin/clang',
      'CXX': '/usr/bin/clang++',
      'GYP_DEFINES':
          ('skia_arch_type=arm skia_clang_build=1 skia_os=ios skia_warnings_a'
           's_errors=0'),
    },
    'nanobench_flags': [
      '--dummy-flags',
    ],
    'upload_dm_results': True,
    'upload_perf_results': False,
  },
}
