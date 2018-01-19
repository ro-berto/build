# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium',
    'chromium_swarming',
    'recipe_engine/properties',
    'recipe_engine/runtime',
]


def RunSteps(api):
  api.chromium.set_config('android', TARGET_PLATFORM='android')

  api.chromium_swarming.configure_swarming(
      'chromium',
      precommit=api.properties['precommit'])


def GenTests(api):
  yield (
      api.test('precommit_cq') +
      api.properties(
          precommit=True,
          patch_project='chromium',
          requester='commit-bot@chromium.org',
          blamelist=['some-user@chromium.org']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('precommit_manual') +
      api.properties(precommit=True, patch_project='chromium') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('postcommit') +
      api.properties(precommit=False) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('experimental') +
      api.properties(precommit=False) +
      api.runtime(is_luci=False, is_experimental=True) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('luci') +
      api.properties(precommit=False) +
      api.runtime(is_luci=True, is_experimental=False) +
      api.post_process(post_process.DropExpectation))
