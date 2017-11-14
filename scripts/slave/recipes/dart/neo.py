# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'dart',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'test_utils',
]

TEST_MATRIX = {
  "configurations": [
    {
      "builders": [
        "dart2js-win10-debug-x64-ff-try",
        "analyzer-linux-release-be"
      ],
      "meta": {},
      "steps": [{
        "name": "Build",
        "script": "tools/build.py",
        "arguments": ["foo", "--bar"],
        "shards": 1
      }, {
        "name": "Test-step 1",
        "script": "tools/test.py",
        "arguments": ["foo", "--bar"],
        "tests": ["-e co19", "language_2"]
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar"],
        "tests": []
      }]
    },
    {
      "builders": [
        "dart2js-linux-release-chrome-try"
      ],
      "meta": {},
      "steps": [{
        "name": "Test-step 1",
        "script": "tools/test.py",
        "arguments": ["foo", "--bar"],
        "tests": ["-e co19", "language_2"],
        "excludeTests": []
      }, {
        "name": "Test-step custom",
        "script": "tools/custom_thing.py",
        "arguments": ["foo", "--bar"]
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar"],
        "tests": ["co19"]
      }]
    }
  ]
}

def RunSteps(api):
  # If parent_fileset is set, the bot is triggered by
  # another builder, and we should not download the sdk.
  # We rely on all files being in the isolate
  if 'parent_fileset' in api.properties:
    api.dart.download_parent_isolate()
  else:
    builder_name = api.properties.get('buildername')
    builder_fragments = builder_name.split('-')
    channel = builder_fragments[-1]
    if channel not in ['be', 'dev', 'stable', 'integration', 'try']:
      channel = 'be'
    api.dart.checkout(channel)

  api.dart.kill_tasks()

  with api.step.defer_results():
    api.dart.test(test_data=TEST_MATRIX)
    api.dart.kill_tasks()
    with api.context(cwd=api.path['checkout']):
      api.dart.read_debug_log()

def GenTests(api):
   yield (
      api.test('builders/vm-linux-release-x64') +
      api.properties.generic(
        buildername='builders/vm-linux-release-x64')
   )
   yield (
      api.test('builders/vm-linux-release-x64-try') +
      api.properties.generic(
        buildername='builders/vm-linux-release-x64-try')
   )
   yield (
      api.test('builders/analyzer-triggered') +
      api.properties.generic(
        buildername='builders/analyzer-triggered',
        parent_fileset='isolate_123',
        parent_fileset_name='test_name')
   )
