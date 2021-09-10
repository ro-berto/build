# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for building V8 with bazel.
"""

from recipe_engine.post_process import Filter

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'v8',
]


def RunSteps(api):
  api.gclient.set_config('v8_with_bazel')
  api.chromium.set_config('v8')
  api.v8.checkout()
  api.v8.runhooks()
  bazel = api.path['checkout'].join('tools', 'bazel', 'bazel')
  clang = api.path['checkout'].join(
      'third_party', 'llvm-build', 'Release+Asserts', 'bin')
  with api.context(
      cwd=api.path['checkout'],
      env_prefixes={'PATH': [clang, api.v8.depot_tools_path]}):
    try:
      api.step('Bazel build', [bazel, 'build', ':d8'])
    finally:
      api.step('Bazel shutdown', [bazel, 'shutdown'])


def GenTests(api):
  yield api.test(
      'basic',
      api.post_process(Filter('Bazel build', 'Bazel shutdown')),
  )
