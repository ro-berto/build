# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'json',
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
  if 'NaCl' in buildername:
    api.gclient.c.solutions[0].deps_file = 'DEPS.nacl'
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

  if 'NaCl' in buildername:
    args += ['--nacl']

  if 'ASan' in buildername:
    args += ['--asan']

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


def _GetTestConfig(api):
  buildername = api.properties.get('buildername')

  test_config = {}
  if 'Android' in buildername:
    test_config['target_os'] = 'android'
  elif 'ChromeOS' in buildername:
    test_config['target_os'] = 'chromeos'  # pragma: no cover
  elif 'Linux' in buildername:
    test_config['target_os'] = 'linux'
  elif 'Win' in buildername:
    test_config['target_os'] = 'windows'
  else:
    raise NotImplementedError('Unknown platform')  # pragma: no cover

  test_config['is_debug'] = 'dbg' in buildername

  if 'Perf' in buildername:
    test_config['test_types'] = ['perf']
  elif 'NaCl' in buildername:
    test_config['test_types'] = ['default', 'nacl']
  else:
    test_config['test_types'] = ['default']

  if 'ASan' in buildername:
    test_config['sanitizer'] = 'asan'

  test_config['master_name'] = api.properties.get('mastername')
  test_config['builder_name'] = api.properties.get('buildername')
  test_config['build_number'] = api.properties.get('buildnumber')
  test_config['test_results_server'] = api.properties.get(
      'test_results_server', 'test-results.appspot.com')

  return test_config


def _TestSteps(api):
  get_test_list_path = api.path['checkout'].join('mojo', 'tools',
                                                 'get_test_list.py')
  test_config = _GetTestConfig(api)
  test_out = [{'name': u'Hello', 'command': ['world']}]
  result = api.python('get_test_list', get_test_list_path,
                      args=[api.json.input(test_config), api.json.output()],
                      step_test_data=lambda: api.json.test_api.output(test_out))
  test_list = result.json.output

  for entry in test_list:
    try:
      name = str(entry['name'])  # api.step() wants a non-Unicode string.
      command = entry['command']
      api.step(name, command, cwd=api.path['checkout'])
    except api.step.StepFailure:  # pragma: no cover
      pass


def _UploadShell(api, buildername):
  upload_path = api.path['checkout'].join('mojo', 'tools',
      'upload_shell_binary.py')
  is_android = 'Android' in buildername
  args = ''
  if is_android:
    args = '--android'
  api.python('upload shell binary', upload_path, args)


def GenSteps(api):
  buildername = api.properties.get('buildername')
  _CheckoutSteps(api, buildername)
  build_type = '--debug' if 'dbg' in buildername else '--release'
  _BuildSteps(api, buildername, build_type)

  is_linux = 'Linux' in buildername
  is_win = 'Win' in buildername
  is_android = 'Android' in buildername
  is_tester = 'Tests' in buildername
  is_try = api.tryserver.is_tryserver
  is_asan = 'ASan' in buildername
  is_perf = 'Perf' in buildername
  is_nacl = 'NaCl' in buildername
  upload_shell = ((is_linux or is_android) and build_type == '--release'
      and not is_try and not is_perf and not is_asan and not is_nacl)
  if not is_tester and not is_linux and not is_win:
    # TODO(blundell): Eliminate this special case
    # once there's an Android release tester bot.
    if upload_shell and is_android:
      _UploadShell(api, buildername)
    return

  _TestSteps(api)

  # TODO(blundell): Remove the "and not is_android" once there's an
  # Android release tester bot and I've removed the logic uploading the
  # shell on Android above.
  if upload_shell and not is_android:
    _UploadShell(api, buildername)

def GenTests(api):
  tests = [
      ['mojo_linux', 'Mojo Linux'],
      ['mojo_linux_dbg', 'Mojo Linux (dbg)'],
      ['mojo_linux_asan', 'Mojo Linux ASan'],
      ['mojo_linux_asan_dbg', 'Mojo Linux ASan (dbg)'],
      ['mojo_linux_nacl', 'Mojo Linux NaCl'],
      ['mojo_linux_nacl_dbg', 'Mojo Linux NaCl (dbg)'],
      ['mojo_android_builder', 'Mojo Android Builder'],
      ['mojo_android_dbg', 'Mojo Android (dbg)'],
      ['mojo_android_builder_tests_dbg', 'Mojo Android Builder Tests (dbg)'],
      ['mojo_chromeos_dbg', 'Mojo ChromeOS (dbg)'],
      ['mojo_win_dbg', 'Mojo Win (dbg)'],
      ['mojo_linux_perf', 'Mojo Linux Perf']
  ]
  for t in tests:
    yield(api.test(t[0]) + api.properties.generic(buildername=t[1]))
  yield(api.test('mojo_linux_try') +
      api.properties.tryserver(buildername="Mojo Linux Try"))
