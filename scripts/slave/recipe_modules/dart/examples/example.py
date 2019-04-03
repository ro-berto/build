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
        "vm-kernel-win-release-x64",
      ],
      "meta": {},
      "steps": [{
        "name": "gn",
        "script": "tools/gn.py",
        "arguments": ["--bytecode"]
      }, {
        "name": "build",
        "script": "tools/build.py",
        "arguments": ["--arch=x64", "runtime"]
      }, {
        "name": "test1",
        "script": "tools/test.py",
        "arguments": ["foo", "-ndartk-${system}-${mode}-${arch}",
                      "language_2", "co19_2", "--exclude_suite=co19"],
        "shards": 2,
        "fileset": "test"
      }, {
        "name": "test2",
        "arguments": ["foo", "--bar", "-ndartk-${system}-${mode}-${arch}"],
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
        "arguments": ["-ndartk-${system}-${mode}-${arch}", "foo", "--bar"],
        "fileset": "test",
        "shards": 2
      }]
    },
    {
      "builders": [
        "analyzer-linux-release",
      ],
      "meta": {},
      "steps": [{
        "name": "build",
        "script": "tools/build.py"
      }, {
        "name": "test1",
        "script": "tools/test.py",
        "fileset": "test",
        "shards": 2,
        "arguments": ["-nunittest-asserts-${mode}-${system}"]
      }, {
        "name": "test2",
        "arguments": ["foo", "--bar", "-ndartk-${system}-${mode}-${arch}"],
      }, {
        "name": "trigger",
        "fileset": "trigger",
        "trigger": ["foo-builder", "bar-builder"]
      }, {
        "name": "test3",
        "arguments": ["-nanalyzer-asserts-${system}", "foo", "--bar"],
        "fileset": "test",
        "shards": 2
      }]
    },
    {
      "builders": [
        "dart2js-strong-mac-x64-chrome",
        "dart2js-strong-linux-x64-firefox",
        "dart2js-strong-win-x64-chrome"
      ],
      "meta": {},
      "steps": [{
        "name": "test1",
        "script": "tools/test.py",
        "arguments": ["-ndart2js-${system}-${runtime}", "foo", "--bar",
                      "-e co19, language_2"],
        "shards": 2,
        "fileset": "test"
      }, {
        "name": "custom",
        "script": "tools/custom_thing.py",
        "arguments": ["foo", "--bar", "--buildername"]
      }, {
        "name": "test2",
        "arguments": ["-ndart2js-${system}-${runtime}", "foo", "--bar", "co19"],
      }]
    },
    {
      "builders": [
        "vm-kernel-mac-release-x64"
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
        "vm-kernel-precomp-android-release-arm"
      ],
      "meta": {},
      "steps": [{
        "name": "android",
        "shards": 2,
        "fileset": "test",
        "arguments": ["-ndartkp-android-${mode}-${arch}"]
      }]
    },
    {
      "builders": [
        "fuzz-linux"
      ],
      "steps": [{
        "name": "make a fuzz",
        "script": "out/ReleaseX64/dart",
        "arguments": [
          "runtime/tools/dartfuzz/dartfuzz_test.dart",
          "--isolates",
          "8",
          "--no-show-stats",
          "--time",
          "2700"
        ],
        "shards": 2,
        "fileset": "test"
      }]
    }
  ]
}

RESULT_DATA = (
    '{"name":"co19_2/Language/Classes/Abstract_Instance_Members/inherited_t01"'
    ',"configuration":"dartk-linux-product-x64","suite":"co19_2",'
    '"test_name":"Language/Classes/Abstract_Instance_Members/inherited_t01",'
    '"time_ms":451,"result":"CompileTimeError","expected":"CompileTimeError",'
    '"matches":true,"commit_time":1551185312,'
    '"commit_hash":"f0042a32250a8a6193e6d07e2b6508b13f43c864",'
    '"build_number":"2404","builder_name":"vm-kernel-linux-product-x64",'
    '"bot_name":"trusty-dart-68765ebb-us-central1-b-2ls0","flaky":false,'
    '"previous_flaky":false,"previous_result":"CompileTimeError",'
    '"previous_commit_hash":"f0042a32250a8a6193e6d07e2b6508b13f43c864",'
    '"previous_commit_time":1551185312,"previous_build_number":2403,'
    '"changed":false}\n' +
    '{"name":"co19_2/Language/Classes/Abstract_Instance_Members/inherited_t02"'
    ',"configuration":"dartk-linux-product-x64","suite":"co19_2",'
    '"test_name":"Language/Classes/Abstract_Instance_Members/inherited_t02",'
    '"time_ms":496,"result":"CompileTimeError","expected":"CompileTimeError",'
    '"matches":true,"commit_time":1551185312,'
    '"commit_hash":"f0042a32250a8a6193e6d07e2b6508b13f43c864",'
    '"build_number":"2404","builder_name":"vm-kernel-linux-product-x64",'
    '"bot_name":"trusty-dart-68765ebb-us-central1-b-2ls0","flaky":false,'
    '"previous_flaky":false,"previous_result":"CompileTimeError",'
    '"previous_commit_hash":"f0042a32250a8a6193e6d07e2b6508b13f43c864",'
    '"previous_commit_time":1551185312,"previous_build_number":2403,'
    '"changed":false}\n')


def RunSteps(api):
  api.dart.checkout('clobber' in api.properties)

  build_args = ['--super-fast']
  api.dart.build(build_args, name='can_time_out')

  api.dart.kill_tasks()
  api.dart.read_debug_log()

  api.dart.test(test_data=TEST_MATRIX)

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
          builder='dart2js-strong-linux-x64-firefox-try',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.override_step_data(
        'download previous results.gerrit changes',
        api.json.output([{'change_id': 'Ideadbeef'}])) +
      _canned_step(api, 'test1', 2, False) +
      _canned_step(api, 'test2') +
      api.step_data('upload testing fileset test',
          stdout=api.raw_io.output('test_hash')) +
      api.step_data('download previous results.gsutil find latest build',
          api.raw_io.output_text('123', name='latest')) +
      api.step_data('add fields to result records',
          api.raw_io.output_text(RESULT_DATA)))

  yield (api.test('analyzer-linux-release') +
      api.properties(
          bot_id='trusty-dart-123',
          new_workflow_enabled=True) +
      api.buildbucket.ci_build(revision = '3456abce78ef',
          build_number=1357,
          builder='analyzer-linux-release',
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
                    stdout=api.json.output(TRIGGER_RESULT)) +
      api.step_data('add fields to result records',
          api.raw_io.output_text(RESULT_DATA)))

  yield (api.test('build-failure-in-matrix') +
      api.buildbucket.ci_build(revision = '3456abce78ef',
          build_number=1357,
          builder='analyzer-linux-release',
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
      api.step_data('can_time_out', times_out_after=60 * 61 + 1))

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
                    stdout=api.json.output(TRIGGER_RESULT)) +
      api.step_data('add fields to result records',
          api.raw_io.output_text(RESULT_DATA)))

  yield (api.test('basic-mac') + api.platform('mac', 64) +
      api.buildbucket.ci_build(revision='a' * 40,
          build_number=1357,
          builder='dart2js-strong-mac-x64-chrome',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      api.properties(
          clobber='True',
          parent_fileset='isolate_hash_123',
          parent_fileset_name='test') +
      api.step_data('add fields to result records',
          api.raw_io.output_text(RESULT_DATA)))

  yield (api.test('example-mac') + api.platform('mac', 64) +
      api.buildbucket.ci_build(builder='vm-kernel-mac-release-x64',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'))

  yield (api.test('example-android') + api.platform('linux', 64) +
      api.buildbucket.ci_build(builder='vm-kernel-precomp-android-release-arm',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart') +
      _canned_step(api, 'android', 2, False, ' on Android') +
      api.step_data('upload testing fileset test',
                    stdout=api.raw_io.output('test_hash')))

  yield (api.test('fuzz-test') +
      api.step_data('upload testing fileset test',
                    stdout=api.raw_io.output('test_hash')) +
      api.buildbucket.ci_build(builder='fuzz-linux',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'))
