# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'dart',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/osx_sdk',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'test_utils',
  'swarming_client',
]


TEST_MATRIX = {
  "filesets": {
    "fileset1": "[]",
    "nameoffileset": "[]"
  },
  "global": {
    "chrome": "66.0.3359.139",
    "firefox": "60.0.1"
  },
  "builder_configurations": [
    {
      "builders": [
        "dart2js-win-debug-x64-firefox",
        "analyzer-linux-release-none"
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
        "arguments": ["foo", "--bar", "-e co19", "language_2"],
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar", "-mdebug",
                      "-n${runtime}-foo-${mode}-${arch}-bar"],
      }]
    },
    {
      "builders": [
        "dart2js-linux-release-chrome"
      ],
      "meta": {},
      "steps": [{
        "name": "Test-step 1",
        "script": "tools/test.py",
        "arguments": ["foo", "--bar", "-e co19", "language_2"],
      }, {
        "name": "Test-step custom",
        "script": "tools/custom_thing.py",
        "arguments": ["foo", "--bar"]
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar", "co19"],
      }]
    }
  ]
}


def RunSteps(api):
  with api.osx_sdk('mac'):
    _run_steps_impl(api)


def _run_steps_impl(api):
  # If parent_fileset is set, the bot is triggered by
  # another builder, and we should not download the sdk.
  # We rely on all files being in the isolate
  if 'parent_fileset' in api.properties:
    # todo(athom): this doesn't work on windows, see bug 785362.
    api.swarming_client.checkout('master')
    api.dart.download_parent_isolate()
  else:
    builder_name = api.buildbucket.builder_name
    builder_fragments = builder_name.split('-')
    channel = builder_fragments[-1]
    if channel not in ['be', 'dev', 'stable', 'try']:
      channel = 'be'
    clobber = 'clobber' in api.properties
    api.dart.checkout(clobber)

  api.dart.kill_tasks()

  try_build_args = api.properties.get('try_build_args', None)
  try_commands = [key for key in api.properties.keys() if
      'try_cmd' in key and '_repeat' not in key]

  if try_build_args or try_commands:
    if try_build_args:
      build_args = try_build_args.split()
      api.dart.build(build_args)
    elif 'parent_fileset' not in api.properties:
      api.dart.build()
    try_commands.sort()
    with api.step.defer_results(), api.context(cwd=api.path['checkout']):
      for cmd_key in try_commands:
        try_test_cmd = api.properties[cmd_key].split()
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
      api.buildbucket.ci_build(
          builder='builders/vm-linux-release-x64',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart')
   )
   yield (
      api.test('builders/dart2js-win-debug-x64-firefox-try') +
      api.buildbucket.try_build(
          revision='3456abcd78ef',
          builder='dart2js-win-debug-x64-firefox-try',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.properties.generic(new_workflow_enabled='true')
   )
   yield (
      api.test('builders/try-cl-builder') +
      api.buildbucket.try_build(
          builder='builders/vm-linux-release-x64-try',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.properties.generic(
          try_build_args='  runtime,sdk',
          try_cmd_1='tools/test.py -rchrome',
          try_cmd_2='tools/test.py -mdebug',
          try_cmd_2_repeat='2')
   )
   yield (
      api.test('builders/try-cl-builder-default-build') +
      api.buildbucket.try_build(
          builder='builders/vm-linux-release-x64-try',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.properties.generic(
          try_cmd_1='xvfb tools/test.py  -mrelease',
          try_cmd_1_repeat='1',
          try_cmd_2='tools/test.py language_2/some_test',
          try_cmd_2_repeat='3')
   )
   yield (
      api.test('builders/analyzer-triggered') +
      api.buildbucket.ci_build(
          builder='builders/analyzer-triggered',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.properties.generic(
        parent_fileset='isolate_123',
        parent_fileset_name='test_name')
   )
