# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
from recipe_engine import post_process


DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_name = api.buildbucket.builder_name
  bot_id = api.chromium_tests.create_bot_id(api.properties['mastername'],
                                            builder_name,
                                            api.properties.get('testername'))
  assert bot_id['buildername'] == builder_name
  assert bot_id.get('tester') == api.properties.get('testername')


def GenTests(api):
  yield api.test(
      'without_testername',
      api.chromium.ci_build(mastername='fake.master', builder='builder'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_testername',
      api.chromium.ci_build(mastername='fake.master', builder='builder'),
      api.properties(testername='tester'),
      api.post_process(post_process.DropExpectation),
  )
