# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium_android',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium_android.git_number(api.properties.get('commitrefs'))


def GenTests(api):
  yield (
      api.test('no_commitrefs') +
      api.post_process(
          post_process.StepCommandRE,
          'git number',
          ['git', 'number']) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('with_commitrefs') +
      api.properties(commitrefs=['01234567', '89abcdef']) +
      api.post_process(
          post_process.StepCommandRE,
          'git number',
          ['git', 'number', '01234567', '89abcdef']) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation))
