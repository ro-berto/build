# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

DEPS = [
    'bisect_tester',
    'properties',
    'step',
    'raw_io',
]


# This file is meant only to provide missing code coverage for this module
# Typically, the module is covered by the chromium recipe.
def GenSteps(api):
  try:
    api.step('Fake failing test.', ['dummy_command.py'])
  except api.step.StepFailure as failure:
    api.bisect_tester.upload_failure(failure)

def GenTests(api):
  basic_test = api.test('basic')
  basic_test += api.step_data(
      'Fake failing test.',
      stdout=api.raw_io.output('Test failed'),
      stderr=api.raw_io.output('Exception trace.'),
      retcode=4)
  basic_test += api.step_data(
      'saving json to temp file',
      stdout=api.raw_io.output('dummy_location.json'))
  basic_test += api.properties(job_name='dummy')
  yield basic_test


