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
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.py')
  args = []
  if 'Android' in buildername:
    args += ['--android']
  elif 'ChromeOS' in buildername:
    args += ['--chromeos']
  api.python('mojob gn',
             mojob_path,
             args=['gn', build_type] + args,
             cwd=api.path['checkout'])
  if 'Win' in buildername:
    return  # until http://crbug.com/402648 is fixed.
  api.python('mojob build', mojob_path, args=['build', build_type] + args)

def _RunTests(api, build_type):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.py')
  api.python('mojob test', mojob_path, args=['test', build_type])

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
           ['mojo_chromeos_dbg', 'Mojo ChromeOS (dbg)'],
           ['mojo_win_dbg', 'Mojo Win (dbg)']]
  for t in tests:
    yield(api.test(t[0]) + api.properties.generic(buildername=t[1]))
