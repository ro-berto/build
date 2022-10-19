# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

RESULTS_URL = 'https://chromeperf.appspot.com'


def stock_config(name, config='Release', target_bits=64, staging=True,
                 **kwargs):
  if 'mac' in name.lower():
    platform = 'mac'
  elif 'win' in name.lower():
    platform = 'win'
  elif 'linux' in name.lower():
    platform = 'linux'
  assert (platform)

  bot_config = {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb',],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': target_bits,
      },
      'simulation_platform': platform,
  }
  bot_config.update(**kwargs)
  if staging:
    bot_config['test_results_config'] = 'staging_server'
  return name, builder_spec.BuilderSpec.create(**bot_config)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.fyi.star
# * VR Linux
# * Win11 Tests x64
# * ios-simulator-cronet
# * linux-chromeos-js-code-coverage
# * mac-osxbeta-rel

SPEC = {
    'Mac Builder Next':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'fuchsia-fyi-arm64-femu':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_arm64', 'fuchsia_arm64_host'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            # Serialize the tests to limit capacity usage.
            serialize_tests=True,
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'fuchsia-fyi-arm64-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_arm64', 'fuchsia_arm64_host'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            # Serialize the tests to limit capacity usage.
            serialize_tests=True,
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'fuchsia-fyi-x64-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            # Serialize the tests to limit capacity usage.
            serialize_tests=True,
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'lacros-amd64-generic-rel-fyi':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            # Some tests on this bot depend on being unauthenticated with GS, so
            # don't run the tests inside a luci-auth context to avoid having the
            # BOTO config setup for the task's service account.
            # TODO(crbug.com/1217155): Fix this.
            chromium_apply_config=['mb', 'mb_no_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos', 'checkout_lacros_sdk'],
            chromium_config_kwargs={
                'TARGET_BITS': 64,
                'TARGET_CROS_BOARDS': 'eve',
                'CROS_BOARDS_WITH_QEMU_IMAGES': 'amd64-generic',
                'TARGET_PLATFORM': 'chromeos',
            },
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'linux-backuprefptr-x64-fyi-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'linux',
            },
            gclient_apply_config=['enable_reclient'],
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'win-backuprefptr-x64-fyi-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'win',
            },
            simulation_platform='win',
            test_results_config='staging_server',
        ),
    'win-backuprefptr-x86-fyi-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'win',
            },
            simulation_platform='win',
            test_results_config='staging_server',
        ),
    'android-backuprefptr-arm64-fyi-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'android-backuprefptr-arm-fyi-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'linux-paeverywhere-x64-fyi-dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'linux',
            },
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'linux-paeverywhere-x64-fyi-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'linux',
            },
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'mac-paeverywhere-x64-fyi-dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            simulation_platform='mac',
            test_results_config='staging_server',
        ),
    'mac-paeverywhere-x64-fyi-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            simulation_platform='mac',
            test_results_config='staging_server',
        ),
    'Site Isolation Android':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_mb',
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    # For building targets instrumented for code coverage.
    'linux-code-coverage':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'fuchsia-code-coverage':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64', 'use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'mac-code-coverage':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'win32-arm64-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_ARCH': 'arm'
            },
            simulation_platform='win',
        ),
    'Win 10 Fast Ring':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='win',
        ),
    'linux-autofill-captured-sites-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'linux',
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'linux-chromeos-code-coverage':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['chromeos', 'use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'linux-lacros-code-coverage':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos', 'use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'linux-lacros-version-skew-fyi':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'linux-example-builder':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            gclient_apply_config=['enable_reclient'],
            execution_mode=builder_spec.COMPILE_AND_TEST,
            simulation_platform='linux',
        ),
    'ios-webkit-tot':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=['ios_webkit_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
        ),
    'ios13-beta-simulator':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios13-sdk-device':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
        ),
    'ios13-sdk-simulator':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios15-beta-simulator':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios15-sdk-simulator':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios-simulator-multi-window':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios-simulator-code-coverage':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'android-code-coverage':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=['download_vr_test_apks', 'mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'android-code-coverage-native':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=['download_vr_test_apks', 'mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'android', 'use_clang_coverage', 'enable_reclient'
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'win10-code-coverage':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'linux-upload-perfetto':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            gclient_apply_config=['enable_reclient'],
            simulation_platform='linux',
        ),
    'mac-upload-perfetto':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'win-upload-perfetto':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    # Start - Reclient migration phase 2, block 1 shadow builders
    'Linux ASan LSan Builder (reclient shadow)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium_asan',
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            # This doesn't affect the build, but ensures that trybots get
            # the right runtime flags.
            chromium_apply_config=['lsan', 'mb'],
            simulation_platform='linux',
            # From chromium_memory.py, _chromium_memory_spec
            build_gs_bucket='chromium-memory-archive',
        ),
    'Linux CFI (reclient shadow)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            # From chromium_memory.py, _chromium_memory_spec
            build_gs_bucket='chromium-memory-archive',
        ),
    'Linux MSan Builder (reclient shadow)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium_msan',
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            # From chromium_memory.py, _chromium_memory_spec
            build_gs_bucket='chromium-memory-archive',
        ),
    'CFI Linux CF (reclient shadow)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            # Not a ToT bot so no clang_tot gclient_apply_config.
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=False,
            test_results_config='staging_server',
            simulation_platform='linux',
            # From chromium_clang.py, _chromium_clang_spec
            build_gs_bucket='chromium-clang-archive',
        ),
    'WebKit Linux ASAN (reclient shadow)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium_clang',
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['asan', 'mb'],
            simulation_platform='linux',
            # From chromium_memory.py, _chromium_memory_spec
            build_gs_bucket='chromium-memory-archive',
        ),
    'WebKit Linux MSAN (reclient shadow)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium_clang',
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['asan', 'mb'],
            simulation_platform='linux',
            # From chromium_memory.py, _chromium_memory_spec
            build_gs_bucket='chromium-memory-archive',
        ),
    'WebKit Linux Leak (reclient shadow)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['mb'],
            simulation_platform='linux',
            # From chromium_memory.py, _chromium_memory_spec
            build_gs_bucket='chromium-memory-archive',
        ),
    'Mojo Linux (reclient shadow)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    # End - Reclient migration phase 2, block 1 shadow builders
    'Linux Builder (j-500) (reclient)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'use_clang_coverage',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Win x64 Builder (reclient)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'use_clang_coverage',
                'enable_reclient',
                'reclient_test',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'Win x64 Builder (reclient)(cross)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'use_clang_coverage',
                'enable_reclient',
                'reclient_test',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'chromeos-amd64-generic-rel (reclient)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos', 'enable_reclient'],
            chromium_config_kwargs={
                'TARGET_BITS':
                    64,
                'CROS_BOARDS_WITH_QEMU_IMAGES':
                    'amd64-generic:amd64-generic-vm',
                'TARGET_PLATFORM':
                    'chromeos',
            },
            simulation_platform='linux',
        ),
    # TODO(crbug.com/1235218): remove after the migration.
    'chromeos-amd64-generic-rel (reclient compare)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos', 'enable_reclient'],
            chromium_config_kwargs={
                'TARGET_BITS':
                    64,
                'CROS_BOARDS_WITH_QEMU_IMAGES':
                    'amd64-generic:amd64-generic-vm',
                'TARGET_PLATFORM':
                    'chromeos',
            },
            simulation_platform='linux',
        ),
    'chromeos-amd64-generic-rel (goma cache silo)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'goma_enable_cache_silo'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'TARGET_BITS':
                    64,
                'CROS_BOARDS_WITH_QEMU_IMAGES':
                    'amd64-generic:amd64-generic-vm',
                'TARGET_PLATFORM':
                    'chromeos',
            },
            simulation_platform='linux',
        ),
    'lacros-amd64-generic-rel (reclient)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'chromeos', 'enable_reclient', 'checkout_lacros_sdk'
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'chromeos',
                'TARGET_CROS_BOARDS': 'amd64-generic',
            },
            simulation_platform='linux',
        ),
    'lacros-amd64-generic-rel (goma cache silo)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'goma_enable_cache_silo'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos', 'checkout_lacros_sdk'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'chromeos',
                'TARGET_CROS_BOARDS': 'amd64-generic',
            },
            simulation_platform='linux',
        ),
    'linux-lacros-builder-rel (reclient)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'linux-lacros-builder-rel (goma cache silo)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'goma_enable_cache_silo'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    # TODO(crbug.com/1244441): remove after the migration.
    'Mac Builder (reclient)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'use_clang_coverage',
                'enable_reclient',
                'reclient_test',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'Mac Builder (reclient compare)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'use_clang_coverage',
                'enable_reclient',
                'reclient_test',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    # TODO(crbug.com/1252626): remove after the migration.
    'mac-arm64-on-arm64-rel-reclient':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
                'reclient_test',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'linux-headless-shell-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            gclient_apply_config=['enable_reclient'],
            execution_mode=builder_spec.COMPILE_AND_TEST,
            simulation_platform='linux',
        ),
}

SPEC.update([
    stock_config('Linux Viz', gclient_apply_config=['enable_reclient']),
    stock_config(
        'linux-annotator-rel', gclient_apply_config=['enable_reclient']),
    stock_config(
        'linux-chromeos-annotator-rel', gclient_apply_config=['chromeos']),
    stock_config(
        'linux-ash-chromium-builder-fyi-rel',
        gclient_apply_config=['chromeos', 'enable_reclient']),
    stock_config('linux-blink-animation-use-time-delta', config='Debug'),
    stock_config(
        'linux-blink-heap-verification',
        gclient_apply_config=['enable_reclient']),
    stock_config(
        'linux-blink-v8-sandbox-future-dbg',
        config='Debug',
        gclient_apply_config=['enable_reclient']),
    stock_config('linux-fieldtrial-rel'),
    stock_config(
        'linux-lacros-builder-fyi-rel', gclient_apply_config=['chromeos']),
    stock_config('linux-lacros-dbg-fyi', gclient_apply_config=['chromeos']),
    stock_config(
        'linux-lacros-dbg-tests-fyi',
        execution_mode=builder_spec.TEST,
        parent_buildername='linux-lacros-dbg-fyi'),
    stock_config(
        'linux-lacros-tester-fyi-rel',
        execution_mode=builder_spec.TEST,
        parent_buildername='linux-lacros-builder-fyi-rel'),
    stock_config(
        'linux-perfetto-rel', gclient_apply_config=['enable_reclient']),
    stock_config('linux-tcmalloc-rel'),
    stock_config('linux-wpt-fyi-rel', gclient_apply_config=['enable_reclient']),
    # Despite the FYI name, these are the "MVP bots" used by teams:
    # https://source.chromium.org/chromium/chromium/src/+/main:docs/testing/web_platform_tests_wptrunner.md;l=64;drc=5ce5d37c5ebfbd3b658f1f68173be7573a95d0ea
    stock_config(
        'linux-wpt-identity-fyi-rel',
        staging=False,
        gclient_apply_config=['enable_reclient']),
    stock_config(
        'linux-wpt-input-fyi-rel',
        staging=False,
        gclient_apply_config=['enable_reclient']),
    stock_config('mac-hermetic-upgrade-rel'),
    stock_config('win-annotator-rel'),
])

# Many of the FYI specs are made by transforming specs from other files, so
# rather than have to do 2 different things for specs based on other specs and
# specs created within this file, just evolve all of the specs afterwards
for name, spec in SPEC.items():
  SPEC[name] = spec.evolve(build_gs_bucket='chromium-fyi-archive')
