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
    'recipe_engine/raw_io',
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
  # Override analyzer cache location to make analyzer runs hermetic.
  env = {'ANALYZER_STATE_LOCATION_OVERRIDE':
      api.path['cleanup'].join('analysis-cache')}
  with api.osx_sdk('mac'), api.context(env=env):
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

  with api.step.defer_results():
    api.dart.test(test_data=TEST_MATRIX)
    api.dart.kill_tasks()


def GenTests(api):
  yield api.test(
      'builders/vm-linux-release-x64',
      api.buildbucket.ci_build(
          builder='builders/vm-linux-release-x64',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'),
  )
  yield api.test(
      'builders/dart2js-win-debug-x64-firefox-try',
      api.buildbucket.try_build(
          builder='dart2js-win-debug-x64-firefox-try',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'),
      api.properties.generic(new_workflow_enabled='true'),
      api.step_data('add fields to result records',
                    api.raw_io.output_text('{"data":"result data"}\n')),
  )
  yield api.test(
      'builders/analyzer-triggered',
      api.buildbucket.ci_build(
          builder='builders/analyzer-triggered',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'),
      api.properties.generic(
          parent_fileset='isolate_123', parent_fileset_name='test_name'),
  )
