# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromite',
    'ndk',
]


def RunSteps(api):
  api.chromite.set_config('chromite_config')


def GenTests(api):
  yield (
    api.test('basic') +
    api.post_process(post_process.DropExpectation)
  )
