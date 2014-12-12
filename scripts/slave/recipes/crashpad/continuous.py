# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot recipe definition for the various Crashpad continuous builders.
"""

DEPS = [
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


def GenSteps(api):
  """Generates the sequence of steps that will be run by the slave."""
  api.gclient.set_config('crashpad')
  api.gclient.checkout()

  if 'clobber' in api.properties:
    api.path.rmtree('out', api.path['slave_build'].join('out'))

  api.gclient.runhooks()

  buildername = api.properties['buildername']
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
  ]
  for t in tests:
    yield(api.test(t) + api.properties.generic(buildername=t))
    yield(api.test(t + '_clobber') +
          api.properties.generic(buildername=t, clobber=True))
