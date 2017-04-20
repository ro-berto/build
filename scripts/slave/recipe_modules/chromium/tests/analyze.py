# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'filter',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  api.filter.analyze(
      affected_files=[],
      test_targets=[],
      additional_compile_targets=[],
      config_file_name='config.json')


def GenTests(api):
  yield (
      api.test('basic') +
      api.override_step_data('analyze', api.chromium.analyze_builds_nothing)
  )
