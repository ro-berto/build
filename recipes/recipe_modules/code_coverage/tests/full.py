# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_swarming
from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'profiles',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

# Number of tests. Needed by the tests.
_NUM_TESTS = 7


def RunSteps(api):
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder(use_try_db=True))
  api.chromium_tests.configure_build(builder_config)
  # Fake path.
  api.profiles._merge_scripts_dir = api.path['start_dir']

  if 'tryserver' in builder_id.group:
    api.code_coverage.instrument(
        api.properties['files_to_instrument'],
        is_deps_only_change=api.properties.get('is_deps_only_change', False))
  if api.properties.get('mock_merged_profdata', True):
    api.path.mock_add_paths(
        api.profiles.profile_dir().join('unit-merged.profdata'))
    api.path.mock_add_paths(
        api.profiles.profile_dir().join('overall-merged.profdata'))
  if api.properties.get('mock_java_tests_metadata_path', True):
    api.path.mock_add_paths(
        api.chromium.output_dir.join('coverage').join('all.json.gz'))


#   if api.properties.get('mock_java_unit_tests_metadata_path', True):
#     api.path.mock_add_paths(
#         api.chromium.output_dir.join('coverage').join('unit_tests.json.gz'))
  if api.properties.get('mock_javascript_metadata_path', True):
    api.path.mock_add_paths(
        api.chromium.output_dir.join('devtools_code_coverage').join(
            'all.json.gz'))

  test_specs = [
      steps.LocalIsolatedScriptTestSpec.create('checkdeps'),
      # Binary name equals target name.
      steps.SwarmingGTestTestSpec.create('base_unittests'),
      # Binary name is different from target name.
      steps.SwarmingGTestTestSpec.create('xr_browser_tests'),
      # There is no binary, such as Python tests.
      steps.SwarmingGTestTestSpec.create('telemetry_gpu_unittests'),
      steps.SwarmingIsolatedScriptTestSpec.create(
          'blink_web_tests',
          merge=chromium_swarming.MergeScript.create(
              script=api.path['start_dir'].join('coverage', 'tests',
                                                'merge_blink_web_tests.py'),
              args=['random', 'args'],
          )),
      steps.SwarmingIsolatedScriptTestSpec.create(
          'ios_chrome_smoke_eg2tests_module'),
      steps.SwarmingIsolatedScriptTestSpec.create('ios_web_view_inttests')
  ]
  tests = [s.get_test() for s in test_specs]
  assert _NUM_TESTS == len(tests)

  for test in tests:
    step = test.name
    api.profiles.profile_dir(step)
    api.code_coverage.shard_merge(
        step,
        test.target_name,
        additional_merge=getattr(test.spec, 'merge', None),
        skip_validation=True,
        sparse=True)

  api.code_coverage.process_coverage_data(tests)

  # Exercise these properties to provide coverage only.
  _ = api.code_coverage.using_coverage


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='linux-chromeos-code-coverage'),
      api.code_coverage(use_clang_coverage=True),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.merge '
          'all profile files into a single .profdata'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload artifact to GS'),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.generate '
          'line number mapping from bot to Gerrit'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Extract '
          'directory metadata'),
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
          'profile merge errors', ['--root-dir']),
      api.post_process(post_process.StepCommandContains, (
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS),
                       ['None/out/Release/content_shell']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_exclusions_module_property',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='linux-chromeos-code-coverage'),
      api.code_coverage(
          use_clang_coverage=True,
          coverage_exclude_sources='ios_test_files_and_test_utils'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_exclusions',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='linux-chromeos-code-coverage'),
      api.code_coverage(
          use_clang_coverage=True, coverage_exclude_sources='all_test_files'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_reference_commit',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='linux-code-coverage'),
      api.code_coverage(
          use_clang_coverage=True, coverage_reference_commit='123hash'),
      api.post_process(
          post_process.StepCommandContains,
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS,
          ['--reference-commit', '123hash']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'javascript: full repo',
      api.chromium.generic_build(
          builder_group='chromium.fyi',
          builder='linux-chromeos-js-code-coverage'),
      api.code_coverage(use_javascript_coverage=True),
      api.post_process(post_process.MustRun, 'process javascript coverage'),
      api.post_process(
          post_process.MustRun, 'process javascript coverage.'
          'Generate JavaScript coverage metadata'),
      api.post_process(
          post_process.MustRun, 'process javascript coverage.'
          'Generate JavaScript coverage metadata'),
      api.post_process(
          post_process.MustRun, 'process javascript coverage.'
          'gsutil Upload JSON metadata'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'javascript: full repo with no coverage files',
      api.chromium.generic_build(
          builder_group='chromium.fyi',
          builder='linux-chromeos-js-code-coverage'),
      api.code_coverage(use_javascript_coverage=True),
      api.step_data(
          'process javascript coverage.'
          'Generate JavaScript coverage metadata',
          retcode=1),
      api.post_check(lambda check, steps: check(steps[
          'process javascript coverage.'
          'Generate JavaScript coverage metadata'].output_properties[
              'process_coverage_data_failure'] == True)),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'process javascript coverage for per-cl',
      api.chromium.try_build(
          builder_group='tryserver.chromium.chromiumos',
          builder='linux-chromeos-js-code-coverage'),
      api.code_coverage(use_javascript_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.js',
          'some/other/path/to/file.js',
      ]),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(post_process.MustRun, 'process javascript coverage'),
      api.post_process(
          post_process.MustRun, 'process javascript coverage.'
          'generate line number mapping from bot to Gerrit'),
      api.post_process(
          post_process.MustRun, 'process javascript coverage.'
          'Generate JavaScript coverage metadata'),
      api.post_process(
          post_process.MustRun, 'process javascript coverage.'
          'Generate JavaScript coverage metadata'),
      api.post_process(
          post_process.MustRun, 'process javascript coverage.'
          'gsutil Upload JSON metadata'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'javascript coverage skipped per-cl when no js files',
      api.chromium.try_build(
          builder_group='tryserver.chromium.chromiumos',
          builder='linux-chromeos-js-code-coverage'),
      api.code_coverage(use_javascript_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(
          post_process.MustRun,
          'skip processing coverage data because no source file changed'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tryserver',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.merge '
          'all profile files into a single .profdata'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload artifact to GS'),
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
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file%d.cc' % i for i in range(500)
      ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tryserver skip instrumenting if DEPS only change',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=['third_party/skia/file.cc']),
      api.properties(is_deps_only_change=True),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tryserver unsupported repo',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
          git_repo='https://chromium.googlesource.com/v8/v8'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.post_process(
          post_process.MustRun,
          'skip processing coverage data, project(s) '
          'chromium-review.googlesource.com/v8/v8 is(are) unsupported',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'merge errors',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='linux-code-coverage'),
      api.code_coverage(use_clang_coverage=True),
      api.override_step_data(
          'process clang code coverage data for overall test coverage.Finding '
          'profile merge errors',
          stdout=api.json.output(['some_step'])),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Finding '
          'profile merge errors'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip collecting coverage data',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=['some/path/to/non_source_file.txt']),
      api.post_process(
          post_process.MustRun,
          'skip processing coverage data because no source file changed'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip processing coverage data if not data is found',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
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
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='linux-code-coverage'),
      api.code_coverage(use_clang_coverage=True),
      api.step_data((
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS),
                    retcode=1),
      api.post_check(lambda check, steps: check(steps[
          'process clang code coverage data '
          'for overall test coverage.gsutil '
          'upload coverage metadata'
          ''].output_properties['process_coverage_data_failure'] == True)),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'do not raise failure for per-cl coverage',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.step_data((
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in %s tests' % _NUM_TESTS),
                    retcode=1),
      api.post_check(lambda check, steps: check(steps[
          'process clang code coverage data '
          'for overall test coverage.gsutil '
          'upload coverage metadata'
          ''].output_properties['process_coverage_data_failure'] == True)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'merged profdata does not exist',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='linux-code-coverage'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(mock_merged_profdata=False),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.skip '
          'processing because no profdata was generated'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'process java coverage for full-codebase',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='android-code-coverage'),
      api.code_coverage(use_java_coverage=True),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'Extract directory metadata'),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'Generate Java coverage metadata'),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'gsutil Upload JSON metadata'),
      api.post_process(post_process.MustRun, 'Clean up Java coverage files'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'process java coverage for full-codebase dual coverage',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='android-code-coverage'),
      api.code_coverage(
          use_java_coverage=True, coverage_test_types=['unit', 'overall']),
      api.post_process(
          post_process.MustRun, 'process java coverage (unit).'
          'Generate Java coverage metadata'),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'Generate Java coverage metadata'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip collecting coverage data for java',
      api.chromium.generic_build(
          builder_group='tryserver.chromium.android',
          builder='android-marshmallow-arm64-rel'),
      api.code_coverage(use_java_coverage=True),
      api.properties(files_to_instrument=['some/path/to/non_source_file.txt']),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(
          post_process.MustRun,
          'skip processing coverage data because no source file changed'),
      api.post_process(post_process.MustRun, 'Clean up Java coverage files'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'process java coverage for per-cl',
      api.chromium.try_build(
          builder_group='tryserver.chromium.android',
          builder='android-marshmallow-arm64-rel'),
      api.code_coverage(use_java_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.java',
          'some/other/path/to/file.java',
      ]),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'generate line number mapping from bot to Gerrit'),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'Generate Java coverage metadata'),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'gsutil Upload JSON metadata'),
      api.post_process(post_process.MustRun, 'Clean up Java coverage files'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'java metadata for tests does not exist',
      api.chromium.try_build(
          builder_group='tryserver.chromium.android',
          builder='android-marshmallow-arm64-rel'),
      api.code_coverage(use_java_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/FileTest.java',
          'some/other/path/to/FileTest.java',
      ]),
      api.properties(mock_java_tests_metadata_path=False),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'generate line number mapping from bot to Gerrit'),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'Generate Java coverage metadata'),
      api.post_process(
          post_process.MustRun, 'process java coverage (overall).'
          'skip processing because overall tests metadata was missing'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'raise failure for java full-codebase coverage',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='android-code-coverage'),
      api.code_coverage(use_java_coverage=True),
      api.step_data(
          'process java coverage (overall).Generate Java coverage metadata',
          retcode=1),
      api.post_check(lambda check, steps: check(steps[
          'process java coverage (overall).Generate Java coverage metadata'
      ].output_properties['process_coverage_data_failure'] == True)),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'do not raise failure for java per-cl coverage',
      api.chromium.try_build(
          builder_group='tryserver.chromium.android',
          builder='android-marshmallow-arm64-rel'),
      api.code_coverage(use_java_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.java',
          'some/other/path/to/file.java',
      ]),
      api.step_data(
          'process java coverage (overall).Generate Java coverage metadata',
          retcode=1),
      api.post_check(lambda check, steps: check(steps[
          'process java coverage (overall).Generate Java coverage metadata'
      ].output_properties['process_coverage_data_failure'] == True)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'android native code coverage CI',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='android-code-coverage-native'),
      api.code_coverage(use_clang_coverage=True),
      api.step_data(
          'process clang code coverage data for overall test coverage.'
          'Get all unstripped artifacts paths',
          api.json.output([
              '/chromium/output_dir/'
              'lib.unstrippedlibbase_unittests__library.so'
          ])),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.merge '
          'all profile files into a single .profdata'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload artifact to GS'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Finding '
          'profile merge errors'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.'
          'Get all unstripped artifacts paths'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Extract '
          'directory metadata'),
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
      'Fuchsia code coverage CI',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='fuchsia-code-coverage'),
      api.code_coverage(use_clang_coverage=True),
      api.step_data(
          'process clang code coverage data for overall test coverage.'
          'Get all unstripped artifacts paths',
          api.json.output(['/chromium/output_dir/'
                           'base_unittests__exec'])),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.merge '
          'all profile files into a single .profdata'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload artifact to GS'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Finding '
          'profile merge errors'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.'
          'Get all unstripped artifacts paths'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Extract '
          'directory metadata'),
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
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='ios-simulator-code-coverage'),
      api.code_coverage(use_clang_coverage=True),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.merge '
          'all profile files into a single .profdata'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload artifact to GS'),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.generate '
          'line number mapping from bot to Gerrit'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.Extract '
          'directory metadata'),
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
          'profile merge errors', ['--root-dir']),
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
      api.chromium.try_build(
          builder_group='tryserver.chromium.mac', builder='ios-simulator'),
      api.code_coverage(use_clang_coverage=True, coverage_test_types=['unit']),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.properties(xcode_build_version='11c29'),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for unit test coverage.merge '
          'all profile files into a single .profdata'),
      api.post_process(
          post_process.DoesNotRun,
          'process clang code coverage data for overall test coverage.merge '
          'all profile files into a single .profdata'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for unit test coverage.gsutil '
          'upload artifact to GS'),
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
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='linux-code-coverage'),
      api.code_coverage(
          use_clang_coverage=True,
          coverage_test_types=['unsupportedtest', 'overall']),
      api.post_process(
          post_process.MustRun,
          'Exception when validating test types to process: Unsupported test '
          'type unsupportedtest.'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'process dual test types in per-cl coverage',
      api.chromium.try_build(
          builder_group='tryserver.chromium.mac', builder='ios-simulator'),
      api.code_coverage(
          use_clang_coverage=True, coverage_test_types=['unit', 'overall']),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for unit test coverage'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip processing when wrong test type',
      api.chromium.try_build(
          builder_group='tryserver.chromium.mac', builder='ios-simulator'),
      api.code_coverage(
          use_clang_coverage=True, coverage_test_types=['instrument']),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.post_process(
          post_process.MustRun,
          'skip processing because of an exception when validating test types '
          'to process: Unsupported test type instrument.'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tryserver_win',
      api.chromium.try_build(
          builder_group='tryserver.chromium.win',
          builder='win10-rel-orchestrator'),
      api.code_coverage(use_clang_coverage=True),
      api.properties(files_to_instrument=[
          'some/path/to/file.cc',
          'some/other/path/to/file.cc',
      ]),
      api.post_process(post_process.MustRun, 'save paths of affected files'),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*',
                       _NUM_TESTS, _NUM_TESTS),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.merge '
          'all profile files into a single .profdata'),
      api.post_process(
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.gsutil '
          'upload artifact to GS'),
      api.post_process(
          post_process.StepCommandContains,
          'process clang code coverage data for overall test coverage.filter '
          'binaries with valid data for %s binaries' % (_NUM_TESTS - 2),
          ['None/out/Release/content_shell.exe']),
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
