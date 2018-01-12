# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot recipe definition for the various Crashpad continuous builders.
"""

import ast

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


FAKE_SWARMING_TEST_SPEC = """\
[
  {
    'builders': ['crashpad_win_x86_wow64_rel'],
    'step_name': 'run_tests_on_x86',
    'isolate': 'out/Debug/run_tests.isolate',
    'args': [
       '-d', 'os', 'Windows-7',
       '-d', 'os', 'x86-32',
       '-d', 'os', 'Chrome',
    ],
  },
]
"""

def RunSteps(api):
  """Generates the sequence of steps that will be run by the slave."""
  api.gclient.set_config('crashpad')

  buildername = api.properties['buildername']
  env = {}

  target_os = api.m.properties.get('target_os')
  if target_os:
    api.gclient.c.target_os = {target_os}
  is_fuchsia = target_os == 'fuchsia'
  config = api.m.properties['config']
  is_debug = config == 'Debug'

  api.bot_update.ensure_checkout()

  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmtree('out', api.path['checkout'].join('out'))

  if '_x86' in buildername:
    env = {'GYP_DEFINES': 'target_arch=ia32'}
  with api.context(env=env):
    api.gclient.runhooks()

  # On Windows, we need to test:
  # a) x64 OS, x64 handler, x64 client
  # b) x64 OS, x64 handler, x86 client
  # c) x64 OS, x86 handler, x86 client
  # d) x86 OS, x86 handler, x86 client
  #
  # c) is tested on the _x86_wow64 bots.
  #
  # d) is tested on the _x86 bots.
  #
  # a) and b) are tested on the _x64 bots. Crashpad's gclient takes care of
  # generating Debug == x86 and Debug_x64 == x64 when target_arch==x64 (the
  # default). So, we just need to make sure to build both the suffixed and
  # unsuffixed trees, and then make sure to run the tests from the _x64 tree.

  dirname = config
  if is_fuchsia:
    # Fuchsia has only a GN build.
    path = api.path['checkout'].join('out', dirname)
    args = 'target_os="fuchsia" is_debug=' + ('true' if is_debug else 'false')
    with api.context(cwd=api.path['checkout']):
      api.step('generate build files', ['gn', 'gen', path, '--args=' + args])
  else:
    # Other platforms still default to the gyp build, so the build files have
    # already been generated during runhooks.
    path = api.path['checkout'].join('out', dirname)

  api.step('compile with ninja', ['ninja', '-C', path])

  if '_x64' in buildername and not is_fuchsia:
    # Note that we modify the dirname on x64 because we want to handle variants
    # a) and b) above.
    dirname += '_x64'
    path = api.path['checkout'].join('out', dirname)
    api.step('compile with ninja', ['ninja', '-C', path])

  if is_fuchsia:
    # Start a QEMU instance.
    api.python('start qemu',
               api.path['checkout'].join('build', 'run_fuchsia_qemu.py'),
               args=['start'])

  api.python('run tests',
             api.path['checkout'].join('build', 'run_tests.py'),
             args=[path],
             timeout=5*60)

  if is_fuchsia:
    # Shut down the QEMU instance.
    api.python('stop qemu',
               api.path['checkout'].join('build', 'run_fuchsia_qemu.py'),
               args=['stop'])

  test_spec_path = api.path['checkout'].join('build', 'swarming_test_spec.pyl')
  if api.path.exists(test_spec_path):
    file_contents = api.file.read_text('read swarming_test_spec',
        test_spec_path, test_data=FAKE_SWARMING_TEST_SPEC)

    try:
      swarming_test_spec = ast.literal_eval(file_contents)
    except Exception: # pragma: no cover
      # TODO(crbug.com/743139) figure out how to handle different kinds of
      # errors cleanly.
      api.step.fail()
      return

    for spec in swarming_test_spec:
      if buildername in spec['builders']:
        api.python(
            spec['step_name'],
            api.path['checkout'].join('build', 'run_on_swarming.py'),
            args=[api.path['checkout'].join(spec['isolate'][2:])] + spec['args'])


def GenTests(api):
  # Only test a single clobber case.
  test = 'crashpad_mac_dbg'
  yield(api.test(test + '_clobber') +
        api.properties.generic(buildername=test, config='Debug', clobber=True))

  tests = [
      test,
      'crashpad_try_mac_rel',
      'crashpad_try_win_x64_dbg',
      'crashpad_win_x64_rel',
      'crashpad_try_win_x86_wow64_dbg',
      'crashpad_win_x86_wow64_rel',
  ]
  for t in tests:
    yield(api.test(t) +
          api.properties.generic(buildername=t,
                                 config='Debug' if '_dbg' in t else 'Release') +
          api.path.exists(api.path['checkout'].join(
              'build', 'swarming_test_spec.pyl')))

  tests_with_target_os_fuchsia = [
      'crashpad_fuchsia_x64_dbg',
      'crashpad_fuchsia_x64_rel',
  ]
  for t in tests_with_target_os_fuchsia:
    yield(api.test(t) +
          api.properties.generic(buildername=t,
                                 config='Debug' if '_dbg' in t else 'Release',
                                 target_os='fuchsia') +
          api.path.exists(api.path['checkout'].join(
              'build', 'swarming_test_spec.pyl')))
