# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import (steps, try_spec as
                                                 try_spec_module)

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

# For trybot test data. If not given, buildbucket module will make the gerrit
# project the same as the buildbucket project, but since
# 'chromium' != 'chromium/src', and we check the patch's project against a
# whitelist, let's pass this to the buildbucket test api to populate the values
# as in production.
_DEFAULT_GIT_REPO = 'https://chromium.googlesource.com/chromium/src'


def RunSteps(api):
  builder_id = chromium.BuilderId.create_for_master(
      api.properties['mastername'], api.properties['buildername'])
  try_spec = api.chromium_tests.trybots.get(builder_id)
  if try_spec is None:
    try_spec = try_spec_module.TrySpec.create(bot_ids=[builder_id])

  bot_config = api.chromium_tests.create_bot_config_object(try_spec.mirrors)
  api.chromium_tests.configure_build(bot_config)
  # Fake path.
  api.code_coverage._merge_scripts_location = api.path['start_dir']

  if 'tryserver' in builder_id.master:
    api.code_coverage.instrument(api.properties['files_to_instrument'])
  if api.properties.get('mock_merged_profdata', True):
    api.path.mock_add_paths(
        api.code_coverage.profdata_dir().join('unit-merged.profdata'))
    api.path.mock_add_paths(
        api.code_coverage.profdata_dir().join('overall-merged.profdata'))
  if api.properties.get('mock_java_metadata_path', True):
    api.path.mock_add_paths(
        api.chromium.output_dir.join('coverage').join('all.json.gz'))

  tests = [
      steps.LocalIsolatedScriptTest('checkdeps'),
      # Binary name equals target name.
      steps.SwarmingGTestTest('base_unittests'),
      # Binary name is different from target name.
      steps.SwarmingGTestTest('xr_browser_tests'),
      # There is no binary, such as Python tests.
      steps.SwarmingGTestTest('telemetry_gpu_unittests'),
      steps.SwarmingIsolatedScriptTest(
          'blink_web_tests',
          merge={
              'script':
                  api.path['start_dir'].join('coverage', 'tests',
                                             'merge_blink_web_tests.py'),
              'args': ['random', 'args'],
          }),
      steps.SwarmingIsolatedScriptTest('ios_chrome_smoke_eg2tests_module'),
      steps.SwarmingIsolatedScriptTest('ios_web_view_inttests')
  ]
  assert _NUM_TESTS == len(tests)

  for test in tests:
    step = test.name
    api.code_coverage.profdata_dir(step)
    # Protected access ok here, as this is normally done by the test object
    # itself.
    api.code_coverage.shard_merge(
        step, test.target_name, additional_merge=getattr(test, '_merge', None))

  api.code_coverage.process_coverage_data(tests)

  # Exercise these properties to provide coverage only.
  _ = api.code_coverage.using_coverage
  _ = api.code_coverage.raw_profile_merge_script


def GenTests(api):
  yield api.test(
      'basic',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-chromeos-code-coverage',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.post_process(post_process.MustRunRE, 'ensure profdata dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          ('process clang code coverage data for overall test coverage.merge '
           'profile data for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload merged.profdata'),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.generate '
          'line number mapping from bot to Gerrit'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Run '
          'component extraction script to generate mapping'),
      api.post_process(post_process.MustRun, (
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload coverage metadata'),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.generate '
          'html report for overall test coverage in %s tests' % _NUM_TESTS),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload html report'),
      api.post_process(
          post_process.StepCommandContains,
          'process clang code coverage data for overall test coverage.Finding '
          'merging errors', ['--root-dir']),
      api.post_process(post_process.StepCommandContains, (
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS),
                       ['None/out/Release/content_shell']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'with_exclusions_module_property',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-chromeos-code-coverage',
          buildnumber=54,
      ),
      api.code_coverage(
          use_clang_coverage=True,
          coverage_exclude_sources='ios_test_files_and_test_utils'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_exclusions',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-chromeos-code-coverage',
          buildnumber=54,
          coverage_exclude_sources='all_test_files',
      ),
      api.code_coverage(use_clang_coverage=True),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tryserver',
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.buildbucket.try_build(
          project='chromium', builder='linux-rel', git_repo=_DEFAULT_GIT_REPO),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(post_process.MustRunRE, 'ensure profdata dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          ('process clang code coverage data for overall test coverage.merge '
           'profile data for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload merged.profdata'),
      api.post_process(post_process.MustRun, (
          'process clang code coverage data for overall test coverage.generate '
          'html report for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload html report'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.generate '
          'line number mapping from bot to Gerrit'),
      # Tests that local isolated scripts are skipped for collecting code
      # coverage data.
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.filter '
          'binaries with valid data for %s binaries' % (_NUM_TESTS - 2)),
      api.post_process(post_process.MustRun, (
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload coverage metadata'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tryserver skip instrumenting if there are too many files',
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file%d.cc' % i for i in range(500)
      ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test('tryserver unsupported repo',
       api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          buildnumber=54),
       api.code_coverage(use_clang_coverage=True),
       api.properties(
          files_to_instrument=[
            'some/path/to/file.cc',
            'some/other/path/to/file.cc',
          ]),
       api.buildbucket.try_build(
           project='chromium', builder='linux-rel',
           git_repo='https://chromium.googlesource.com/v8/v8'),
       api.post_process(
          post_process.MustRun,
          'skip processing coverage data, project(s) '
          'chromium-review.googlesource.com/v8/v8 is(are) unsupported',
       ),
       api.post_process(post_process.StatusSuccess),
       api.post_process(post_process.DropExpectation),)

  yield api.test(
      'merge errors',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.override_step_data(
          'process clang code coverage data for overall test coverage.Finding '
          'merging errors',
          stdout=api.json.output(['some_step'])),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Finding '
          'merging errors'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test('skip collecting coverage data',
       api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          buildnumber=54),
       api.code_coverage(use_clang_coverage=True),
       api.properties(
          files_to_instrument=[
            'some/path/to/non_source_file.txt'
          ]),
       api.buildbucket.try_build(
          project='chromium', builder='linux-rel', git_repo=_DEFAULT_GIT_REPO),
       api.post_process(
          post_process.MustRun,
          'skip processing coverage data because no source file changed'),
       api.post_process(post_process.DropExpectation),)

  yield api.test(
      'skip processing coverage data if not data is found',
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.buildbucket.try_build(
          project='chromium', builder='linux-rel', git_repo=_DEFAULT_GIT_REPO),
      api.override_step_data(
          'process clang code coverage data for overall test coverage.filter '
          'binaries with valid data for %s binaries' % (_NUM_TESTS - 2),
          step_test_data=lambda: self.m.json.test_api.output([])),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.skip '
          'processing because no data is found'),
      api.post_process(
          post_process.DoesNotRunRE,
          'process clang code coverage data for overall test coverage.generate '
          'metadata .*'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'raise failure for full-codebase coverage',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.step_data((
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS),
                    retcode=1),
      api.post_check(
          lambda check, steps: check(steps['process clang code coverage data '
              'for overall test coverage.gsutil '
              'upload coverage metadata'
              ''].output_properties['process_coverage_data_failure'] == True)
      ),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'do not raise failure for per-cl coverage',
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.buildbucket.try_build(
          project='chromium', builder='linux-rel', git_repo=_DEFAULT_GIT_REPO),
      api.step_data((
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS),
                    retcode=1),
      api.post_check(
          lambda check, steps: check(steps['process clang code coverage data '
              'for overall test coverage.gsutil '
              'upload coverage metadata'
              ''].output_properties['process_coverage_data_failure'] == True)
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'merged profdata does not exist',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.properties(mock_merged_profdata=False),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.skip '
          'processing because no profdata was generated'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test('process java coverage for full-codebase',
       api.properties.generic(
          mastername='chromium.fyi',
          buildername='android-code-coverage',
          buildnumber=54),
       api.code_coverage(use_java_coverage=True),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'Run component extraction script to generate mapping'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'Generate Java coverage metadata'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'gsutil Upload JSON metadata'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'Generate JaCoCo HTML report'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'Zip generated JaCoCo HTML report files'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'gsutil Upload zipped JaCoCo HTML report'),
       api.post_process(
          post_process.MustRun,
          'Clean up Java coverage files'),
       api.post_process(post_process.StatusSuccess),
       api.post_process(post_process.DropExpectation),)

  yield api.test('skip collecting coverage data for java',
       api.properties.generic(
          mastername='tryserver.chromium.android',
          buildername='android-marshmallow-arm64-rel',
          buildnumber=54),
       api.code_coverage(use_java_coverage=True),
       api.properties(
          files_to_instrument=[
            'some/path/to/non_source_file.txt'
          ]),
       api.post_process(
          post_process.MustRun, 'save paths of affected files'),
       api.post_process(
          post_process.MustRun,
          'skip processing coverage data because no source file changed'),
       api.post_process(
          post_process.MustRun,
          'Clean up Java coverage files'),
       api.post_process(post_process.DropExpectation),)

  yield api.test('process java coverage for per-cl',
       api.properties.generic(
          mastername='tryserver.chromium.android',
          buildername='android-marshmallow-arm64-rel',
          buildnumber=54),
       api.code_coverage(use_java_coverage=True),
       api.buildbucket.try_build(
          project='chromium', builder='android-marshmallow-arm64-rel',
          git_repo=_DEFAULT_GIT_REPO),
       api.properties(
          files_to_instrument=[
            'some/path/to/file.java',
            'some/other/path/to/file.java',
          ]),
       api.post_process(
          post_process.MustRun, 'save paths of affected files'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'generate line number mapping from bot to Gerrit'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'Generate Java coverage metadata'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'gsutil Upload JSON metadata'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'Generate JaCoCo HTML report'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'Zip generated JaCoCo HTML report files'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'gsutil Upload zipped JaCoCo HTML report'),
       api.post_process(
          post_process.MustRun,
          'Clean up Java coverage files'),
       api.post_process(post_process.StatusSuccess),
       api.post_process(post_process.DropExpectation),)

  yield api.test('java metadata does not exist',
       api.properties.generic(
          mastername='tryserver.chromium.android',
          buildername='android-marshmallow-arm64-rel',
          buildnumber=54),
       api.code_coverage(use_java_coverage=True),
       api.buildbucket.try_build(
          project='chromium', builder='android-marshmallow-arm64-rel',
          git_repo=_DEFAULT_GIT_REPO),
       api.properties(
          files_to_instrument=[
            'some/path/to/FileTest.java',
            'some/other/path/to/FileTest.java',
          ]),
       api.properties(
          mock_java_metadata_path = False),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'generate line number mapping from bot to Gerrit'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'Generate Java coverage metadata'),
       api.post_process(
          post_process.MustRun, 'process java coverage.'
          'skip processing because no metadata was generated'),
       api.post_process(post_process.StatusSuccess),
       api.post_process(post_process.DropExpectation),)

  yield api.test('raise failure for java full-codebase coverage',
       api.properties.generic(
          mastername='chromium.fyi',
          buildername='android-code-coverage',
          buildnumber=54),
       api.code_coverage(use_java_coverage=True),
       api.step_data(
          'process java coverage.Generate Java coverage metadata',
          retcode=1),
       api.post_check(lambda check, steps: check(steps[
              'process java coverage.Generate Java coverage metadata'
          ].output_properties['process_coverage_data_failure'] == True)),
       api.post_process(post_process.StatusFailure),
       api.post_process(post_process.DropExpectation),)

  yield api.test('do not raise failure for java per-cl coverage',
       api.properties.generic(
          mastername='tryserver.chromium.android',
          buildername='android-marshmallow-arm64-rel',
          buildnumber=54),
       api.code_coverage(use_java_coverage=True),
       api.properties(
          files_to_instrument=[
            'some/path/to/file.java',
            'some/other/path/to/file.java',
          ]),
       api.buildbucket.try_build(
          project='chromium', builder='android-marshmallow-arm64-rel',
          git_repo=_DEFAULT_GIT_REPO),
       api.step_data(
          'process java coverage.Generate Java coverage metadata',
          retcode=1),
       api.post_check(lambda check, steps: check(steps[
              'process java coverage.Generate Java coverage metadata'
          ].output_properties['process_coverage_data_failure'] == True)),
       api.post_process(post_process.StatusSuccess),
       api.post_process(post_process.DropExpectation),)

  yield api.test(
      'android native code coverage CI',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='android-code-coverage-native',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.step_data(
          'process clang code coverage data for overall test coverage.'
          'Get all Android unstripped artifacts paths',
          api.json.output([
              '/chromium/output_dir/'
              'lib.unstrippedlibbase_unittests__library.so'
          ])),
      api.post_process(post_process.MustRunRE, 'ensure profdata dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          ('process clang code coverage data for overall test coverage.merge '
           'profile data for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload merged.profdata'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Finding '
          'merging errors'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.'
          'Get all Android unstripped artifacts paths'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Run '
          'component extraction script to generate mapping'),
      api.post_process(post_process.MustRun, (
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload coverage metadata'),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.generate '
          'html report for overall test coverage in %s tests' % _NUM_TESTS),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload html report'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'iOS code coverage CI',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='ios-simulator-code-coverage',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.post_process(post_process.MustRunRE, 'ensure profdata dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          ('process clang code coverage data for overall test coverage.merge '
           'profile data for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload merged.profdata'),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.generate '
          'line number mapping from bot to Gerrit'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Run '
          'component extraction script to generate mapping'),
      api.post_process(post_process.MustRun, (
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload coverage metadata'),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.generate '
          'html report for overall test coverage in %s tests' % _NUM_TESTS),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload html report'),
      api.post_process(
          post_process.StepCommandContains,
          'process clang code coverage data for overall test coverage.Finding '
          'merging errors', ['--root-dir']),
      api.post_process(post_process.StepCommandContains, (
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS),
                       ['None/out/Debug/content_shell.app/content_shell']),
      api.post_process(post_process.StepCommandContains, (
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS), [
              'None/out/Debug/ios_chrome_eg2tests.app/ios_chrome_eg2tests'
          ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'iOS code coverage tryserver',
      api.properties.generic(
          mastername='tryserver.chromium.mac',
          buildername='ios-simulator-code-coverage',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.properties(xcode_build_version='11c29'),
      api.properties(coverage_test_types=['unit']),
      api.buildbucket.try_build(
          project='chromium',
          builder='ios-simulator-code-coverage',
          git_repo=_DEFAULT_GIT_REPO),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(post_process.MustRunRE, 'ensure profdata dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          ('process clang code coverage data for unit test coverage.merge '
           'profile data for unit test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.DoesNotRun,
          ('process clang code coverage data for overall test coverage.merge '
           'profile data for overall test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for unit test coverage.gsutil '
          'upload merged.profdata'),
      api.post_process(
          post_process.MustRun,
          ('process clang code coverage data for unit test coverage.generate '
           'html report for unit test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for unit test coverage.gsutil '
          'upload html report'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for unit test coverage.generate '
          'line number mapping from bot to Gerrit'),
      # Tests that local isolated scripts are skipped for collecting code
      # coverage data. For iOS try build, only 1 unit test target binary is
      # valid.
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for unit test coverage.filter '
          'binaries with valid data for 1 binaries'),
      api.post_process(
          post_process.MustRun,
          ('process clang code coverage data for unit test coverage.generate '
           'metadata for unit test coverage in %s tests' % _NUM_TESTS)),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for unit test coverage.gsutil '
          'upload coverage metadata'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'raise failure for unsupported test type',
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.properties(coverage_test_types=['unsupportedtest', 'overall']),
      api.post_process(
          post_process.MustRun,
          'Exception when validating test types to process: Unsupported test '
          'type unsupportedtest.'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip processing when more than one test type in per-cl coverage',
      api.properties.generic(
          mastername='tryserver.chromium.mac',
          buildername='ios-simulator-code-coverage',
          buildnumber=54),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.properties(coverage_test_types=['unit', 'overall']),
      api.buildbucket.try_build(
          project='chromium',
          builder='ios-simulator-code-coverage',
          git_repo=_DEFAULT_GIT_REPO),
      api.post_process(
          post_process.MustRun,
          'skip processing because of an exception when validating test types '
          'to process: Only one test type is supported for per-cl coverage but '
          '2 found in builder properties.'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
