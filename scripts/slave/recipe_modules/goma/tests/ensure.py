# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'goma',
  'recipe_engine/properties',
]


def RunSteps(api):
  canary = api.m.properties.get('canary', False)
  api.goma.ensure_goma(canary=canary)


def GenTests(api):
  yield (
      api.test('non_canary') +
      api.properties(canary=False)
  )
  yield (
    api.test('canary') +
    api.properties(canary=True)
  )
