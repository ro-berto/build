# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot recipe definition for the various Crashpad continuous builders.
"""

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


def RunSteps(api):
  """Generates the sequence of steps that will be run by the slave."""
  api.gclient.set_config('crashpad')
  api.bot_update.ensure_checkout()

  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmtree('out', api.path['checkout'].join('out'))

  buildername = api.properties['buildername']
  env = {}
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
  dirname = 'Debug' if '_dbg' in buildername else 'Release'
  path = api.path['checkout'].join('out', dirname)
  api.step('compile with ninja', ['ninja', '-C', path])

  if '_x64' in buildername:
    # Note that we modify the dirname on x64 because we want to handle variants
    # a) and b) above.
    dirname += '_x64'
    path = api.path['checkout'].join('out', dirname)
    api.step('compile with ninja', ['ninja', '-C', path])

  api.python('run tests',
             api.path['checkout'].join('build', 'run_tests.py'),
             args=[path],
             timeout=5*60)


def GenTests(api):
  # Only test a single clobber case.
  test = 'crashpad_mac_dbg'
  yield(api.test(test + '_clobber') +
        api.properties.generic(buildername=test, clobber=True))

  # Every other test is a trybot.
  tests = [
      test,
      'crashpad_try_mac_rel',
      'crashpad_try_win_x64_dbg',
      'crashpad_win_x64_rel',
      'crashpad_win_x86_dbg',
      'crashpad_try_win_x86_rel',
      'crashpad_try_win_x86_wow64_dbg',
      'crashpad_win_x86_wow64_rel',
  ]
  for t in tests:
    yield(api.test(t) + api.properties.generic(buildername=t))

