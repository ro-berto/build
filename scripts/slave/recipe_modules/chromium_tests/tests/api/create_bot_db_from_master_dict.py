# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
  'chromium_tests',
]


def RunSteps(api):
  api.chromium_tests.create_bot_db_from_master_dict('test_mastername', {})


def GenTests(api):
  yield (
      api.test('basic') +
      api.post_process(post_process.DropExpectation)
  )
