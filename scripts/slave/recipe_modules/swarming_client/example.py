# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'raw_io',
  'swarming_client',
]


def GenSteps(api):
  # Code coverage for these methods.
  yield api.swarming_client.checkout('master')
  yield api.swarming_client.query_script_version('swarming.py')

  # 'master' had swarming.py at v0.4.4 at the moment of writing this example.
  assert api.swarming_client.get_script_version('swarming.py') >= (0, 4, 4)


def GenTests(api):
  yield (
      api.test('basic') +
      api.step_data(
          'swarming.py --version',
          stdout=api.raw_io.output('0.4.4')))
