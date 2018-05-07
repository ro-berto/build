# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'goma',
  'recipe_engine/properties',
  'recipe_engine/runtime',
]


def RunSteps(api):
  api.goma.ensure_goma(canary=True)
  api.goma.start()
  api.goma.stop()


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(buildername='test_buildername')
  )

  yield (
    api.test('luci_and_experimental') +
    api.properties(buildername='test_buildername') +
    api.runtime(is_luci=True, is_experimental=True)
  )
