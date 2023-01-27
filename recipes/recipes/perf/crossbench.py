# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Recipe for running CBB tests in Crossbench
"""

DEPS = [
    'depot_tools/git',
    'recipe_engine/buildbucket',
    'recipe_engine/step',
]


def RunSteps(api):
  revision = api.buildbucket.gitiles_commit.id or 'HEAD'
  api.git.checkout(
      'https://chromium.googlesource.com/crossbench/', ref=revision)

  api.step('Run CBB Tests', ['vpython3', 'tests/cbb/cbb_runner.py'])


def GenTests(api):
  yield api.test('basic')
