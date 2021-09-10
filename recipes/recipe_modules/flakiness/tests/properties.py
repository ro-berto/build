# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'flakiness',
    'recipe_engine/assertions',
]


def RunSteps(api):
  id_tests = api.flakiness.using_test_identifier
  api.assertions.assertEqual(id_tests, True)


def GenTests(api):

  yield api.test(
      'basic',
      api.flakiness(identify_new_tests=True),
      api.post_process(post_process.DropExpectation),
  )
