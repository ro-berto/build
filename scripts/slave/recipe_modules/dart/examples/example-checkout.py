# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'dart',
  'recipe_engine/buildbucket',
  'recipe_engine/platform',
  'recipe_engine/properties',
]

def RunSteps(api):
  if 'clobber' in api.properties:
    api.dart.checkout(True)
    return

  api.dart.checkout(False, revision=api.buildbucket.gitiles_commit.id)

def GenTests(api):
  yield (api.test('clobber') + api.properties(clobber='True'))

  yield (api.test('bot_update-retry') +
      api.buildbucket.ci_build(
          builder='analyzer-linux-release-be',
          revision='deadbeef',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('bot_update', retcode=1) +
      api.post_process(post_process.MustRun, 'bot_update (2)') +
      api.post_process(post_process.DropExpectation))

  yield (api.test('bot_update-no-retry') +
      api.buildbucket.ci_build(
          builder='analyzer-linux-release-be',
          revision='',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('bot_update', retcode=1) +
      api.post_process(post_process.DoesNotRun, 'bot_update (2)') +
      api.post_process(post_process.DropExpectation))
