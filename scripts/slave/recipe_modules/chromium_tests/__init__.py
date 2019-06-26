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
  'code_coverage',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'filter',
  'gn',
  'goma',
  'isolate',
  'perf_dashboard',
  'puppet_service_account',
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
  'recipe_engine/step',
  'recipe_engine/scheduler',
  'recipe_engine/tempfile',
  'recipe_engine/time',
  'test_results',
  'test_utils',
  'traceback',
  'trigger',
  'zip',
]
