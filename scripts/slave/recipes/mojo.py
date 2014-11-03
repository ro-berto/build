# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


def _CheckoutSteps(api):
  # Checkout mojo and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('mojo')
  api.gclient.checkout()
  api.gclient.runhooks()


def _BuildSteps(api, buildername, build_type):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.sh')
  args = []
  if 'Android' in buildername:
    args += ['--android']
  elif 'ChromeOS' in buildername:
    args += ['--chromeos']
  api.step('mojob gn',
           [mojob_path] + args + [build_type, 'gn'],
           cwd=api.path['checkout'])
  api.step('mojob build', [mojob_path] + args + [build_type, 'build'])

def _RunTests(api, build_type):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.sh')
  api.step('mojob test', [mojob_path, build_type, 'test'])

def _UploadShell(api):
  upload_path = api.path['checkout'].join('mojo', 'tools',
      'upload_shell_binary.py')
  api.python('upload shell binary', upload_path)

def GenSteps(api):
  _CheckoutSteps(api)
  buildername = api.properties.get('buildername')
  build_type = '--debug' if 'dbg' in buildername else '--release'
  _BuildSteps(api, buildername, build_type)
  if 'Linux' in buildername:
    _RunTests(api, build_type)
    if build_type == '--release':
      _UploadShell(api)

def GenTests(api):
  tests = [['mojo_linux', 'Mojo Linux'],
           ['mojo_linux_dbg', 'Mojo Linux (dbg)'],
           ['mojo_android_dbg', 'Mojo Android (dbg)'],
           ['mojo_chromeos_dbg', 'Mojo ChromeOS (dbg)']]
  for t in tests:
    yield(api.test(t[0]) + api.properties.generic(buildername=t[1]))
