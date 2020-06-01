# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe for building and running tests for Open Screen stand-alone."""

DEPS = [
    'code_coverage',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/gsutil',
    'depot_tools/osx_sdk',
    'depot_tools/tryserver',
    'goma',
    'profiles',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/isolated',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'recipe_engine/swarming',
]

BUILD_CONFIG = 'Default'
UNIT_TEST_BINARY_NAME = 'openscreen_unittests'
E2E_TEST_BINARY_NAME = 'e2e_tests'
BUILD_TARGETS = ['gn_all', UNIT_TEST_BINARY_NAME, E2E_TEST_BINARY_NAME]
OPENSCREEN_REPO = 'https://chromium.googlesource.com/openscreen'

# Due to the oddities of how the recipe properties JSON string works, we need
# to know to wrap strings, but leave primitives such as boolean or integer
# alone. GN does not consider the quoted string "true" to be a boolean.
GN_PROPERTIES = [
    'is_debug', 'is_asan', 'is_tsan', 'is_gcc', 'target_cpu',
    'sysroot_platform', 'sysroot', 'target_sysroot_dir', 'use_coverage'
]

# List of dimensions used for starting swarming on ARM64.
SWARMING_DIMENSIONS = {
    'cpu': 'arm64',
    'pool': 'luci.flex.try',
    'os': 'Ubuntu-18.04'
}


class FileInfo:

  def __init__(self, input_path, output_dir, is_dir):
    self.input_path = input_path
    self.output_dir = output_dir
    self.is_dir = is_dir


def GetHostToolLabel(platform):
  """Determines what the platform label is, e.g. 'mac' or 'linux64'."""
  if platform.is_linux and platform.bits == 64:
    return 'linux64'
  elif platform.is_mac:
    return 'mac'
  raise ValueError('unknown or unsupported platform')  # pragma: no cover


def GenerateCoverageTestConstants(api, checkout_dir, output_dir):
  """Generates fake file paths used for validation in code coverage tests."""
  # Add fakes for the paths that are validated in SetCodeCoverageConstants()
  if api.properties.get('is_valid_coverage_test', False):
    llvm_dir = checkout_dir.join('third_party', 'llvm-build', 'Release+Asserts',
                                 'bin')
    api.path.mock_add_paths(checkout_dir.join('build', 'code_coverage'))
    api.path.mock_add_paths(llvm_dir.join('llvm-profdata'))
    api.path.mock_add_paths(llvm_dir.join('llvm-cov'))
    api.path.mock_add_paths(output_dir.join('default.profraw'))

  # Add fake .profraw data and destination path
  if api.properties.get('generate_test_profraw', False):
    root_dir = api.path['checkout']
    api.path.mock_add_paths(root_dir.join('default.profraw'))

  # Generate fake .profdata
  if api.properties.get('generate_test_profdata', False):
    api.path.mock_add_paths(output_dir.join('default.profdata'))


def GetChangedFiles(api, checkout_path):
  """Returns list of POSIX paths of files affected by patch."""
  files = []
  if api.tryserver.gerrit_change:
    patch_root = api.gclient.get_gerrit_patch_root()
    assert patch_root, ('local path is not configured for {}'.format(
        api.tryserver.gerrit_change_repo_url))
    with api.context(cwd=checkout_path):
      files = api.tryserver.get_files_affected_by_patch(patch_root)
    for i, path in enumerate(files):
      path = str(path)
      files[i] = api.path.relpath(path, checkout_path)
  return files


def FormatGnArg(properties, key):
  """Takes a specific keg, e.g. is_debug, and format the key and value pair as
     a valid gn argument."""
  value = properties.get(key, None)
  if value:
    format_string = '{}="{}"' if isinstance(value, str) else '{}={}'
    return format_string.format(key, value).lower()
  return ""


def FormatGnArgs(properties):
  """Takes a list of properties and maps them to string gn arguments."""
  mapper = lambda key: FormatGnArg(properties, key)
  return ' '.join([arg for arg in map(mapper, GN_PROPERTIES) if arg])


def UploadFilesToIsolateStorage(api, files):
  """Pushes files up to the isolate server storage."""
  with api.step.nest('Upload isolates'):
    isolate_dir = api.path.mkdtemp('isolate-directory')
    for file_info in files:
      output_dir = isolate_dir.join(file_info.output_dir)
      if file_info.is_dir:
        api.file.copytree("Copying tree: {}".format(file_info.input_path),
                          file_info.input_path, output_dir)
      else:
        api.file.ensure_directory("Ensuring directory: {}".format(output_dir),
                                  output_dir)
        api.file.copy("Copying file: {}".format(file_info.input_path),
                      file_info.input_path, output_dir)
    isolated = api.isolated.isolated(isolate_dir)
    isolated.add_dir(isolate_dir)
  return isolated.archive('Archive build outputs')


def CheckSwarmingResults(api, name, results):
  """Called after swarming.collect() to produce a proper step result."""
  for result in results:
    if (result.state == api.swarming.TaskState.COMPLETED or
        result.state == api.swarming.TaskState.TIMED_OUT):
      if not result.success:
        fail_text = '{} failure'.format(name)
        step = api.step(fail_text, None)
        step.presentation.status = 'FAILURE'
        raise api.step.StepFailure(fail_text)
    else:
      api.step.active_result.presentation.status = 'EXCEPTION'
      result.analyze()


def SwarmTests(api, output_path, checkout_path, dimensions):
  """Runs specific types of tests on a separate swarming bot."""
  TEST_DATA_DIR = 'test/data'
  # Format: file name, output folder, is directory?
  isolated_files = [
      FileInfo(output_path.join(UNIT_TEST_BINARY_NAME), "out/Default", False),
      FileInfo(output_path.join(E2E_TEST_BINARY_NAME), "out/Default", False),
      FileInfo(checkout_path.join(TEST_DATA_DIR), TEST_DATA_DIR, True)
  ]
  isolated_hash = UploadFilesToIsolateStorage(api, isolated_files)

  # Generate the swarming request
  request = api.swarming.task_request().with_name(UNIT_TEST_BINARY_NAME)
  request = (
      request.with_slice(
          0, request[0].with_command([
              './out/Default/{}'.format(UNIT_TEST_BINARY_NAME)
          ]).with_dimensions(**dimensions).with_isolated(isolated_hash)))
  e2e_request = api.swarming.task_request().with_name(E2E_TEST_BINARY_NAME)
  e2e_request = (
      e2e_request.with_slice(
          0, e2e_request[0].with_command([
              './out/Default/{}'.format(E2E_TEST_BINARY_NAME)
          ]).with_dimensions(**dimensions).with_isolated(isolated_hash)))

  # Run the actual tests
  metadata = api.swarming.trigger(
      'Trigger Open Screen Unit Tests', requests=[request])

  e2e_metadata = api.swarming.trigger(
      'Trigger E2E tests', requests=[e2e_request])

  # Collect the result of the task by metadata.
  output_directory = api.path.mkdtemp('swarming-output')
  results = api.swarming.collect(
      'collect unit tests',
      metadata,
      output_dir=output_directory,
      timeout='30m')
  CheckSwarmingResults(api, 'unit tests', results)

  e2e_output_directory = api.path.mkdtemp('e2e-swarming-output')
  e2e_results = api.swarming.collect(
      'collect E2E tests',
      e2e_metadata,
      output_dir=e2e_output_directory,
      timeout='30m')
  CheckSwarmingResults(api, 'e2e tests', e2e_results)


def SetCodeCoverageConstants(api, checkout_dir, host_tool_label):
  """Performs dependency injection on internal constants of the code_coverage
     module needed to allow for the code coverage module to function correctly.
  """
  llvm_dir = checkout_dir.join('third_party', 'llvm-build', 'Release+Asserts',
                               'bin')
  merge_libs_dir = checkout_dir.join('build', 'code_coverage')

  api.profiles._merge_scripts_dir = merge_libs_dir
  api.profiles._llvm_base_path = llvm_dir
  api.code_coverage._platform = host_tool_label
  api.code_coverage._use_clang_coverage = True

  paths_to_check = [
      api.profiles.llvm_profdata_exec, api.code_coverage.cov_executable,
      merge_libs_dir
  ]
  path_existance = {}
  for path in paths_to_check:
    path_existance[path] = api.path.exists(path)
  if not all(path_existance.values()):
    result = ''.join('\nhas {}: {}'.format(path, path_existance[path])
                     for path in path_existance)
    api.python.infra_failing_step(
        'code coverage executable dependencies missing!', result)


def CalculateCodeCoverage(api, output_path, unit_test_binary, e2e_test_binary):
  """Calculates code coverage from raw coverage data generated by prior test
       runs."""
  root_dir = api.path['checkout']

  # Configure a temporary directory where the code_coverage module knows
  # to look for .profdata files.
  temp_dir = api.profiles.profile_dir('profdata')

  # Process the raw code coverage data.
  api.python(
      'process raw coverage data',
      api.profiles.merge_results_script,
      args=[
          '--task-output-dir', root_dir, '--profdata-dir', temp_dir,
          '--llvm-profdata', api.profiles.llvm_profdata_exec,
          '--per-cl-coverage'
      ])

  # Validate that the script worked as expected, then bubble this up to
  # the trybot UI.
  source = output_path.join('default.profdata')
  dest = temp_dir.join('default.profdata')
  if api.path.exists(source) or api.path.exists(dest):
    api.python.succeeding_step('coverage data successfully processed', '')
  else:
    api.python.failing_step('failed to process coverage data', '')

  # Copy the generated profdata file to a temp directory where the
  # code_coverage tool knows to look for it.
  # NOTE: This is needed because the merge_lib.py chromium script does
  # not correctly respect the --profdata-dir parameter. This fix has
  # been added here rather than in merge_lib.py for two reasons:
  # - To keep openscreen's merge_lib.py in sync with that of chromium.
  # - So that if Chromium's merge_lib.py fixes this issue, the
  #   dependency can be updated without breaking our build
  if api.path.exists(source) and not api.path.exists(dest):
    api.file.copy('copy processed coverage data', source, dest)

  # Upload the coverage results to the code_coverage cloud storge
  # account, so that Gerrit can find it.
  # For more information, see:
  # https://source.chromium.org/chromium/chromium/tools/build/+/master:scripts/slave/recipe_modules/code_coverage/api.py;l=363  #pylint: disable=line-too-long
  api.code_coverage._process_clang_coverage_data(None, {unit_test_binary})


def RunTestsLocally(api, unit_test_binary, e2e_test_binary):
  """Runs unit tests and e2e tests locally"""
  api.step('run unit tests', [unit_test_binary])
  api.step('run e2e tests', [e2e_test_binary])


def RunTestsAndCoverageLocally(api, output_path, unit_test_binary,
                               e2e_test_binary):
  """Runs unit tests and e2e tests locally and calculates code coverage"""
  # Proceed with remaining tests for non-ARM bots.
  root_dir = api.path['checkout']
  with api.step.nest('run tests'):
    # Clean up invalid coverage data generated by build.
    #
    # TODO(crbug/1086998): Stop generating this invalid data.
    with api.step.nest('perform pre-test cleanup'):
      files = api.file.glob_paths(
          'get files',
          root_dir,
          '**/*.profraw',
          test_data=[output_path.join('default.profraw')])
      for path in files:
        api.file.remove('remove ' + str(path), path)

    # Run the Unit Tests, generating the .profraw data
    api.step('run unit tests', [unit_test_binary])

    # Ensure tests correctly generated coverage data.
    profraw_path = root_dir.join('default.profraw')
    if not api.path.exists(profraw_path):
      api.python.failing_step(
          'skip coverage calculations because no data was generated', '')

    # Use data generated from tests to calculate code coverage.
    else:
      with api.step.nest('calculate code coverage'):
        CalculateCodeCoverage(api, output_path, unit_test_binary,
                              e2e_test_binary)

    # TODO(issuetracker.google.com/155643967): Include E2E test coverage
    # with unit test coverage.
    api.step('run e2e tests', [e2e_test_binary])

  # Set output properties on the buildbot as required for code coverage
  # to function.
  # NOTE: This cannot be done in a nested step due to buildbot weirdness.
  # If it is, the output properties will not be reflected correctly for
  # the build.
  api.code_coverage._set_builder_output_properties_for_uploads()


def RunSteps(api):
  """Main function body for execution on the current bot."""
  openscreen_config = api.gclient.make_config()
  solution = openscreen_config.solutions.add()
  solution.name = 'openscreen'
  solution.url = OPENSCREEN_REPO
  solution.deps_file = 'DEPS'

  api.gclient.c = openscreen_config

  api.bot_update.ensure_checkout()
  api.gclient.runhooks()
  api.goma.ensure_goma()

  checkout_path = api.path['checkout']
  output_path = checkout_path.join('out', BUILD_CONFIG)
  unit_test_binary = output_path.join(UNIT_TEST_BINARY_NAME)
  e2e_test_binary = output_path.join(E2E_TEST_BINARY_NAME)

  GenerateCoverageTestConstants(api, checkout_path, output_path)

  env = {}
  if api.properties.get('is_asan', False):
    env['ASAN_SYMBOLIZER_PATH'] = str(
        api.profiles.llvm_exec_path('llvm-symbolizer'))

  with api.context(cwd=checkout_path, env=env):
    host_tool_label = GetHostToolLabel(api.platform)

    # Populate Code coverage tool with the set of files that changed.
    use_coverage = api.properties.get('use_coverage', False)
    full_repo_coverage = api.properties.get('is_ci', False)
    if use_coverage:
      with api.step.nest('initialize code coverage') as coverage_step:
        coverage_step.status = api.step.SUCCESS
        try:
          SetCodeCoverageConstants(api, checkout_path, host_tool_label)

          if full_repo_coverage:
            # NOTE: By skipping the below instrument() call, the
            # code_coverage  module is set to perform full-repo coverage
            # calculations.
            api.python.succeeding_step(
                'instrumentation skipped for full repo coverage', '')
          else:
            changed_files = GetChangedFiles(api, checkout_path)

            # Initialize code coverage.
            # For more details, see: https://goto.google.com/dmbjf
            #
            # NOTE: This step configures the code_coverage module to perform
            # per-CL coverage calculations.
            api.code_coverage.instrument(changed_files, output_dir=output_path)

            api.python.succeeding_step(
                'coverage calculations will proceed for {} files'.format(
                    len(changed_files)),
                ''.join('\n{}'.format(str(path)) for path in changed_files))
        except:  # pylint: disable=bare-except
          coverage_step.status = api.step.FAILURE
          use_coverage = False

    api.step('gn gen', [
        checkout_path.join('buildtools', host_tool_label, 'gn'), 'gen',
        output_path, '--args={}'.format(FormatGnArgs(api.properties))
    ])

    # NOTE: The following just runs Ninja without setting up the Mac toolchain
    # if this is being run on a non-Mac platform.
    with api.osx_sdk('mac'):
      ninja_cmd = [api.depot_tools.ninja_path, '-C', output_path]
      ninja_cmd.extend(['-j', api.goma.recommended_goma_jobs])
      ninja_cmd.extend(BUILD_TARGETS)
      api.goma.build_with_goma(
          name='compile',
          ninja_command=ninja_cmd,
          ninja_log_outdir=output_path)

    # ARM64 tests cannot be run on the building bot, since they must be
    # cross-compiled from x86-64.
    is_arm64 = api.properties.get('target_cpu') == 'arm64'
    if is_arm64:
      assert not use_coverage
      SwarmTests(api, output_path, checkout_path, SWARMING_DIMENSIONS)
      return

    if use_coverage:
      RunTestsAndCoverageLocally(api, output_path, unit_test_binary,
                                 e2e_test_binary)
    else:
      RunTestsLocally(api, unit_test_binary, e2e_test_binary)


def GenTests(api):
  """Generates tests used to verify there are no python usage errors."""
  yield api.test(
      'linux64_coverage_debug',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(
          is_debug=True,
          is_asan=True,
          use_coverage=True,
          is_valid_coverage_test=True,
          generate_test_profraw=True,
          generate_test_profdata=True),
      api.step_data(
          'run tests.calculate code coverage.process raw coverage data',
          retcode=0),
  )
  yield api.test(
      'linux64_coverage_debug_no_profdata_does_fail_bot',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(
          is_debug=True,
          is_asan=True,
          use_coverage=True,
          is_valid_coverage_test=True,
          generate_test_profraw=True,
      ),
      api.step_data(
          'run tests.calculate code coverage.process raw coverage data',
          retcode=0),
  )
  yield api.test(
      'linux64_coverage_debug_no_profraw_does_fail_bot',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(
          is_debug=True,
          is_asan=True,
          use_coverage=True,
          is_valid_coverage_test=True),
  )
  yield api.test(
      'linux64_coverage_debug_failed_coverage_init',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(is_debug=True, is_asan=True, use_coverage=True),
  )
  yield api.test(
      'linux64_coverage_debug_full_repo_coverage',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'ci'),
      api.properties(
          is_debug=True,
          is_asan=True,
          is_ci=True,
          use_coverage=True,
          is_valid_coverage_test=True,
          generate_test_profraw=True,
          generate_test_profdata=True),
      api.step_data(
          'run tests.calculate code coverage.process raw coverage data',
          retcode=0),
  )
  yield api.test(
      'linux64_debug',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(is_debug=True, is_asan=True),
  )
  yield api.test(
      'linux64_tsan',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(is_tsan=True),
  )
  yield api.test(
      'linux64_debug_gcc',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(is_debug=True, is_asan=False, is_gcc=True),
  )
  yield api.test(
      'mac_debug',
      api.platform('mac', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(is_debug=True),
  )
  yield api.test('linux_arm64_debug', api.platform('linux', 64),
                 api.buildbucket.try_build('openscreen', 'try'),
                 api.properties(is_debug=True, target_cpu='arm64'))
  failed_result = api.swarming.task_result(
      id='0',
      name=UNIT_TEST_BINARY_NAME,
      state=api.swarming.TaskState.COMPLETED,
      failure=True)
  yield api.test(
      'linux_arm64_debug_with_collect_COMPLETED_and_failed',
      api.platform('linux', 64), api.buildbucket.try_build('openscreen', 'try'),
      api.properties(is_debug=True, target_cpu='arm64'),
      api.override_step_data('collect unit tests',
                             api.swarming.collect([failed_result])))
  timeout_result = api.swarming.task_result(
      id='0',
      name=UNIT_TEST_BINARY_NAME,
      state=api.swarming.TaskState.TIMED_OUT)
  yield api.test(
      'linux_arm64_debug_with_collect_TIMED_OUT', api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(is_debug=True, target_cpu='arm64'),
      api.override_step_data('collect unit tests',
                             api.swarming.collect([timeout_result])))
  died_result = api.swarming.task_result(
      id='0', name=UNIT_TEST_BINARY_NAME, state=api.swarming.TaskState.BOT_DIED)
  yield api.test(
      'linux_arm64_debug_with_collect_BOT_DIED', api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(is_debug=True, target_cpu='arm64'),
      api.override_step_data('collect unit tests',
                             api.swarming.collect([died_result])))
