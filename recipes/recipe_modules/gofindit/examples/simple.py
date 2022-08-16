# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import StepCommandRE, DropExpectation

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'gofindit',
]


def RunSteps(api):
  api.gofindit.send_result_to_gofindit()


def GenTests(api):
  yield api.test(
      'basic',
      api.post_process(StepCommandRE, 'send_result_to_gofindit',
                       ['echo', 'send_result_to_gofindit']),
      api.post_process(DropExpectation),
  )
