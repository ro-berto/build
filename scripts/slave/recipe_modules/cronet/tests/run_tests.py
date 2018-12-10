# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'chromium_android',
  'cronet',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config('main_builder')
  api.chromium_android.set_config('main_builder')
  api.cronet.run_tests(venv=True)


def GenTests(api):
  # Ensure that cronet_unittests is built and run.
  yield (
      api.test('m65__cronet_unittests') +
      api.properties(
          buildername='generic_cronet_builder',
          buildnumber='1') +
      api.chromium.override_version(major=65) +
      api.post_process(post_process.MustRun, 'cronet_unittests') +
      api.post_process(post_process.DropExpectation))

  # Ensure that cronet_unittests_android is built and run.
  yield (
      api.test('m66__cronet_unittests_android') +
      api.properties(
          buildername='generic_cronet_builder',
          buildnumber='1') +
      api.chromium.override_version(major=66) +
      api.post_process(post_process.MustRun, 'cronet_unittests_android') +
      api.post_process(post_process.DropExpectation))
