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
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

BUILD_CONFIG = 'Default'
BUILD_TARGETS = ['gn_all', 'openscreen_unittests', 'e2e_tests']
OPENSCREEN_REPO = 'https://chromium.googlesource.com/openscreen'

def _GetHostToolLabel(platform):
  if platform.is_linux and platform.bits == 64:
    return 'linux64'
  elif platform.is_mac:
    return 'mac'
  raise ValueError('unknown or unsupported platform')  # pragma: no cover


def RunSteps(api):
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
    host_tool_label = _GetHostToolLabel(api.platform)
    is_debug = str(api.properties.get('debug', False)).lower()
    is_asan = str(api.properties.get('is_asan', False)).lower()
    is_tsan = str(api.properties.get('is_tsan', False)).lower()
    is_gcc = str(api.properties.get('is_gcc', False)).lower()
    api.step('gn gen',
             [checkout_path.join('buildtools', host_tool_label, 'gn'), 'gen',
              output_path,
              '--args=is_debug={} is_asan={} is_tsan={} is_gcc={}'.format(
                  is_debug, is_asan, is_tsan, is_gcc)
              ])

    # NOTE: The following just runs Ninja without setting up the Mac toolchain
    # if this is being run on a non-Mac platform.
    with api.osx_sdk('mac'):
      ninja_cmd = [
          api.depot_tools.ninja_path, '-C', output_path, '-j',
          api.goma.recommended_goma_jobs
      ] + BUILD_TARGETS
      api.goma.build_with_goma(
          name='compile',
          ninja_command=ninja_cmd,
          ninja_log_outdir=output_path)
    api.step('Run unit tests', [output_path.join('openscreen_unittests')])

    # TODO(btolsch): Make these required when they appear stable on the bots.
    try:
      api.step('Run e2e tests', [output_path.join('e2e_tests')])
    except api.step.StepFailure:
      pass


def GenTests(api):
  yield api.test(
      'linux64_debug',
      api.platform('linux', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(debug=True, is_asan=True),
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
      api.properties(debug=True, is_asan=False, is_gcc=True),
  )
  yield api.test(
      'mac_debug',
      api.platform('mac', 64),
      api.buildbucket.try_build('openscreen', 'try'),
      api.properties(debug=True, is_asan=False),
  )
  yield api.test('linux64_debug (fail e2e tests)', api.platform('linux', 64),
                 api.buildbucket.try_build('openscreen', 'try'),
                 api.properties(debug=True, is_asan=True),
                 api.step_data('Run e2e tests', retcode=1))
