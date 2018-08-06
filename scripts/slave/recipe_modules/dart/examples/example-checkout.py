# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (DropExpectation, MustRun)

DEPS = [
  'dart',
  'recipe_engine/platform',
  'recipe_engine/properties',
]

def RunSteps(api):
  if 'clobber' in api.properties:
    api.dart.checkout(True)
    return

  api.dart.checkout(False)

def GenTests(api):
  yield (api.test('clobber') + api.properties(clobber='True'))

  yield (api.test('bot_update-retry') + api.properties(
      buildername='analyzer-linux-release-be') +
      api.step_data('bot_update', retcode=1) +
      api.post_process(MustRun, 'bot_update (2)') +
      api.post_process(DropExpectation))
