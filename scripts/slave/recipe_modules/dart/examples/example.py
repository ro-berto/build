# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from recipe_engine.post_process import (DoesNotRun, DropExpectation)


DEPS = [
  'dart',
  'recipe_engine/buildbucket',
  'recipe_engine/json',
  'recipe_engine/properties',
  'recipe_engine/platform',
  'recipe_engine/raw_io',
  'recipe_engine/step'
]


CANNED_OUTPUT_DIR = {
  'logs.json': '{"test":"log"}\n',
  'results.json': '{"name":"test1"}\n{"name":"test2"}\n',
  'run.json': '{"build":123}\n',
  'result.log': '{}\n'
}


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
        "dart2js-win-debug-x64-firefox",
        "dart2js-mac-debug-x64-chrome",
        "analyzer-none-linux-release",
        "vm-kernel-win-release-x64",
      ],
      "meta": {},
      "steps": [{
        "name": "Build",
        "script": "tools/build.py",
        "arguments": ["foo", "--bar"]
      }, {
        "name": "Test-step 1",
        "script": "tools/test.py",
        "arguments": ["foo", "-n${runtime}-foo-${mode}-${arch}-bar"],
        "tests": ["language_2", "co19_2"],
        "exclude_tests": ["co19"],
        "shards": 2,
        "fileset": "nameoffileset"
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar",
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
    },
    {
      "builders": [
        "example-android"
      ],
      "meta": {},
      "steps": [{
        "name": "Test on android device",
        "shards": 2,
        "fileset": "fileset1"
      }]
    }
  ]
}


def RunSteps(api):
  latest, latest_revision = api.dart.get_latest_tested_commit()
  api.dart.checkout(False, revision=latest_revision)

  build_args = ['--super-fast']
  api.dart.build(build_args, name='can_time_out')
  isolate_hash = api.dart.upload_isolate('dart_testing_fileset')

  test_args = ['--all']
  if 'shards' in api.properties:
    tasks = api.dart.shard('vm_tests', isolate_hash, test_args)
    api.dart.collect_all([{'shards':tasks,
                            'args': ['--test_arg'],
                            'environment': {},
                            'step_name': 'example sharded step'}],
                          {'commit_hash':'deadbeef',
                            'commit_time': '12124546'},
                          {})

  with api.step.defer_results():
    api.step('Print Hello World', ['echo', 'hello', 'world'])

  api.dart.kill_tasks()
  api.dart.read_debug_log()

  api.dart.test(latest=latest, test_data=TEST_MATRIX)

  if 'parent_fileset' in api.properties:
    api.dart.download_parent_isolate()


def GenTests(api):
  yield (api.test('basic') +
      api.properties(
          shards='2', shard_timeout='600',
          new_workflow_enabled=True) +
      api.buildbucket.try_build(revision = '3456abce78ef',
          build_number=1357,
          builder='dart2js-linux-release-chrome-try',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('Test-step 1_shard_1',
                    api.raw_io.output_dir(CANNED_OUTPUT_DIR)) +
      api.step_data('Test-step 2',
                    api.raw_io.output_dir(CANNED_OUTPUT_DIR)) +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('gsutil find latest build',
                    api.raw_io.output_text('123', name='latest')))

  yield (api.test('analyzer-none-linux-release-be') +
      api.properties(
          bot_id='trusty-dart-123',
          new_workflow_enabled=True) +
      api.buildbucket.ci_build(revision = '3456abce78ef',
          build_number=1357,
          builder='analyzer-none-linux-release-be',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('Test-step 1_shard_1',
                    api.raw_io.output_dir(CANNED_OUTPUT_DIR)) +
      api.step_data('Test-step 2',
                    api.raw_io.output_dir(CANNED_OUTPUT_DIR)) +
      api.step_data('upload testing fileset nameoffileset',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))

  yield (api.test('build-failure-in-matrix') +
      api.buildbucket.ci_build(revision = '3456abce78ef',
          build_number=1357,
          builder='analyzer-none-linux-release-be',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('Build', retcode=1) +
      api.post_process(DoesNotRun, 'Test-step 1') +
      api.post_process(DropExpectation))

  yield (api.test('basic-missing-name') +
      api.buildbucket.ci_build(
          builder='this-name-does-not-exist-in-test-matrix',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'))

  yield (api.test('basic-timeout') +
      api.buildbucket.ci_build(builder='times-out',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('can_time_out', times_out_after=20 * 61 + 1))

  yield (api.test('basic-failure') +
      api.buildbucket.ci_build(builder='build-fail',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('can_time_out', retcode=1))

  yield (api.test('vm-win') +
      api.platform('win', 64) +
      api.buildbucket.ci_build(revision = '3456abce78ef',
          build_number=1357,
          builder='vm-kernel-win-release-x64',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))


  yield (api.test('basic-win-stable') +
      api.platform('win', 64) +
      api.buildbucket.ci_build(revision = '3456abce78ef',
          build_number=1357,
          builder='dart2js-win-debug-x64-firefox-stable',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))

  yield (api.test('basic-win') + api.platform('win', 64) +
      api.buildbucket.ci_build(revision='a' * 40,
          build_number=1357,
          builder='dart2js-win-debug-x64-firefox',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.properties(
          parent_fileset='isolate_hash_123',
          parent_fileset_name='nameoffileset') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))

  yield (api.test('basic-mac') + api.platform('mac', 64) +
      api.buildbucket.ci_build(revision='a' * 40,
          build_number=1357,
          builder='dart2js-mac-debug-x64-chrome',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.properties(
          parent_fileset='isolate_hash_123',
          parent_fileset_name='nameoffileset') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))

  yield (api.test('example-mac') + api.platform('mac', 64) +
      api.buildbucket.ci_build(builder='example-mac',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'))

  yield (api.test('example-android') + api.platform('linux', 64) +
      api.buildbucket.ci_build(builder='example-android',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('upload testing fileset fileset1',
          stdout=api.raw_io.output('test isolate hash')))
