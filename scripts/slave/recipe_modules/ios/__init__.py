# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'build/chromium',
  'build/chromium_checkout',
  'build/filter',
  'build/goma',
  'build/isolate',
  'build/perf_dashboard',
  'build/swarming',
  'build/swarming_client',
  'build/test_results',
  'depot_tools/bot_update',
  'depot_tools/cipd',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'recipe_engine/time',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
