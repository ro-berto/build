# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
  'test_utils',
]


def _GetToolSuffix(platform):
  if platform.is_linux:
    if platform.bits == 64:
      return 'linux64'
  elif platform.is_mac:
    return 'mac'
  # TODO(davidben): Add other platforms as they're ready.


def _GetExeSuffix(platform):
  # TODO(davidben): Add a Windows check when there's enough for a Windows bot.
  return ''


def GenSteps(api):
  # Sync and pull in everything.
  api.gclient.set_config('boringssl')
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()

  # Set up paths.
  bot_utils = api.path['checkout'].join('util', 'bot')
  go_env = bot_utils.join('go', 'env.py')
  build_dir = api.path['checkout'].join('build')
  api.path.makedirs('mkdir', build_dir)

  # Build BoringSSL itself.
  cmake = bot_utils.join('cmake-' + _GetToolSuffix(api.platform), 'bin',
                         'cmake' + _GetExeSuffix(api.platform))
  api.step('cmake', [cmake, '-GNinja', api.path['checkout']], cwd=build_dir)
  api.step('ninja', ['ninja', '-C', build_dir])

  # Run the unit tests.
  api.python('unit tests', go_env,
             ['go', 'run', api.path.join('util', 'all_tests.go'),
              '-json-output', api.test_utils.test_results()],
             cwd=api.path['checkout'])

  # Run the SSL tests.
  runner_dir = api.path['checkout'].join('ssl', 'test', 'runner')
  runner = build_dir.join('runner' + _GetExeSuffix(api.platform))
  api.python('build runner.go', go_env, ['go', 'build', '-o', runner],
             cwd=runner_dir)
  api.step('ssl tests', [runner, '-pipe', '-json-output',
                         api.test_utils.test_results()],
           cwd=runner_dir)


def GenTests(api):
  yield (
    api.test('linux') +
    api.platform('linux', 64) +
    api.properties.generic(mastername='client.boringssl', buildername='linux',
                           slavename='slavename') +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(True)) +
    api.override_step_data('ssl tests', api.test_utils.canned_test_output(True))
  )

  yield (
    api.test('mac') +
    api.platform('mac', 64) +
    api.properties.generic(mastername='client.boringssl', buildername='mac',
                           slavename='slavename') +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(True)) +
    api.override_step_data('ssl tests', api.test_utils.canned_test_output(True))
  )
