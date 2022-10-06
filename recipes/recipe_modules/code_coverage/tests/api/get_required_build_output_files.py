# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build import chromium_swarming
from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build.code_coverage import constants

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'profiles',
    'recipe_engine/assertions',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

PROPERTIES = {
    'expected_paths': Property(kind=list),
    'target_platform': Property(kind=str)
}


def RunSteps(api, expected_paths, target_platform):
  api.chromium.set_config('chromium', TARGET_PLATFORM=target_platform)

  tests = [
      steps.SwarmingGTestTestSpec.create('browser_tests').get_test(
          api.chromium_tests),
      steps.SwarmingGTestTestSpec.create('android_browsertests').get_test(
          api.chromium_tests)
  ]

  api.code_coverage.src_dir = api.chromium_checkout.src_dir
  api.code_coverage.build_dir = api.chromium_checkout.src_dir.join(
      'out', 'Release')
  file_paths = api.code_coverage.get_required_build_output_files(tests)

  str_file_paths = [str(f) for f in file_paths]
  str_expected_paths = [str(f) for f in expected_paths]
  api.assertions.assertCountEqual(str_file_paths, str_expected_paths)


def GenTests(api):

  yield api.test(
      'basic',
      api.chromium.try_build(builder='linux-rel'),
      api.properties(
          expected_paths=[
              api.chromium_checkout.src_dir.join('out/Release/browser_tests')
          ],
          target_platform='linux'),
      api.path.exists(
          api.chromium_checkout.src_dir.join('out/Release/browser_tests')),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  android_test_path = (
      'out/Release/lib.unstripped/libandroid_browsertests__library.so')
  jacoco_file = ('broker_java__process_host__jacoco_sources.json')

  yield api.test(
      'android',
      api.chromium.try_build(
          builder_group='tryserver.chromium.android',
          builder='android-12-x64-rel'),
      api.code_coverage(use_java_coverage=True),
      api.properties(
          expected_paths=[
              api.chromium_checkout.src_dir.join(android_test_path),
              api.chromium_checkout.src_dir.join(
                  'out/Release/{}'.format(jacoco_file)),
              api.chromium_checkout.src_dir.join('out/Release/{}'.format(
                  'chrome/browser/java__process_device.filter.jar'))
          ],
          target_platform='android'),
      api.path.exists(api.chromium_checkout.src_dir.join(android_test_path)),
      api.override_step_data(
          'Get all unstripped artifacts paths',
          api.json.output(['[CACHE]/builder/src/{}'.format(android_test_path)
                          ])),
      api.override_step_data(
          'Get jacoco and jar files for java coverage',
          api.json.output([
              '[CACHE]/builder/src/out/Release/{}'.format(jacoco_file),
              ('[CACHE]/builder/src/out/Release/chrome/browser/'
               'java__process_device.filter.jar'),
          ]),
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
