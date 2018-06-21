# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot recipe definition for the various Crashpad continuous builders.
"""

import ast
from recipe_engine.recipe_api import Property

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

PROPERTIES = {
  'buildername': Property(kind=str, help='The builder name', default=None),
  'config': Property(kind=str, help='Debug or Release', default='Debug'),
  'target_os':
    Property(kind=str, help='win, mac, linux, or fuchsia', default=None),
  'target_cpu': Property(kind=str, help='x64, arm64, or ""', default=''),
}

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

def RunSteps(api, buildername, config, target_os, target_cpu):
  """Generates the sequence of steps that will be run by the slave."""
  api.gclient.set_config('crashpad')

  env = {}

  is_fuchsia = is_linux = is_mac = is_win = False
  if target_os == 'fuchsia':
    is_fuchsia = True
  elif target_os == 'linux':
    is_linux = True
  elif target_os == 'mac':
    is_mac = True
  elif target_os == 'win':
    is_win = True

  assert is_fuchsia or is_linux or is_mac or is_win

  api.gclient.c.target_os = {target_os}

  is_debug = config == 'Debug'

  if is_linux:
    # The Linux build uses the system compiler by default, but bots do not have
    # a clang installed by default, so use a local copy. Setting this variable
    # causes DEPS to download a clang cipd package in runhooks. See also the
    # setting of clang_path below.
    api.gclient.c.solutions[0].custom_vars['pull_linux_clang'] = True

  if is_win:
    # Setting this variable causes DEPS to download the Windows SDK and
    # toolchain in runhooks. See also the setting of win_toolchain_path below.
    api.gclient.c.solutions[0].custom_vars['pull_win_toolchain'] = True

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
    if target_cpu is "":
      target_cpu = 'x64'
    args = 'target_os="' + target_os + '" target_cpu="' + target_cpu + '"' + \
           ' is_debug=' + ('true' if is_debug else 'false')
    if is_linux:
      # Point at the local copy of clang and a sysroot that were downloaded by
      # gclient runhooks.
      args += ' clang_path="//third_party/linux/clang/linux-amd64"'
      args += ' target_sysroot="//third_party/linux/sysroot"'

      # The 14.04 systems do not include a compatible libstdc++ that can deal
      # with -std=c++14, so force static linkage of libstdc++ from the sysroot.
      args += ' link_libstdcpp_statically = true'
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
    args = 'target_os="win" is_debug=' + ('true' if is_debug else 'false') + \
           ' win_toolchain_path="//third_party/win/toolchain"'
    with api.context(cwd=api.path['checkout']):
      api.step('generate build files x86',
               ['gn', 'gen', x86_path, '--args=' + args + ' target_cpu="x86"'])
      api.step('generate build files x64',
               ['gn', 'gen', x64_path, '--args=' + args + ' target_cpu="x64"'])
  else:
    assert is_mac
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
        api.properties.generic(buildername=test,
                               target_os='mac',
                               config='Debug',
                               clobber=True))

  tests = [
      (test, 'mac', ''),
      ('crashpad_try_mac_rel', 'mac', ''),
      ('crashpad_try_win_dbg', 'win', ''),
      ('crashpad_linux_debug', 'linux', ''),
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
