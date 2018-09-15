# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
from recipe_engine import post_process


DEPS = [
    'chromium_tests',
    'recipe_engine/properties',
]


def RunSteps(api):
  bot_id = api.chromium_tests.create_bot_id(
      api.properties['mastername'], api.properties['buildername'],
      api.properties.get('testername'))
  assert bot_id['buildername'] == api.properties['buildername']
  assert bot_id.get('tester') == api.properties.get('testername')


def GenTests(api):
  yield (
      api.test('without_testername') +
      api.properties.generic(
          mastername='fake.master',
          buildername='builder') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('with_testername') +
      api.properties.generic(
          mastername='fake.master',
          buildername='builder',
          testername='tester') +
      api.post_process(post_process.DropExpectation)
  )
