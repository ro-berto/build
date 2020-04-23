# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe for building and running tests for Open Screen stand-alone."""

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/osx_sdk',
    'depot_tools/tryserver',
    'goma',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/isolated',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'recipe_engine/swarming',
]

BUILD_CONFIG = 'Default'
UNIT_TEST_BINARY_NAME = 'openscreen_unittests'
BUILD_TARGETS = ['gn_all', UNIT_TEST_BINARY_NAME, 'e2e_tests']
OPENSCREEN_REPO = 'https://chromium.googlesource.com/openscreen'

# Due to the oddities of how the recipe properties JSON string works, we need
# to know to wrap strings, but leave primitives such as boolean or integer
# alone. GN does not consider the quoted string "true" to be a boolean.
GN_PROPERTIES = [
    'is_debug', 'is_asan', 'is_tsan', 'is_gcc', 'target_cpu',
    'sysroot_platform', 'sysroot', 'target_sysroot_dir'
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


def SwarmTests(api, output_path, checkout_path, dimensions):
  """Runs specific types of tests on a separate swarming bot."""

  TEST_DATA_DIR = "test/data"
  # Format: output folder, file name, is directory?
  isolated_files = [
      FileInfo(output_path.join(UNIT_TEST_BINARY_NAME), "out/Default", False),
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

  # Run the actual tests
  metadata = api.swarming.trigger(
      'Trigger Open Screen Unit Tests', requests=[request])

  # Collect the result of the task by metadata.
  output_directory = api.path.mkdtemp('swarming-output')
  results = api.swarming.collect(
      'collect', metadata, output_dir=output_directory, timeout='30m')
  for result in results:
    result.analyze()


def RunTestsLocally(api, output_path):
  """Runs all types of enabled tests on the current bot."""
  api.step('Run unit tests', [output_path.join(UNIT_TEST_BINARY_NAME)])

  # TODO(btolsch): Make these required when they appear stable on the bots.
  # TODO(jophba): Add to swarming when they are stable.
  try:
    api.step('Run e2e tests', [output_path.join('e2e_tests')])
  except api.step.StepFailure:
    pass


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
  env = {}

  if api.properties.get('is_asan', False):
    env['ASAN_SYMBOLIZER_PATH'] = str(
        checkout_path.join('third_party', 'llvm-build', 'Release+Asserts',
                           'bin', 'llvm-symbolizer'))

  with api.context(cwd=checkout_path, env=env):
    host_tool_label = GetHostToolLabel(api.platform)
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
      SwarmTests(api, output_path, checkout_path, SWARMING_DIMENSIONS)
    else:
      RunTestsLocally(api, output_path)



def GenTests(api):
  """Generates tests used to verify there are no python usage errors."""
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
  yield api.test('linux64_debug (fail e2e tests)', api.platform('linux', 64),
                 api.buildbucket.try_build('openscreen', 'try'),
                 api.properties(is_debug=True, is_asan=True),
                 api.step_data('Run e2e tests', retcode=1))
