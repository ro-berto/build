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
    'builders': ['crashpad_try_win_dbg'],
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
  target_cpu = api.m.properties.get('target_cpu')
  is_fuchsia = target_os == 'fuchsia'
  is_linux = target_os == 'linux'
  is_win = target_os == 'win'
  config = api.m.properties['config']
  is_debug = config == 'Debug'

  api.bot_update.ensure_checkout()

  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmtree('out', api.path['checkout'].join('out'))

  with api.context(env=env):
    api.gclient.runhooks()

  dirname = config
  if is_fuchsia or is_linux:
    # Generic GN build.
    path = api.path['checkout'].join('out', dirname)
    args = 'target_os="' + target_os + '" target_cpu="' + target_cpu + '"' + \
           ' is_debug=' + ('true' if is_debug else 'false')
    with api.context(cwd=api.path['checkout']):
      api.step('generate build files', ['gn', 'gen', path, '--args=' + args])
  elif is_win:
    # On Windows, we ought to test:
    # a) x64 OS, x64 handler, x64 client
    # b) x64 OS, x64 handler, x86 client
    # c) x64 OS, x86 handler, x86 client
    # d) x86 OS, x86 handler, x86 client
    #
    # d) used to be tested on _x86 bots, but they have been removed.
    #
    # Two build directories are generated, one for x86 and one for x64, which
    # allows testing a), b), and c). As the bot time is dominated by machine
    # setup and build time, we do not separate these onto separate slaves.
    # Additionally, they're all on the same physical machine currently, so
    # there's no upside in parallelism.

    x86_path = api.path['checkout'].join('out', dirname + '_x86')
    x64_path = api.path['checkout'].join('out', dirname + '_x64')
    args = 'target_os="win" is_debug=' + ('true' if is_debug else 'false')
    with api.context(cwd=api.path['checkout']):
      api.step('generate build files x86',
               ['gn', 'gen', x86_path, '--args=' + args + ' target_cpu="x86"'])
      api.step('generate build files x64',
               ['gn', 'gen', x64_path, '--args=' + args + ' target_cpu="x64"'])
  else:
    # Other platforms still default to the gyp build, so the build files have
    # already been generated during runhooks.
    path = api.path['checkout'].join('out', dirname)

  def run_tests(build_dir, env=None):
    if is_fuchsia:
      # Start a QEMU instance.
      api.python('start qemu',
                 api.path['checkout'].join('build', 'run_fuchsia_qemu.py'),
                 args=['start'])

    with api.context(env=env):
      api.python('run tests',
                api.path['checkout'].join('build', 'run_tests.py'),
                args=[build_dir],
                timeout=5*60)

    if is_fuchsia:
      # Shut down the QEMU instance.
      api.python('stop qemu',
                 api.path['checkout'].join('build', 'run_fuchsia_qemu.py'),
                 args=['stop'])

  if is_win:
    api.step('compile with ninja x86', ['ninja', '-C', x86_path])
    api.step('compile with ninja x64', ['ninja', '-C', x64_path])
    run_tests(x86_path)
    run_tests(x64_path, env={'CRASHPAD_TEST_32_BIT_OUTPUT':x86_path})
  else:
    api.step('compile with ninja', ['ninja', '-C', path])
    run_tests(path)

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
            args=[api.path['checkout'].join(spec['isolate'][2:])] +
                 spec['args'])


def GenTests(api):
  # Only test a single clobber case.
  test = 'crashpad_mac_dbg'
  yield(api.test(test + '_clobber') +
        api.properties.generic(buildername=test, config='Debug', clobber=True))

  tests = [
      (test, 'mac', None),
      ('crashpad_try_mac_rel', 'mac', None),
      ('crashpad_try_win_dbg', 'win', None),
      ('crashpad_fuchsia_x64_dbg', 'fuchsia', 'x64'),
      ('crashpad_fuchsia_arm64_rel', 'fuchsia', 'arm64'),
  ]
  for t, os, cpu in tests:
    yield(api.test(t) +
          api.properties.generic(buildername=t,
                                 config='Debug' if '_dbg' in t else 'Release',
                                 target_os=os,
                                 target_cpu=cpu) +
          api.path.exists(api.path['checkout'].join(
              'build', 'swarming_test_spec.pyl')))
