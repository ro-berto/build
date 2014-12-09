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
  'step',
]


def GenSteps(api):
  """Generates the sequence of steps that will be run by the slave."""
  api.gclient.set_config('crashpad')
  api.gclient.checkout()
  api.gclient.runhooks()

  buildername = api.properties['buildername']
  dirname = 'Debug' if '_dbg' in buildername else 'Release'
  path = api.path['checkout'].join('out', dirname)
  api.step('compile with ninja', ['ninja', '-C', path])


def GenTests(api):
  tests = [
      'crashpad_mac_dbg',
      'crashpad_mac_rel',
      'crashpad_win_dbg',
      'crashpad_win_rel',
  ]
  for t in tests:
    yield(api.test(t) + api.properties.generic(buildername=t))
