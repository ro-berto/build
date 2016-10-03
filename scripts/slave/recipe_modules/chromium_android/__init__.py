# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'adb',
  'depot_tools/bot_update',
  'chromium',
  'commit_position',
  'file',
  'depot_tools/gclient',
  'recipe_engine/generator_script',
  'depot_tools/git',
  'gsutil',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'recipe_engine/time',
  'test_utils',
  'depot_tools/tryserver',
  'url',
  'archive',
  'zip',
]
