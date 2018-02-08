# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'goma',
  'recipe_engine/properties',
]


def RunSteps(api):
  canary = api.m.properties.get('canary', False)
  warn_if_canary = api.m.properties.get('warn_if_canary', False)
  api.goma.ensure_goma(canary=canary, warn_if_canary=warn_if_canary)


def GenTests(api):
  # non canary
  yield (
      api.test('non_canary') +
      api.properties(canary=False, warn_if_canary=False)
  )
  # non canary / warn if canary
  yield (
    api.test('non_canary_warn_if_canary') +
    api.properties(canary=False, warn_if_canary=True)
  )
  # canary
  yield (
    api.test('canary') +
    api.properties(canary=True, warn_if_canary=False)
  )
  # canary / warn if canary
  yield (
    api.test('canary_warn_if_canary') +
    api.properties(canary=True, warn_if_canary=True)
  )
