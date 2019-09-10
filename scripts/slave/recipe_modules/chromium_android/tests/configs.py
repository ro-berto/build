# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
  'chromium',
  'chromium_android',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'))
  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)

  api.chromium_android.set_config(
      api.properties.get('android_config', 'main_builder'))
  for config in api.properties.get('android_apply_config', []):
    api.chromium_android.apply_config(config)


def GenTests(api):
  yield api.test(
      'cronet_builder',
      api.properties(chromium_config='cronet_builder'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cronet_official',
      api.properties(chromium_config='cronet_official'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non_device_wipe_provisioning',
      api.properties(chromium_config='non_device_wipe_provisioning'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'errorprone',
      api.properties(chromium_apply_config=['errorprone']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'main_builder_mb',
      api.properties(android_apply_config=['main_builder_mb']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'main_builder_rel_mb',
      api.properties(
          android_apply_config=['main_builder_rel_mb'],
          chromium_config='main_builder_rel_mb'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'clang_builder_mb',
      api.properties(
          android_apply_config=['clang_builder_mb'],
          chromium_config='clang_builder_mb'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'clang_builder_mb_x64',
      api.properties(android_apply_config=['clang_builder_mb_x64']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'x86_builder_mb',
      api.properties(
          android_apply_config=['x86_builder_mb'],
          chromium_config='x86_builder_mb'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mipsel_builder_mb',
      api.properties(
          android_apply_config=['mipsel_builder_mb'],
          chromium_config='mipsel_builder_mb'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'x64_builder_mb',
      api.properties(
          android_apply_config=['x64_builder_mb'],
          chromium_config='x64_builder_mb'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'arm64_builder',
      api.properties(android_apply_config=['arm64_builder']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'arm64_builder_mb',
      api.properties(
          android_apply_config=['arm64_builder_mb'],
          chromium_config='arm64_builder_mb'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'arm64_builder_rel_mb',
      api.properties(
          android_apply_config=['arm64_builder_rel_mb'],
          chromium_config='arm64_builder_rel_mb'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'incremental_coverage_builder_tests',
      api.properties(
          android_config='incremental_coverage_builder_tests',
          chromium_config='incremental_coverage_builder_tests'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'chromium_perf',
      api.properties(android_apply_config=['chromium_perf']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cast_builder',
      api.properties(
          chromium_config='cast_builder',
          android_apply_config=['cast_builder']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'restart_usb',
      api.properties(android_apply_config=['restart_usb']),
      api.post_process(post_process.DropExpectation),
  )
