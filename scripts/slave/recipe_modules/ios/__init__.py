# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'build/chromium',
  'build/chromium_checkout',
  'build/file',
  'build/filter',
  'build/goma',
  'depot_tools/gsutil',
  'build/isolate',
  'build/swarming',
  'build/swarming_client',
  'build/test_results',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
