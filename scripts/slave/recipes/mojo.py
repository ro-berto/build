# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
  'tryserver',
]


def _CheckoutSteps(api, buildername):
  # Checkout mojo and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('mojo')
  if 'Android' in buildername:
    api.gclient.apply_config('android')
  if api.tryserver.is_tryserver:
    api.step.auto_resolve_conflicts = True
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()


def _BuildSteps(api, buildername, build_type):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.py')
  args = []
  if 'Android' in buildername:
    args += ['--android']
  elif 'ChromeOS' in buildername:
    args += ['--chromeos']

  goma_dir = ''
  if 'Win' not in buildername:
    # Disable Goma on Windows as it makes the build much slower (> 1 hour vs
    # 15 minutes). Try renabling once we have trybots and the cache would be
    # warm.
    goma_dir = api.path['build'].join('goma')
  env = {}
  if goma_dir:
    env['GOMA_DIR'] = goma_dir
  api.python('mojob gn',
             mojob_path,
             args=['gn', build_type] + args,
             cwd=api.path['checkout'],
             env=env)
  api.python('mojob build',
             mojob_path,
             args=['build', build_type] + args,
             env=env)

def _RunTests(api, build_type):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.py')
  api.python('mojob test', mojob_path, args=[
    'test', build_type,
    '--master-name', api.properties.get('mastername'),
    '--builder-name', api.properties.get('buildername'),
    '--build-number', api.properties.get('buildnumber'),
    '--test-results-server', api.properties.get('test_results_server',
        'test-results.appspot.com'),
  ])

def _RunPerfTests(api, build_type):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.py')
  api.python('mojob perftest', mojob_path, args=['perftest', build_type])

def _UploadShell(api):
  upload_path = api.path['checkout'].join('mojo', 'tools',
      'upload_shell_binary.py')
  api.python('upload shell binary', upload_path)

def GenSteps(api):
  buildername = api.properties.get('buildername')
  _CheckoutSteps(api, buildername)
  build_type = '--debug' if 'dbg' in buildername else '--release'
  _BuildSteps(api, buildername, build_type)
  if 'Perf' in buildername:
    _RunPerfTests(api, build_type)
    return
  is_linux = 'Linux' in buildername
  is_win = 'Win' in buildername
  if not is_linux and not is_win:
    return
  _RunTests(api, build_type)
  is_try = api.tryserver.is_tryserver
  if is_linux and build_type == '--release' and not is_try:
    _UploadShell(api)

def GenTests(api):
  tests = [['mojo_linux', 'Mojo Linux'],
           ['mojo_linux_dbg', 'Mojo Linux (dbg)'],
           ['mojo_android_dbg', 'Mojo Android (dbg)'],
           ['mojo_chromeos_dbg', 'Mojo ChromeOS (dbg)'],
           ['mojo_win_dbg', 'Mojo Win (dbg)'],
           ['mojo_linux_perf', 'Mojo Linux Perf']]
  for t in tests:
    yield(api.test(t[0]) + api.properties.generic(buildername=t[1]))
  yield(api.test('mojo_linux_try') +
      api.properties.tryserver(buildername="Mojo Linux Try"))
