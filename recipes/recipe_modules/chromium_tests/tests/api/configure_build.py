# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.config import Dict
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'depot_tools/gclient',
    'recipe_engine/assertions',
    'recipe_engine/properties',
]

PROPERTIES = {
    'expected_gclient_vars': Property(kind=Dict(), default={}),
}


def RunSteps(api, expected_gclient_vars):
  _, builder_config = api.chromium_tests_builder_config.lookup_builder()
  api.chromium_tests.configure_build(builder_config)
  for k, v in expected_gclient_vars.items():
    api.assertions.assertEqual(v, api.gclient.c.solutions[0].custom_vars.get(k))


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
      'cros-boards-with-vm-optimized-qemu-images',
      api.properties(
          expected_gclient_vars={
              'cros_boards_with_qemu_images': 'amd64-generic-vm'
          },),
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
                              'TARGET_PLATFORM':
                                  'chromeos',
                              'CROS_BOARDS_WITH_QEMU_IMAGES':
                                  'amd64-generic-vm',
                          },
                      ),
              },
          })),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cros-boards-with-non-optimized-qemu-images',
      api.properties(
          expected_gclient_vars={
              'cros_boards_with_qemu_images': 'amd64-generic'
          },),
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
                              'CROS_BOARDS_WITH_QEMU_IMAGES': 'amd64-generic',
                          },
                      ),
              },
          })),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cros-boards-with-qemu-images-pre-96',
      api.properties(
          expected_gclient_vars={
              'cros_boards_with_qemu_images': 'amd64-generic'
          },),
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          project='chromium-m95',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          chromium_config_kwargs={
                              'TARGET_PLATFORM':
                                  'chromeos',
                              'CROS_BOARDS_WITH_QEMU_IMAGES':
                                  'amd64-generic-vm',
                          },
                      ),
              },
          })),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'reclient',
      api.properties(
          expected_gclient_vars={
              'checkout_reclient': 'True',
          },
          **{
              '$build/reclient': {
                  'instance': 'fake-reclient-instance',
              },
          }),
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
