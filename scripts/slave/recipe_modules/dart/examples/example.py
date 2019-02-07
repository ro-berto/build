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


CANNED_FLAKY_OUTPUT_DIR = {
  'logs.json': '{"Flaky/Test/1":"log"}\n{"Flaky/Test/2":"log"}',
  'results.json': '{"name":"Flaky/Test/1"}\n{"name":"Flaky/Test/2"}\n',
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
    "test": "[]",
    "trigger": "[]"
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
        "name": "build",
        "script": "tools/build.py",
        "arguments": ["foo", "--bar"]
      }, {
        "name": "test1",
        "script": "tools/test.py",
        "arguments": ["foo", "-n${runtime}-foo-${mode}-${arch}-bar",
                      "language_2", "co19_2", "--exclude_suite=co19"],
        "shards": 2,
        "fileset": "test"
      }, {
        "name": "test2",
        "arguments": ["foo", "--bar",
                      "-n${runtime}-foo-${mode}-${arch}-bar"],
      }, {
        "name": "trigger",
        "fileset": "trigger",
        "trigger": ["foo-builder", "bar-builder"]
      }, {
        "name": "dart",
        "script": "out/ReleaseX64/dart",
        "arguments": ["--bar", "foo.dart"]
      }, {
        "name": "test3",
        "arguments": ["foo", "--bar", "-rfirefox"],
        "fileset": "test",
        "shards": 2
      }]
    },
    {
      "builders": [
        "dart2js-linux-release-chrome"
      ],
      "meta": {},
      "steps": [{
        "name": "test1",
        "script": "tools/test.py",
        "arguments": ["foo", "--bar", "-e co19, language_2"],
        "shards": 2,
        "fileset": "test"
      }, {
        "name": "custom",
        "script": "tools/custom_thing.py",
        "arguments": ["foo", "--bar", "--buildername"]
      }, {
        "name": "test2",
        "arguments": ["foo", "--bar", "co19"],
      }]
    },
    {
      "builders": [
        "example-mac"
      ],
      "meta": {},
      "steps": [{
        "name": "build",
        "script": "tools/build.py",
        "arguments": []
      }, {
        "name": "custom",
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
        "name": "android",
        "shards": 2,
        "fileset": "test"
      }]
    }
  ]
}


def RunSteps(api):
  latest, latest_revision = api.dart.get_latest_tested_commit()
  api.dart.checkout(False, revision=latest_revision)

  build_args = ['--super-fast']
  api.dart.build(build_args, name='can_time_out')

  api.dart.kill_tasks()
  api.dart.read_debug_log()

  api.dart.test(latest=latest, test_data=TEST_MATRIX)

  if 'parent_fileset' in api.properties:
    api.dart.download_parent_isolate()

def _canned_step(api, name, shards=0, local_shard=True, suffix=''):
  data = api.step_data('deflaking.list tests to deflake (%s)' % name,
                stdout=api.raw_io.output('Flaky/Test/1\nFlaky/Test/2'))
  if shards == 0:
    data += api.step_data(name, api.raw_io.output_dir(CANNED_OUTPUT_DIR))
    data += api.step_data('deflaking.%s' % name,
                          api.raw_io.output_dir(CANNED_FLAKY_OUTPUT_DIR))
  else:
    for i in range(1, shards):
      data += api.step_data('%s_shard_%s%s' % (name, i, suffix),
                            api.raw_io.output_dir(CANNED_OUTPUT_DIR))
    # TODO(athom): Remove this hack when sharded deflaking works
    local_shard = True
    deflaking_name = ('deflaking.%s' % name if local_shard
                      else 'deflaking.%s_shard_1%s' % (name, suffix))
    data += api.step_data(deflaking_name,
                          api.raw_io.output_dir(CANNED_FLAKY_OUTPUT_DIR))

  return data

def GenTests(api):
  yield (api.test('basic') +
      api.properties(
          shard_timeout='600',
          new_workflow_enabled=True) +
      api.buildbucket.try_build(revision = '3456abce78ef',
          build_number=1357,
          builder='dart2js-linux-release-chrome-try',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      _canned_step(api, 'test1', 2, False) +
      _canned_step(api, 'test2') +
      api.step_data('upload testing fileset test',
          stdout=api.raw_io.output('test_hash')) +
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
      _canned_step(api, 'test1', 2, False) +
      _canned_step(api, 'test2') +
      _canned_step(api, 'test3', 2) +
      api.step_data('upload testing fileset test',
                    stdout=api.raw_io.output('test_hash')) +
      api.step_data('upload testing fileset trigger',
                    stdout=api.raw_io.output('trigger_hash')) +
      api.step_data('buildbucket.put',
                    stdout=api.json.output(TRIGGER_RESULT)))

  yield (api.test('build-failure-in-matrix') +
      api.buildbucket.ci_build(revision = '3456abce78ef',
          build_number=1357,
          builder='analyzer-none-linux-release-be',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.step_data('build', retcode=1) +
      api.post_process(DoesNotRun, 'test1') +
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
      api.step_data('upload testing fileset test',
                    stdout=api.raw_io.output('test_hash')) +
      api.step_data('upload testing fileset trigger',
                    stdout=api.raw_io.output('trigger_hash')) +
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
          parent_fileset_name='test') +
      api.step_data('upload testing fileset trigger',
                    stdout=api.raw_io.output('trigger_hash')) +
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
      _canned_step(api, 'android', 2, False, ' on Android') +
      api.step_data('upload testing fileset test',
                    stdout=api.raw_io.output('test_hash')))
