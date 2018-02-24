# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'recipe_engine/python',
]

def RunSteps(api):
  version = api.chromium.get_version()
  api.python.succeeding_step(
      'chromium version: {MAJOR}.{MINOR}.{BUILD}.{PATCH}'.format(**version),
      '')

def GenTests(api):
  yield (
      api.test('override_version') +
      api.chromium.override_version(
          major=123, minor=1, build=9876, patch=2) +
      api.post_process(post_process.MustRun, 'chromium version: 123.1.9876.2') +
      api.post_process(post_process.DropExpectation))
