# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for running presubmit in V8 CI.
"""

from recipe_engine.post_process import Filter

DEPS = [
  'chromium',
  'depot_tools/gclient',
  'depot_tools/infra_paths',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/runtime',
  'v8',
]

def RunSteps(api):
  api.gclient.set_config('v8')
  api.chromium.set_config('v8')
  api.v8.checkout()
  api.v8.runhooks()
  with api.context(
      cwd=api.path['checkout'],
      env_prefixes={'PATH': [api.v8.depot_tools_path]}):
    api.python(
      'Presubmit',
      api.path['checkout'].join('tools', 'v8_presubmit.py'),
    )


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(path_config='kitchen') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.post_process(Filter('Presubmit'))
  )
