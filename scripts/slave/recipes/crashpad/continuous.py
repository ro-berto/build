# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot recipe definition for the various Crashpad continuous builders.
"""

DEPS = [
  'file',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


def RunSteps(api):
  """Generates the sequence of steps that will be run by the slave."""
  api.gclient.set_config('crashpad')
  api.gclient.checkout()

  if 'clobber' in api.properties:
    api.file.rmtree('out', api.path['checkout'].join('out'))

  buildername = api.properties['buildername']
  env = {}
  if '_x86' in buildername:
    env = {'GYP_DEFINES': 'target_arch=ia32'}
  api.gclient.runhooks(env=env)

  dirname = 'Debug' if '_dbg' in buildername else 'Release'
  path = api.path['checkout'].join('out', dirname)
  api.step('compile with ninja', ['ninja', '-C', path])
  api.python('run tests',
             api.path['checkout'].join('build', 'run_tests.py'),
             args=[dirname])


def GenTests(api):
  tests = [
      'crashpad_mac_dbg',
      'crashpad_mac_rel',
      'crashpad_win_dbg',
      'crashpad_win_rel',
      'crashpad_win_x86_dbg',
      'crashpad_win_x86_rel',
  ]
  for t in tests:
    yield(api.test(t) + api.properties.generic(buildername=t))
    yield(api.test(t + '_clobber') +
          api.properties.generic(buildername=t, clobber=True))
