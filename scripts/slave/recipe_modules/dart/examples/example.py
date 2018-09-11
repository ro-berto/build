# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (DoesNotRun, DropExpectation)

DEPS = [
  'dart',
  'recipe_engine/json',
  'recipe_engine/properties',
  'recipe_engine/platform',
  'recipe_engine/raw_io',
  'recipe_engine/step'
]

TRIGGER_RESULT = {
  "results": [
    {
      "build": {
        "id": "8963024236039183808",
        "tags": [
          "builder:analyzer-linux-release",
          "parent_buildername:dart-sdk-linux"
        ],
        "url": "https://ci.chromium.org/p/dart/builds/b8963024236039183808",
      }
    },
    {
      "build": {
        "id": "8963024236039836208",
        "tags": [
          "builder:analyzer-strong-linux-release",
          "parent_buildername:dart-sdk-linux"
        ],
        "url": "https://ci.chromium.org/p/dart/builds/b8963024236039836208",
      }
    },
    {
      "build": {
        "id": "8963024236039228096",
        "tags": [
          "builder:analyzer-analysis-server-linux",
          "parent_buildername:dart-sdk-linux"
        ],
        "url": "https://ci.chromium.org/p/dart/builds/b8963024236039228096",
      }
    }
  ]
}

TEST_MATRIX = {
  "filesets": {
    "fileset1": "[]",
    "nameoffileset": "[]"
  },
  "global": {
    "chrome": "66.0.3359.139",
    "firefox": "61"
  },
  "builder_configurations": [
    {
      "builders": [
        "dart2js-win10-debug-x64-firefox",
        "analyzer-none-linux-release"
      ],
      "meta": {},
      "steps": [{
        "name": "Build",
        "script": "tools/build.py",
        "arguments": ["foo", "--bar"]
      }, {
        "name": "Test-step 1",
        "script": "tools/test.py",
        "arguments": ["foo", "--arch=x64"],
        "tests": ["language_2"],
        "exclude_tests": ["co19"],
        "shards": 2,
        "fileset": "nameoffileset"
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar", "-rchrome",
                      "-n${runtime}-foo-${mode}-${arch}-bar"],
        "tests": []
      }, {
        "name": "Trigger step",
        "fileset": "fileset1",
        "trigger": ["foo-builder", "bar-builder"]
      }, {
        "name": "Test-step dart",
        "script": "out/ReleaseX64/dart",
        "arguments": ["--bar", "foo.dart"]
      }, {
        "name": "Test-step 3",
        "arguments": ["foo", "--bar", "-rfirefox"],
        "fileset": "fileset1",
        "shards": 2
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
        "arguments": ["foo", "--bar"],
        "tests": ["-e co19, language_2"],
        "shards": 2,
        "fileset": "fileset1"
      }, {
        "name": "Test-step custom",
        "script": "tools/custom_thing.py",
        "arguments": ["foo", "--bar", "--buildername"]
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar"],
        "tests": ["co19"]
      }]
    },
    {
      "builders": [
        "example-mac"
      ],
      "meta": {},
      "steps": [{
        "name": "Build",
        "script": "tools/build.py",
        "arguments": []
      }, {
        "name": "Test-step custom",
        "script": "out/custom_thing",
        "arguments": ["foo", "--bar", "--buildername"]
      }]
    }
  ]
}

def RunSteps(api):
  api.dart.checkout(False)

  build_args = ['--super-fast']
  api.dart.build(build_args, name='can_time_out')
  isolate_hash = api.dart.build(build_args, 'dart_tests')

  test_args = ['--all']
  if 'shards' in api.properties:
    tasks = api.dart.shard('vm_tests', isolate_hash, test_args)
    api.dart.collect(tasks)

  with api.step.defer_results():
    api.step('Print Hello World', ['echo', 'hello', 'world'])
    api.dart.read_result_file('print result', 'result.log')

  api.dart.kill_tasks()
  api.dart.read_debug_log()

  api.dart.test(test_data=TEST_MATRIX)

  if 'parent_fileset' in api.properties:
    api.dart.download_parent_isolate()

def GenTests(api):
  yield (api.test('basic') + api.properties(
      shards='2', shard_timeout='600', branch="refs/head/master",
      buildername='dart2js-linux-release-chrome-try', buildnumber='1357') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')))

  yield (api.test('analyzer-none-linux-release-be') + api.properties(
      buildername='analyzer-none-linux-release-be', buildnumber='1357') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))

  yield (api.test('build-failure-in-matrix') + api.properties(
      buildername='analyzer-none-linux-release-be', buildnumber='1357') +
      api.step_data('Build', retcode=1) +
      api.post_process(DoesNotRun, 'Test-step 1') +
      api.post_process(DropExpectation))

  yield (api.test('basic-missing-name') + api.properties(
      buildername='this-name-does-not-exist-in-test-matrix'))

  yield (api.test('basic-timeout') + api.properties(
      buildername='times-out') +
      api.step_data('can_time_out', times_out_after=20 * 61 + 1))

  yield (api.test('basic-failure') + api.properties(
      buildername='build-fail') +
      api.step_data('can_time_out', retcode=1))

  yield (api.test('basic-win-stable') +
      api.platform('win', 64) +
      api.properties(buildername='dart2js-win10-debug-x64-firefox-stable',
           buildnumber='1357') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))

  yield (api.test('basic-win') + api.platform('win', 64) + api.properties(
      buildername='dart2js-win10-debug-x64-firefox',
      buildnumber='1357',
      revision='a' * 40,
      parent_fileset='isolate_hash_123',
      parent_fileset_name='nameoffileset') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))

  yield (api.test('example-mac') + api.platform('mac', 64) + api.properties(
      buildername='example-mac'))
