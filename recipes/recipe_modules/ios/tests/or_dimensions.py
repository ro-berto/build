# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'ios',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]


def RunSteps(api):
  api.ios.swarming_service_account = 'other-service-account'
  api.ios.read_build_config()
  tasks = api.ios.isolate()
  for task in tasks:
    test = api.ios.generate_test_from_task(task)
    if test:
      test.pre_run(api.ios.m, suffix='')


def GenTests(api):
  yield api.test(
      'basic',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=0,
          bot_id='fake-vm',
      ),
      api.ios.make_test_build_config({
          'gn_args': [
              'is_debug=true',
              'target_cpu="x64"',
          ],
          'xcode build version':
              '11m382q',
          'tests': [{
              'app': 'fake test 0',
              'device type': 'fake device 0',
              'os': '12.0',
              'host os': 'Mac-10.14.3|Mac-10.13.6',
          },],
      }),
      # Check that we have both the main dimensions and the optional
      # dimensions set.
      api.post_process(
          post_process.StepCommandContains,
          ('[trigger] fake test 0 (fake device 0 iOS 12.0) on Mac-10.14.3 or'
           ' Mac-10.13.6'), ['--dimension', 'os', 'Mac-10.14.3|Mac-10.13.6']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
