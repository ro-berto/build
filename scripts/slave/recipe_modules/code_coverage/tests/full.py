# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'code_coverage',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

# Number of tests. Needed by the tests.
_NUM_TESTS = 7


def RunSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  bot_config_object = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)],
      builders=None)
  api.chromium_tests.configure_build(bot_config_object)
  if 'tryserver' in mastername:
    api.code_coverage.instrument(api.properties['files_to_instrument'])
  # Fake path.
  api.code_coverage._merge_scripts_location = api.path['start_dir']
  api.path.mock_add_paths(api.chromium.output_dir.join('args.gn'))

  if api.properties.get('mock_merged_profdata', True):
    api.path.mock_add_paths(
        api.code_coverage.profdata_dir().join('merged.profdata'))

  tests = [
      api.chromium_tests.steps.LocalIsolatedScriptTest('checkdeps'),
      api.chromium_tests.steps.SwarmingGTestTest('chrome_all_tast_tests'),
      api.chromium_tests.steps.SwarmingGTestTest('base_unittests'),
      api.chromium_tests.steps.SwarmingGTestTest('xr_browser_tests'),
      api.chromium_tests.steps.SwarmingGTestTest('gl_unittests_ozone'),
      api.chromium_tests.steps.SwarmingIsolatedScriptTest('abc_fuzzer'),
      api.chromium_tests.steps.SwarmingIsolatedScriptTest(
          'blink_web_tests',
          merge={
              'script':
                  api.path['start_dir'].join('coverage', 'tests',
                                             'merge_blink_web_tests.py'),
              'args': ['random', 'args'],
          })
  ]
  assert _NUM_TESTS == len(tests)

  for test in tests:
    step = test.name
    api.code_coverage.profdata_dir(step)
    # Protected access ok here, as this is normally done by the test object
    # itself.
    api.code_coverage.shard_merge(
        step, additional_merge=getattr(test, '_merge', None))

  api.code_coverage.process_coverage_data(tests)

  # Exercise these properties to provide coverage only.
  _ = api.code_coverage.using_coverage
  _ = api.code_coverage.raw_profile_merge_script


# yapf: disable
def GenTests(api):
  yield (
      api.test('basic')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-chromeos-code-coverage',
          buildnumber=54)
      + api.post_process(post_process.MustRunRE, 'ensure profdata dir for .*',
                       _NUM_TESTS, _NUM_TESTS)
      + api.post_process(
          post_process.MustRun,
          ('process clang code coverage data.merge profile data for %s tests' %
           _NUM_TESTS))
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.gsutil upload merged.profdata')
      + api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data.generate line number mapping from '
          'bot to Gerrit')
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.Run component extraction script to '
          'generate mapping')
      + api.post_process(
          post_process.MustRun,
          ('process clang code coverage data.generate metadata for %s tests' %
           _NUM_TESTS))
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.gsutil upload coverage metadata')
      + api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data.generate html report for %s '
          'tests' % _NUM_TESTS)
      + api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data.gsutil upload html report')
      + api.post_process(
          post_process.StepCommandContains,
          'process clang code coverage data.Finding merging errors',
          ['--root-dir'])
      + api.post_process(
          post_process.StepCommandContains,
          ('process clang code coverage data.generate metadata for %s tests' %
           _NUM_TESTS),
          ['None/out/Release/chrome'])
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )
  yield (
      api.test('with_exclusions')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-chromeos-code-coverage',
          buildnumber=54,
          exclude_sources='all_test_files',
      )
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
          post_process.MustRunRE,
          'ensure profdata dir for .*', _NUM_TESTS, _NUM_TESTS)
      + api.post_process(
          post_process.MustRun,
          ('process clang code coverage data.merge profile data for %s tests' %
           _NUM_TESTS))
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.gsutil upload merged.profdata')
      + api.post_process(
          post_process.MustRun,
          ('process clang code coverage data.generate html report for %s tests'
           % _NUM_TESTS))
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.gsutil upload html report')
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.generate line number mapping from '
          'bot to Gerrit')
      # Tests that local isolated scripts are skipped for collecting code
      # coverage data.
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.filter binaries with valid data '
          'for %s binaries' % (_NUM_TESTS - 1))
      + api.post_process(
          post_process.MustRun,
          ('process clang code coverage data.generate metadata for %s tests' %
           _NUM_TESTS))
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.gsutil upload coverage metadata')
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
          'process clang code coverage data.Finding merging errors',
          stdout=api.json.output(['some_step']))
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.Finding merging errors')
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
          'process clang code coverage data.skip processing because no source '
          'file is changed')
      + api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('skip processing coverage data if not data is found')
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
    + api.override_step_data(
      'process clang code coverage data.filter binaries with valid data for %s '
      'binaries' % (_NUM_TESTS - 1),
      step_test_data=lambda: self.m.json.test_api.output([]))
    + api.post_process(
        post_process.MustRun,
        'process clang code coverage data.skip processing because no data is '
        'found')
    + api.post_process(
        post_process.DoesNotRunRE,
        'process clang code coverage data.generate metadata .*')
    + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('raise failure for full-codebase coverage')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54)
      + api.step_data(
          ('process clang code coverage data.generate metadata for %s tests' %
           _NUM_TESTS),
          retcode=1)
      + api.post_check(lambda check, steps: check(steps[
              'process clang code coverage data.gsutil upload coverage metadata'
          ].output_properties['process_coverage_data_failure'] == True))
      + api.post_process(post_process.StatusFailure)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('do not raise failure for per-cl coverage')
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
      + api.step_data(
          ('process clang code coverage data.generate metadata for %s tests' %
           _NUM_TESTS),
          retcode=1)
      + api.post_check(lambda check, steps: check(steps[
              'process clang code coverage data.gsutil upload coverage metadata'
          ].output_properties['process_coverage_data_failure'] == True))
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('merged profdata does not exist')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54)
      + api.properties(
          mock_merged_profdata = False)
      + api.post_process(
          post_process.MustRun,
          'process clang code coverage data.skip processing because no '
          'profdata was generated')
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('process java coverage')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='android-code-coverage',
          buildnumber=54)
      + api.step_data('check GN args for coverage', api.raw_io.output_text(
          'jacoco_coverage = true'))
      + api.post_process(
          post_process.MustRun, 'process java coverage')
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )
