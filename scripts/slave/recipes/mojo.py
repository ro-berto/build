# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
]


def _CheckoutSteps(api):
  # Checkout mojo and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('mojo')
  api.gclient.checkout()
  api.gclient.runhooks()


def _BuildSteps(api, buildername):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.sh')
  args = []
  if 'Android' in buildername:
    args += ['--android']
  elif 'ChromeOS' in buildername:
    args += ['--chromeos']
  api.step('mojob gn',
           [mojob_path] + args + ['--debug', 'gn'],
           cwd=api.path['checkout'])
  api.step('mojob build', [mojob_path] + args + ['--debug', 'build'])

def _RunTests(api):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.sh')
  api.step('mojob test', [mojob_path, '--debug', 'test'])

def GenSteps(api):
  _CheckoutSteps(api)
  buildername = api.properties.get('buildername')
  _BuildSteps(api, buildername)
  if 'Linux' in buildername:
    _RunTests(api)

def GenTests(api):
  tests = [['mojo_linux', 'Mojo Linux (dbg)'],
           ['mojo_android', 'Mojo Android (dbg)'],
           ['mojo_chromeos', 'Mojo ChromeOS (dbg)']]
  for t in tests:
    yield(api.test(t[0]) + api.properties.generic(buildername=t[1]))
