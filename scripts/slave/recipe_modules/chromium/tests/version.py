# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'recipe_engine/assertions',
]

def RunSteps(api):
  version = api.chromium.get_version()
  api.assertions.assertEqual(version, {
      'MAJOR': '123',
      'MINOR': '1',
      'BUILD': '9876',
      'PATCH': '2',
  })

def GenTests(api):
  yield (
      api.test('override_version') +
      api.chromium.override_version(
          major=123, minor=1, build=9876, patch=2) +
      api.post_process(post_process.DropExpectation))
