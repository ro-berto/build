# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'profiles',
]


def RunSteps(api):
  api.profiles.find_merge_errors()


def GenTests(api):

  yield api.test(
      'basic',
      api.post_process(post_process.MustRun, 'Finding profile merge errors'),
      api.post_process(post_process.DropExpectation),
  )
