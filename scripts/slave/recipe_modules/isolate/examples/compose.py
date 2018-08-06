# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

DEPS = [
  'isolate',
  'swarming_client',
]


def RunSteps(api):
  api.swarming_client.checkout('master')
  api.isolate.compose(['isolated_hash1', 'isolated_hash2'])


def GenTests(api):
  yield (
      api.test('compose') +
      api.post_process(Filter('compose isolates'))
  )
