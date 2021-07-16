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
    'recipe_engine/cas',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'recipe_engine/swarming',
]

# Open Screen specific paths and repository information.
BUILD_CONFIG = 'Default'
UNIT_TEST_BINARY_NAME = 'openscreen_unittests'
E2E_TEST_BINARY_NAME = 'e2e_tests'
BUILD_TARGETS = ['gn_all', UNIT_TEST_BINARY_NAME, E2E_TEST_BINARY_NAME]
OPENSCREEN_REPO = 'https://chromium.googlesource.com/openscreen'

GN_PROPERTIES = [
    'is_debug', 'is_asan', 'is_tsan', 'is_gcc', 'target_cpu',
    'sysroot_platform', 'sysroot', 'target_sysroot_dir', 'use_coverage'
]

# List of dimensions used for starting swarming on ARM64.
SWARMING_DIMENSIONS = {'cpu': 'arm64', 'os': 'Ubuntu-20.04'}

# LUCI pool information.
FLEX_TRY_POOL = 'luci.flex.try'
FLEX_CI_POOL = 'luci.flex.ci'
POOL_DIMENSION = 'pool'


class RepositoryPaths:
  """Container for checkout_path dependent repository paths, such as
     unit test binary location.
  """

  def __init__(self, api):
    """Initializer for RepositoryPaths.

    Args:
        api (recipe_api.RecipeApi): API generated from recipe dependencies.
    """
    self.checkout_path = api.path['checkout']
    self.output_path = self.checkout_path.join('out', BUILD_CONFIG)
    self.unit_test_binary_path = self.output_path.join(UNIT_TEST_BINARY_NAME)
    self.e2e_test_binary_path = self.output_path.join(E2E_TEST_BINARY_NAME)
    self.test_data_path = self.checkout_path.join('test', 'data')


def GetSwarmingDimensions(is_ci):
  """Get a list of swarming dimensions to pass to swarming API.

  Args:
      is_ci (bool): Whether this is the CI pool (True) or the TRY pool (False).

  Returns:
      dict of str=>str: dimensions to use for swarming.
  """
  dimensions = SWARMING_DIMENSIONS
  dimensions[POOL_DIMENSION] = FLEX_CI_POOL if is_ci else FLEX_TRY_POOL
  return dimensions


def GetHostToolLabel(platform):
  """Determines what the platform label is, e.g. 'mac' or 'linux64'.

  Args:
      platform (api platform): Platform information from recipes API

  Returns:
      str: platform host tool label.
  """
  if platform.is_linux and platform.bits == 64:
    return 'linux64'
  elif platform.is_mac:
    return 'mac'
  raise ValueError('unknown or unsupported platform')  # pragma: no cover


def GenerateCoverageTestConstants(api, paths):
  """Generates fake file paths used for validation in code coverage tests.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      paths (RepositoryPaths): Checkout-dependent repository files.
  """
  # Add fakes for the paths that are validated in SetCodeCoverageConstants()
  if api.properties.get('is_valid_coverage_test', False):
    llvm_dir = paths.checkout_path.join('third_party', 'llvm-build',
                                        'Release+Asserts', 'bin')
    api.path.mock_add_paths(paths.checkout_path.join('build', 'code_coverage'))
    api.path.mock_add_paths(llvm_dir.join('llvm-profdata'))
    api.path.mock_add_paths(llvm_dir.join('llvm-cov'))
    api.path.mock_add_paths(paths.output_path.join('default.profraw'))

  # Add fake .profraw data and destination path
  if api.properties.get('generate_test_profraw', False):
    api.path.mock_add_paths(paths.checkout_path.join('default.profraw'))

  # Generate fake .profdata
  if api.properties.get('generate_test_profdata', False):
    api.path.mock_add_paths(paths.output_path.join('default.profdata'))


def GetChangedFiles(api, checkout_path):
  """Returns list of POSIX paths of files affected by patch.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      checkout_path (os.path): Location of open screen checkout.

  Returns:
      list: os.path: list of changed files.
  """
  files = []
  if api.tryserver.gerrit_change:
    patch_root = api.gclient.get_gerrit_patch_root()
    assert patch_root, ('local path is not configured for {}'.format(
        api.tryserver.gerrit_change_repo_url))
    with api.context(cwd=checkout_path):
      files = api.tryserver.get_files_affected_by_patch(patch_root)
    for i, path in enumerate(files):
      files[i] = api.path.relpath(str(path), checkout_path)
  return files


def FormatGnArg(properties, key):
  """Takes a specific key and formats the key and value pair as
     a valid gn argument.

  Args:
      properties (dict of str=>str): Recipe API properties to combine for GN.
      key (str): API property name to grab from Recipe API dictionary.

  Returns:
      str: Formatted key value pair as GN argument
  """
  value = properties.get(key, None)
  if value:
    format_string = '{}="{}"' if isinstance(value, str) else '{}={}'
    return format_string.format(key, value).lower()
  return ""


def FormatGnArgs(properties):
  """Takes a list of properties and maps them to string gn arguments.

  Args:
      properties (dict of str=>str): Recipe API properties to combine for GN.

  Returns:
      str: formatted GN arguments.
  """
  mapper = lambda key: FormatGnArg(properties, key)
  return ' '.join([arg for arg in map(mapper, GN_PROPERTIES) if arg])


def UploadOpenscreenTestFilesToCas(api, paths):
  """Pushes files up to RBE-CAS server storage.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      paths (RepositoryPaths): Checkout-dependent repository files.

  Returns:
      str: CAS digest of file archive.
  """
  return api.cas.archive('upload files to cas', paths.checkout_path,
                         paths.unit_test_binary_path,
                         paths.e2e_test_binary_path, paths.test_data_path)


def CheckSwarmingResults(api, name, results):
  """Called after swarming.collect() to produce a proper step result.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      name (str): Name of step to use for failures.
      results (list: TaskResult): Collected swarming results.

  Raises:
      api.step.StepFailure: swarming completed and failed, or timed out.
  """
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


def GenerateRequest(api, binary, digest, dimensions):
  """Generates a swarming request to run a |binary| from out/Default using
  the CAS digest |digest|.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      binary (str): Binary to execute, such as unittests.
      digest (str): CAS digest to download as part of execution.
      dimensions (dict of str=>str): Dimensions to be used to generate a
          request. Must be valid swarming selection dimensions to be
          unpacked as **kwargs, such as pool or os.

  Returns:
    TaskRequest: task request to execute on swarming bot.
  """
  request = api.swarming.task_request().with_name(binary)

  # Quick note about the swarming API. Swarming Tasks are composed of "slices"
  # made of individual TaskRequest objects. The task_request() getter returns
  # a basic request with one mostly empty TaskRequest that can be used as a
  # template to generate slices.
  # For more information, see the swarming guide:
  # https://chromium.googlesource.com/infra/luci/luci-py/+/main/appengine/swarming/doc/User-Guide.md#task #pylint: disable=line-too-long
  task_slice = request[0].with_command([
      './out/{}/{}'.format(BUILD_CONFIG, binary)
  ]).with_dimensions(**dimensions).with_cas_input_root(digest)

  request = request.with_slice(0, task_slice)
  return request


def SwarmTests(api, paths, dimensions):
  """Runs specific types of tests on a separate swarming bot.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      paths (RepositoryPaths): Checkout-dependent repository files.
      dimensions (dict of str=>str): Dimensions to be used to generate a
          request. Must be valid swarming selection dimensions to be
          unpacked as **kwargs, such as pool or os.
  """

  cas_digest = UploadOpenscreenTestFilesToCas(api, paths)

  # Generate the swarming request
  unittest_request = GenerateRequest(api, UNIT_TEST_BINARY_NAME, cas_digest,
                                     dimensions)
  unittest_metadata = api.swarming.trigger(
      'trigger unit tests', requests=[unittest_request])

  e2e_request = GenerateRequest(api, E2E_TEST_BINARY_NAME, cas_digest,
                                dimensions)
  e2e_metadata = api.swarming.trigger(
      'trigger e2e tests', requests=[e2e_request])

  # Collect the result of the task by metadata.
  unittest_output_directory = api.path.mkdtemp('swarming-output')
  unittest_results = api.swarming.collect(
      'collect unit tests',
      unittest_metadata,
      output_dir=unittest_output_directory,
      timeout='30m')
  CheckSwarmingResults(api, 'unit tests', unittest_results)

  e2e_output_directory = api.path.mkdtemp('e2e-swarming-output')
  e2e_results = api.swarming.collect(
      'collect e2e tests',
      e2e_metadata,
      output_dir=e2e_output_directory,
      timeout='30m')
  CheckSwarmingResults(api, 'e2e tests', e2e_results)


def SetCodeCoverageConstants(api, checkout_path, host_tool_label):
  """Performs dependency injection on internal constants of the code_coverage
     module needed to allow for the code coverage module to function correctly.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      checkout_path (os.path): Location of open screen checkout.
      host_tool_label (str): Host label from GetHostToolLabel.
  """
  llvm_dir = checkout_path.join('third_party', 'llvm-build', 'Release+Asserts',
                                'bin')
  merge_libs_dir = checkout_path.join('build', 'code_coverage')

  api.profiles._merge_scripts_dir = merge_libs_dir
  api.profiles._llvm_base_path = llvm_dir
  api.code_coverage._platform = host_tool_label
  api.code_coverage._use_clang_coverage = True
  api.code_coverage._include_component_mapping = False

  exists = {
      p: api.path.exists(p) for p in [
          api.profiles.llvm_profdata_exec, api.code_coverage.cov_executable,
          merge_libs_dir
      ]
  }
  if not all(exists.values()):
    result = ''.join('\nhas {}: {}'.format(p, e) for (p, e) in exists.items())
    api.python.infra_failing_step(
        'code coverage executable dependencies missing!', result)


def CalculateCodeCoverage(api, paths):
  """Calculates code coverage from raw coverage data generated by prior test
       runs.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      paths (RepositoryPaths): Checkout-dependent repository files.
  """
  # Configure a temporary directory where the code_coverage module knows
  # to look for .profdata files.
  temp_dir = api.profiles.profile_dir('profdata')

  # Process the raw code coverage data.
  api.python(
      'process raw coverage data',
      api.profiles.merge_results_script,
      args=[
          '--task-output-dir', paths.checkout_path, '--profdata-dir', temp_dir,
          '--llvm-profdata', api.profiles.llvm_profdata_exec,
          '--per-cl-coverage'
      ])

  # Validate that the script worked as expected, then bubble this up to
  # the trybot UI.
  source = paths.output_path.join('default.profdata')
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
  # https://source.chromium.org/chromium/chromium/tools/build/+/main:scripts/slave/recipe_modules/code_coverage/api.py;l=363  #pylint: disable=line-too-long
  api.code_coverage.process_clang_coverage_data(
      binaries={paths.unit_test_binary_path})


def RunTestsLocally(api, paths):
  """Runs unit tests and e2e tests locally.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      paths (RepositoryPaths): Checkout-dependent repository files.
  """
  api.step('run unit tests', [paths.unit_test_binary_path])
  api.step('run e2e tests', [paths.e2e_test_binary_path])


def RunTestsAndCoverageLocally(api, paths):
  """Runs unit tests and e2e tests locally and calculates code coverage.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
      paths (RepositoryPaths): Checkout-dependent repository files.
  """
  # Proceed with remaining tests for non-ARM bots.
  with api.step.nest('run tests'):
    # Clean up invalid coverage data generated by build.
    #
    # TODO(crbug/1086998): Stop generating this invalid data.
    with api.step.nest('perform pre-test cleanup'):
      files = api.file.glob_paths(
          'get files',
          paths.checkout_path,
          '**/*.profraw',
          test_data=[paths.output_path.join('default.profraw')])
      for path in files:
        api.file.remove('remove ' + str(path), path)

    # Run the Unit Tests, generating the .profraw data
    api.step('run unit tests', [paths.unit_test_binary_path])

    # Ensure tests correctly generated coverage data.
    profraw_path = paths.checkout_path.join('default.profraw')
    if not api.path.exists(profraw_path):
      api.python.failing_step(
          'skip coverage calculations because no data was generated', '')

    # Use data generated from tests to calculate code coverage.
    else:
      with api.step.nest('calculate code coverage'):
        CalculateCodeCoverage(api, paths)

    # TODO(issuetracker.google.com/155643967): Include E2E test coverage
    # with unit test coverage.
    api.step('run e2e tests', [paths.e2e_test_binary_path])

  # Set output properties on the buildbot as required for code coverage
  # to function.
  # NOTE: This cannot be done in a nested step due to buildbot weirdness.
  # If it is, the output properties will not be reflected correctly for
  # the build.
  api.code_coverage._set_builder_output_properties_for_uploads()


def RunSteps(api):
  """Main function body for execution on the current bot.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.
  """
  openscreen_config = api.gclient.make_config()
  solution = openscreen_config.solutions.add()
  solution.name = 'openscreen'
  solution.url = OPENSCREEN_REPO
  solution.deps_file = 'DEPS'

  api.gclient.c = openscreen_config

  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

  is_gcc = api.properties.get('is_gcc', False)
  should_use_goma = not is_gcc
  if should_use_goma:
    api.goma.ensure_goma()

  paths = RepositoryPaths(api)
  GenerateCoverageTestConstants(api, paths)

  env = {}
  if api.properties.get('is_asan', False):
    env['ASAN_SYMBOLIZER_PATH'] = str(
        api.profiles.llvm_exec_path('llvm-symbolizer'))

  is_ci = api.properties.get('is_ci', False)
  with api.context(cwd=paths.checkout_path, env=env):
    host_tool_label = GetHostToolLabel(api.platform)

    # Populate Code coverage tool with the set of files that changed.
    use_coverage = api.properties.get('use_coverage', False)
    if use_coverage:
      with api.step.nest('initialize code coverage') as coverage_step:
        coverage_step.status = api.step.SUCCESS
        try:
          SetCodeCoverageConstants(api, paths.checkout_path, host_tool_label)

          # Only continuous integration bots run full-repo coverage--trybots
          # only run per-cl coverage.
          if is_ci:
            # NOTE: By skipping the below instrument() call, the
            # code_coverage  module is set to perform full-repo coverage
            # calculations.
            api.python.succeeding_step(
                'instrumentation skipped for full repo coverage', '')
          else:
            changed_files = GetChangedFiles(api, paths.checkout_path)

            # Initialize code coverage.
            # For more details, see: https://goto.google.com/dmbjf
            #
            # NOTE: This step configures the code_coverage module to perform
            # per-CL coverage calculations.
            api.code_coverage.instrument(
                changed_files, output_dir=paths.output_path)

            api.python.succeeding_step(
                'coverage calculations will proceed for {} files'.format(
                    len(changed_files)),
                ''.join('\n{}'.format(str(path)) for path in changed_files))
        except:  # pylint: disable=bare-except
          coverage_step.status = api.step.FAILURE
          use_coverage = False

    api.python(
        'gn gen', api.depot_tools.gn_py_path,
        ['gen', paths.output_path, '--args=' + FormatGnArgs(api.properties)])

    # NOTE: The following just runs Ninja without setting up the Mac toolchain
    # if this is being run on a non-Mac platform.
    with api.osx_sdk('mac'):
      ninja_cmd = [api.depot_tools.ninja_path, '-C', paths.output_path]
      if should_use_goma:
        ninja_cmd.extend(['-j', api.goma.recommended_goma_jobs])
      ninja_cmd.extend(BUILD_TARGETS)

      if should_use_goma:
        api.goma.build_with_goma(
            name='compile',
            ninja_command=ninja_cmd,
            ninja_log_outdir=paths.output_path)
      else:
        api.step('compile with ninja', ninja_cmd)

    # ARM64 tests cannot be run on the building bot, since they must be
    # cross-compiled from x86-64.
    is_arm64 = api.properties.get('target_cpu') == 'arm64'
    if is_arm64:
      assert not use_coverage, "coverage is not supported on ARM64 builds."
      SwarmTests(api, paths, GetSwarmingDimensions(is_ci))
    elif use_coverage:
      RunTestsAndCoverageLocally(api, paths)
    else:
      RunTestsLocally(api, paths)


def GenTests(api):
  """Generates tests used to verify there are no python usage errors.

  Args:
      api (recipe_api.RecipeApi): API generated from recipe dependencies.

  Yields:
      tests: Generated API tests to be used to verify usage.
  """
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
  yield api.test('linux_arm64_debug_ci', api.platform('linux', 64),
                 api.buildbucket.try_build('openscreen', 'ci'),
                 api.properties(is_debug=True, target_cpu='arm64', is_ci=True))
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
