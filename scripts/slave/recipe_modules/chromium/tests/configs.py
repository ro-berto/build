# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_BITS=api.properties.get('target_bits', 64))

  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)


def GenTests(api):
  yield (
      api.test('gn') +
      api.properties(chromium_apply_config=['gn']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('gn_for_uploads') +
      api.properties(chromium_apply_config=['gn_for_uploads']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('ios') +
      api.platform('mac', 64) +
      api.properties(target_platform='ios') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('goma_canary') +
      api.properties(chromium_apply_config=['goma_canary']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('goma_use_local') +
      api.properties(chromium_apply_config=['goma_use_local']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('gcc') +
      api.properties(chromium_config='gcc') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('no_dump_symbols') +
      api.properties(chromium_apply_config=['no_dump_symbols']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('isolation_mode_noop') +
      api.properties(chromium_apply_config=['isolation_mode_noop']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromeos_with_codecs') +
      api.properties(chromium_apply_config=['chromeos_with_codecs']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromeos') +
      api.properties(chromium_apply_config=['chromeos']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('ozone') +
      api.properties(chromium_apply_config=['ozone']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('analysis') +
      api.properties(chromium_apply_config=['analysis']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('asan_symbolized') +
      api.properties(chromium_apply_config=['asan_symbolized']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('msan_no_origin_tracking') +
      api.properties(chromium_apply_config=['msan_no_origin_tracking']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('msan_full_origin_tracking') +
      api.properties(chromium_apply_config=['msan_full_origin_tracking']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('prebuilt_instrumented_libraries') +
      api.properties(
          chromium_apply_config=['prebuilt_instrumented_libraries']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('trybot_flavor') +
      api.properties(chromium_apply_config=['trybot_flavor']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_win_clang_official') +
      api.platform('win', 64) +
      api.properties(
          chromium_config='chromium_win_clang_official',
          target_platform='win') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_win_clang_official_tot') +
      api.properties(chromium_config='chromium_win_clang_official_tot') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_win_clang_asan') +
      api.properties(chromium_config='chromium_win_clang_asan') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_win_clang_asan_tot_coverage') +
      api.properties(chromium_config='chromium_win_clang_asan_tot_coverage') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('clang_tot_linux') +
      api.properties(chromium_config='clang_tot_linux') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('clang_tot_mac') +
      api.properties(chromium_config='clang_tot_mac') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('clang_tot_linux_asan') +
      api.properties(chromium_config='clang_tot_linux_asan') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_linux_ubsan') +
      api.properties(chromium_config='chromium_linux_ubsan') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_linux_ubsan_vptr') +
      api.properties(chromium_config='chromium_linux_ubsan_vptr') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('clang_tot_linux_ubsan_vptr') +
      api.properties(chromium_config='clang_tot_linux_ubsan_vptr') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('clang_tot_mac_asan') +
      api.platform('mac', 64) +
      api.properties(
          chromium_config='clang_tot_mac_asan',
          target_platform='mac') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('clang_tot_android_asan') +
      api.properties(chromium_config='clang_tot_android_asan') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('clang_tot_android_dbg') +
      api.properties(chromium_config='clang_tot_android_dbg') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_linux_asan') +
      api.properties(chromium_config='chromium_linux_asan') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_linux_asan_no_test_args') +
      api.properties(chromium_config='chromium_linux_asan_no_test_args') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_mac_asan') +
      api.properties(chromium_config='chromium_mac_asan') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_mac_mac_views') +
      api.properties(chromium_config='chromium_mac_mac_views') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_tsan2') +
      api.properties(chromium_config='chromium_tsan2') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_chromiumos_asan') +
      api.properties(chromium_config='chromium_chromiumos_asan') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_official_linux') +
      api.properties(
          chromium_config='chromium_official',
          target_platform='linux') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_official_win') +
      api.platform('win', 64) +
      api.properties(
          chromium_config='chromium_official',
          target_platform='win') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('blink_logging_on') +
      api.properties(chromium_apply_config=['blink_logging_on']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('android_clang') +
      api.properties(chromium_config='android_clang') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('android_asan') +
      api.properties(chromium_config='android_asan') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('v8_optimize_medium') +
      api.properties(chromium_apply_config=['v8_optimize_medium']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('v8_verify_heap') +
      api.properties(chromium_apply_config=['v8_verify_heap']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('v8_hybrid_arm') +
      api.properties(chromium_apply_config=['v8_hybrid_arm']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('enable_ipc_fuzzer') +
      api.properties(chromium_apply_config=['enable_ipc_fuzzer']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('cast_linux') +
      api.properties(chromium_config='cast_linux') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('internal_gles2_conform_tests') +
      api.properties(chromium_apply_config=['internal_gles2_conform_tests']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('build_angle_deqp_tests') +
      api.properties(chromium_apply_config=['build_angle_deqp_tests']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('download_vr_test_apks') +
      api.properties(chromium_apply_config=['download_vr_test_apks']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('fetch_telemetry_dependencies') +
      api.properties(chromium_apply_config=['fetch_telemetry_dependencies']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('mac_toolchain') +
      api.platform('mac', 64) +
      api.properties(
          target_platform='mac',
          chromium_apply_config=['mac_toolchain'],
      ) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('ios_toolchain') +
      api.platform('mac', 64) +
      api.properties(
          target_platform='ios',
          chromium_apply_config=['mac_toolchain'],
      ) +
      api.post_process(post_process.DropExpectation)
  )
