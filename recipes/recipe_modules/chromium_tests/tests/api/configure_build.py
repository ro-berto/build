# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
]

def RunSteps(api):
  _, builder_config = api.chromium_tests_builder_config.lookup_builder()
  api.chromium_tests.configure_build(builder_config)

def GenTests(api):
  yield api.test(
      'android_apply_config',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          android_config='main_builder_mb',
                          chromium_config='chromium',
                          gclient_config='chromium',
                          test_results_config='public_server',
                          android_apply_config=['use_devil_provision'],
                      ),
              },
          })),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'target-cros-boards',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          chromium_config_kwargs={
                              'TARGET_PLATFORM': 'chromeos',
                              'TARGET_CROS_BOARDS': 'fake-board',
                          },
                      ),
              },
          })),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cros-boards-with-qemu-images',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          chromium_config_kwargs={
                              'TARGET_PLATFORM': 'chromeos',
                              'CROS_BOARDS_WITH_QEMU_IMAGES': 'fake-board',
                          },
                      ),
              },
          })),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
