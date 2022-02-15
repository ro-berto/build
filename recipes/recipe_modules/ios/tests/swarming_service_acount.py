# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'ios',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/swarming',
]

def RunSteps(api):
  api.ios.swarming_service_account = 'other-service-account'
  api.ios.read_build_config()
  tasks = api.ios.isolate()
  for task in tasks:
    test = api.ios.generate_test_from_task(task)
    if test:
      test.pre_run(suffix='')


def GenTests(api):
  yield api.test(
      'basic',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake', builder='ios-builder'),
      api.ios.make_test_build_config({
          'gn_args': [
              'is_debug=true',
              'target_cpu="x64"',
              'use_goma=true',
          ],
          'xcode build version':
              '11m382q',
          'tests': [{
              'app': 'fake test 0',
              'device type': 'fake device 0',
              'os': '12.0',
              'dimensions': [{
                  'os': 'Mac-10.13',
                  'pool': 'Chrome',
              }],
          },],
      }),
      api.post_check(
          api.swarming.check_triggered_request,
          '[trigger] fake test 0 (fake device 0 iOS 12.0)', lambda check, req:
          check(req.service_account == 'other-service-account')),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
