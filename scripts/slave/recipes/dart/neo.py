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
    clobber = 'clobber' in api.properties
    api.dart.checkout(channel, clobber)

  api.dart.kill_tasks()

  try_build_args = api.properties.get('try_build_args', None)
  try_commands = [key for key in api.properties.keys() if
      'try_cmd' in key and '_repeat' not in key]

  if try_build_args or try_commands:
    if try_build_args:
      build_args = try_build_args.split(' ')
      api.dart.build(build_args)
    elif 'parent_fileset' not in api.properties:
      api.dart.build()
    try_commands.sort()
    with api.step.defer_results():
      with api.context(cwd=api.path['checkout']):
        for cmd_key in try_commands:
          try_test_cmd = api.properties[cmd_key].split(' ')
          if try_test_cmd[0] == "xvfb":
            try_test_cmd = ['/usr/bin/xvfb-run','-a',
              '--server-args=-screen 0 1024x768x24'] + try_test_cmd[1:]
          try_test_repeat = api.properties.get(cmd_key + '_repeat', '1')
          for x in range(0, int(try_test_repeat)):
            api.step("%s %s" % (api.properties[cmd_key],x), try_test_cmd)
  else:
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
        buildername='builders/vm-linux-release-x64-try',
        clobber='true')
   )
   yield (
      api.test('builders/try-cl-builder') +
      api.properties.generic(
          buildername='builders/vm-linux-release-x64-try',
          try_build_args='runtime,sdk',
          try_cmd_1='tools/test.py -rchrome',
          try_cmd_2='tools/test.py -mdebug',
          try_cmd_2_repeat='2')
   )
   yield (
      api.test('builders/try-cl-builder-default-build') +
      api.properties.generic(
          buildername='builders/vm-linux-release-x64-try',
          try_cmd_1='xvfb tools/test.py -mrelease',
          try_cmd_1_repeat='1',
          try_cmd_2='tools/test.py language_2/some_test',
          try_cmd_2_repeat='3')
   )
   yield (
      api.test('builders/analyzer-triggered') +
      api.properties.generic(
        buildername='builders/analyzer-triggered',
        parent_fileset='isolate_123',
        parent_fileset_name='test_name')
   )
