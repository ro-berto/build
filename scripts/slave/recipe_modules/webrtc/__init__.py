# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'adb',
  'archive',
  'build',
  'chromium',
  'chromium_android',
  'chromium_checkout',
  'chromium_swarming',
  'chromium_tests',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/gitiles',
  'depot_tools/gsutil',
  'depot_tools/osx_sdk',
  'depot_tools/tryserver',
  'goma',
  'ios',
  'isolate',
  'recipe_engine/buildbucket',
  'recipe_engine/commit_position',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/scheduler',
  'recipe_engine/step',
  'test_results',
  'test_utils',
  'trigger',
  'zip',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
