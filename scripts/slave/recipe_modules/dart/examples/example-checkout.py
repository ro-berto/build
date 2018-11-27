# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'dart',
  'recipe_engine/platform',
  'recipe_engine/properties',
]

def RunSteps(api):
  if 'clobber' in api.properties:
    api.dart.checkout(True)
    return

  api.dart.checkout(False, revision=api.properties.get('revision'))

def GenTests(api):
  yield (api.test('clobber') + api.properties(clobber='True'))

  yield (api.test('bot_update-retry') + api.properties(
        buildername='analyzer-linux-release-be',
        revision='deadbeef') +
      api.step_data('bot_update', retcode=1) +
      api.post_process(post_process.MustRun, 'bot_update (2)') +
      api.post_process(post_process.DropExpectation))

  yield (api.test('bot_update-no-retry') + api.properties(
        buildername='analyzer-linux-release-be',
        revision=None) +
      api.step_data('bot_update', retcode=1) +
      api.post_process(post_process.DoesNotRun, 'bot_update (2)') +
      api.post_process(post_process.DropExpectation))
