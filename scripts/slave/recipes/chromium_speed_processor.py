# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/step',
]

from recipe_engine import post_process


def RunSteps(api):
  api.step('test step', ['echo', 'data-processor'])


def GenTests(api):
  yield (api.test('try_test') +
         api.post_check(lambda check, steps: check('test step' in steps)) +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             post_process.DropExpectation))
