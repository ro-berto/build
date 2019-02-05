# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium_tests',
    'clang_coverage',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  bot_config_object = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)],
      builders=None)
  api.chromium_tests.configure_build(bot_config_object)
  if 'tryserver' in mastername:
    api.clang_coverage.instrument(api.properties['files_to_instrument'])

  for i in range(3):
    step = 'step %d' % i
    api.clang_coverage.profdata_dir(step)
    api.clang_coverage.shard_merge(step)
    api.clang_coverage.get_local_isolated_coverage(
        step, api.step(
            'dummy test', [], stdout=api.raw_io.output(),
            step_test_data=lambda: api.raw_io.test_api.stream_output(
                '[run_isolated_out_hack]%s[/run_isolated_out_hack]))' %
                '{"hash":"abc", "storage":"url"}')))
  api.clang_coverage.process_coverage_data([
      api.chromium_tests.steps.SwarmingGTestTest('base_unittests'),
      api.chromium_tests.steps.LocalIsolatedScriptTest('abc_fuzzer'),
      api.chromium_tests.steps.SwarmingIsolatedScriptTest('blink_web_tests')
    ])

  # Exercise these properties to provide coverage only.
  _ = api.clang_coverage.using_coverage
  _ = api.clang_coverage.raw_profile_merge_script


def GenTests(api):
  yield (
      api.test('basic')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54)
      + api.post_process(
          post_process.MustRunRE, 'ensure profdata dir for .*', 3, 3)
      + api.post_process(
          post_process.MustRun, 'merge profile data for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload merged.profdata')
      + api.post_process(
          post_process.DoesNotRun,
          'generate line number mapping from bot to Gerrit')
      + api.post_process(
          post_process.MustRun,
          'Run component extraction script to generate mapping')
      + api.post_process(
          post_process.MustRun, 'generate metadata for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload metadata')
      + api.post_process(
          post_process.DoesNotRun, 'generate html report for 3 targets')
      + api.post_process(
          post_process.DoesNotRun, 'gsutil upload html report')
      + api.post_process(
          post_process.StepCommandContains, 'Finding merging errors',
          ['--root-dir'])
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('tryserver')
      + api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-coverage-rel',
          buildnumber=54)
      + api.properties(
          files_to_instrument=[
            'some/path/to/file.cc',
            'some/other/path/to/file.cc',
          ])
      + api.buildbucket.try_build(
          project='chromium', builder='linux-coverage-rel')
      + api.post_process(
          post_process.MustRun, 'save paths of affected files')
      + api.post_process(
          post_process.MustRunRE, 'ensure profdata dir for .*', 3, 3)
      + api.post_process(
          post_process.MustRun, 'merge profile data for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload merged.profdata')
      + api.post_process(
          post_process.MustRun, 'generate html report for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload html report')
      + api.post_process(
          post_process.MustRun,
          'generate line number mapping from bot to Gerrit')
      + api.post_process(
          post_process.MustRun, 'generate metadata for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload metadata')
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('merge errors')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54)
      + api.override_step_data(
          'Finding merging errors', stdout=api.json.output(['some_step']))
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('bad_local_run')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54)
      + api.post_process(
          post_process.MustRunRE, 'ensure profdata dir for .*', 3, 3)
      + api.post_process(
          post_process.MustRun, 'merge profile data for 3 targets')
      + api.post_process(
          post_process.DoesNotRun,
          'generate line number mapping from bot to Gerrit')
      + api.post_process(
          post_process.MustRun,
          'Run component extraction script to generate mapping')
      + api.post_process(
          post_process.MustRun, 'generate metadata for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload metadata')
      + api.override_step_data('dummy test', stdout=api.raw_io.output(
          'no isolate'))
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('skip collecting coverage data')
      + api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-coverage-rel',
          buildnumber=54)
      + api.properties(
          files_to_instrument=[
            'some/path/to/non_source_file.txt'
          ])
      + api.buildbucket.try_build(
          project='chromium/src', builder='linux-coverage-rel')
      + api.post_process(
          post_process.MustRun,
          'skip collecting coverage data because no source file is changed')
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('raise failure')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54)
      + api.post_process(
          post_process.MustRunRE, 'ensure profdata dir for .*', 3, 3)
      + api.post_process(
          post_process.MustRun, 'merge profile data for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload merged.profdata')
      + api.post_process(
          post_process.DoesNotRun,
          'generate line number mapping from bot to Gerrit')
      + api.post_process(
          post_process.MustRun,
          'Run component extraction script to generate mapping')
      + api.post_process(
          post_process.MustRun, 'generate metadata for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload metadata')
      + api.post_process(
          post_process.DoesNotRun, 'generate html report for 3 targets')
      + api.post_process(
          post_process.DoesNotRun, 'gsutil upload html report')
      + api.post_process(
          post_process.StepCommandContains, 'Finding merging errors',
          ['--root-dir'])
      + api.step_data('generate metadata for 3 targets', retcode=1)
      + api.post_process(
          post_process.AnnotationContains,
          'gsutil upload metadata',
          ['SET_BUILD_PROPERTY@process_coverage_data_failure@true'])
      + api.post_process(post_process.StatusFailure)
      + api.post_process(post_process.DropExpectation)
  )
