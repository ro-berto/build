# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Recipe for running CBB tests in Crossbench
"""

DEPS = [
    'depot_tools/git',
    'recipe_engine/buildbucket',
    'depot_tools/gclient',
    'recipe_engine/step',
    'v8',
]


def RunSteps(api):
  gclient_config = api.gclient.make_config()
  solution = gclient_config.solutions.add()
  solution.url = 'https://chromium.googlesource.com/crossbench/'
  solution.name = 'crossbench'
  gclient_config.got_revision_mapping[solution.name] = 'got_revision'
  api.gclient.c = gclient_config

  api.v8.checkout()

  api.step('Run CBB Tests', ['vpython3', 'tests/cbb/cbb_runner.py'])


def GenTests(api):
  yield api.test('basic')
