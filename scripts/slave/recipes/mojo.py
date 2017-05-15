# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'adb',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'goma',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'recipe_engine/url',
  'depot_tools/tryserver',
]


def _CheckoutSteps(api, buildername):
  # Checkout mojo and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('mojo')
  if 'Android' in buildername:
    api.gclient.apply_config('android')
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()


def _BuildSteps(api, buildername, is_debug, is_official):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.py')
  args = []
  gn_args = []
  if 'Android' in buildername:
    args += ['--android']

  if 'ASan' in buildername:
    args += ['--asan']

  if api.tryserver.is_tryserver:
    args += ['--dcheck_always_on']

  env = {}

  goma_dir = ''
  if 'Win' not in buildername:
    # Disable Goma on Windows as it makes the build much slower (> 1 hour vs
    # 15 minutes). Try renabling once we have trybots and the cache would be
    # warm.
    goma_dir = api.goma.ensure_goma()
    env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = api.goma.service_account_json_path

  if is_debug:
    build_type = "--debug"
  elif is_official:
    build_type = "--official"
  else:
    build_type = "--release"

  if goma_dir:
    env['GOMA_DIR'] = goma_dir
  with api.context(env=env):
    with api.context(cwd=api.path['checkout']):
      api.python('mojob gn',
                 mojob_path,
                 args=['gn', build_type] + args + gn_args)
    api.python('mojob build',
               mojob_path,
               args=['build', build_type] + args)


def _DeviceCheckStep(api):
  known_devices_path = api.path.join(
      api.path.expanduser('~'), '.android', 'known_devices.json')
  # Device recovery.
  args = [
      '--known-devices-file', known_devices_path,
      '--adb-path', api.adb.adb_path(),
      '-v'
  ]
  api.step(
      'device_recovery',
      [api.path['checkout'].join('third_party', 'catapult', 'devil',
                                 'devil', 'android', 'tools',
                                 'device_recovery.py')] + args,
      infra_step=True)

  # Device provisioning.
  api.python(
      'provision_device',
      api.path['checkout'].join('third_party', 'catapult', 'devil',
                                'devil', 'android', 'tools',
                                'provision_devices.py'),
      infra_step=True)

  # Device Status.
  try:
    buildbot_file = '/home/chrome-bot/.adb_device_info'
    args = [
        '--json-output', api.json.output(),
        '--known-devices-file', known_devices_path,
        '--buildbot-path', buildbot_file,
        '-v', '--overwrite-known-devices-files',
    ]
    result = api.python(
        'device_status',
        api.path['checkout'].join('third_party', 'catapult', 'devil', 'devil',
                                  'android', 'tools', 'device_status.py'),
        args=args,
        infra_step=True)
    return result
  except api.step.InfraFailure as f:
    params = {
      'summary': ('Device Offline on %s %s' %
                   (api.properties['mastername'], api.properties['bot_id'])),
      'comment': ('Buildbot: %s\n(Please do not change any labels)' %
                   api.properties['buildername']),
      'labels': 'Restrict-View-Google,OS-Android,Infra-Client,Infra-Labs',
    }
    link = ('https://code.google.com/p/chromium/issues/entry?%s' %
      api.url.urlencode(params))
    f.result.presentation.links.update({
      'report a bug': link
    })
    raise



def _GetTestConfig(api):
  buildername = api.properties.get('buildername')

  test_config = {}
  if 'Android' in buildername:
    test_config['target_os'] = 'android'
  elif 'Linux' in buildername:
    test_config['target_os'] = 'linux'
  elif 'Win' in buildername:
    test_config['target_os'] = 'windows'
  else:
    raise NotImplementedError('Unknown platform')  # pragma: no cover

  test_config['is_debug'] = 'dbg' in buildername
  if 'Official' in buildername:
    # This is not reached, as we only have Android official builds.
    raise NotImplementedError(
        'Testing not supported for official builds') # pragma: no cover

  if 'Perf' in buildername:
    test_config['test_types'] = ['perf']
  else:
    test_config['test_types'] = ['default']

  if 'ASan' in buildername:
    test_config['sanitizer'] = 'asan'

  test_config['master_name'] = api.properties.get('mastername')
  test_config['builder_name'] = api.properties.get('buildername')
  test_config['build_number'] = api.properties.get('buildnumber')
  test_config['test_results_server'] = api.properties.get(
      'test_results_server', 'test-results.appspot.com')

  test_config['dcheck_always_on'] = api.tryserver.is_tryserver

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

  with api.step.defer_results():
    for entry in test_list:
      name = str(entry['name'])  # api.step() wants a non-Unicode string.
      command = entry['command']
      with api.context(cwd=api.path['checkout']):
        api.step(name, command)


def _UploadShellAndApps(api, buildername):
  upload_path = api.path['checkout'].join('mojo', 'tools', 'upload_binaries.py')
  is_android = 'Android' in buildername
  args = []
  if is_android:
    args.append('--android')
    if 'Official' in buildername:
      args.append('--official')
  api.python('upload shell and app binaries', upload_path, args)


def RunSteps(api):
  buildername = api.properties.get('buildername')
  _CheckoutSteps(api, buildername)

  is_debug = 'dbg' in buildername
  is_official = 'Official' in buildername

  _BuildSteps(api, buildername, is_debug, is_official)

  is_linux = 'Linux' in buildername
  is_win = 'Win' in buildername
  is_android = 'Android' in buildername
  is_tester = 'Tests' in buildername
  is_try = api.tryserver.is_tryserver
  is_asan = 'ASan' in buildername
  is_perf = 'Perf' in buildername

  if is_android and is_tester:
    _DeviceCheckStep(api)

  upload_binaries = ((is_linux or is_android)
      and not is_debug and not is_try and not is_perf and not is_asan)
  if not is_tester and not is_linux and not is_win:
    # TODO(blundell): Eliminate this special case
    # once there's an Android release tester bot.
    if upload_binaries and is_android:
      _UploadShellAndApps(api, buildername)
    return

  _TestSteps(api)

  # TODO(blundell): Remove the "and not is_android" once there's an
  # Android release tester bot and I've removed the logic uploading the
  # shell on Android above.
  if upload_binaries and not is_android:
    _UploadShellAndApps(api, buildername)

def GenTests(api):
  tests = [
      ['mojo_linux', 'Mojo Linux'],
      ['mojo_linux_dbg', 'Mojo Linux (dbg)'],
      ['mojo_linux_asan', 'Mojo Linux ASan'],
      ['mojo_linux_asan_dbg', 'Mojo Linux ASan (dbg)'],
      ['mojo_android_builder', 'Mojo Android Builder'],
      ['mojo_android_official', 'Mojo Android Official Builder'],
      ['mojo_android_dbg', 'Mojo Android (dbg)'],
      ['mojo_android_builder_tests_dbg', 'Mojo Android Builder Tests (dbg)'],
      ['mojo_win_dbg', 'Mojo Win (dbg)'],
      ['mojo_linux_perf', 'Mojo Linux Perf']
  ]
  for test_name, buildername in tests:
    test = api.test(test_name) + api.properties.generic(buildername=buildername)
    if 'Android' in buildername and 'Tests' in buildername:
      test += api.step_data("device_status", api.json.output([
          {
            "battery": {
                "status": "5",
                "scale": "100",
                "temperature": "249",
                "level": "100",
                "AC powered": "false",
                "health": "2",
                "voltage": "4286",
                "Wireless powered": "false",
                "USB powered": "true",
                "technology": "Li-ion",
                "present": "true"
            },
            "wifi_ip": "",
            "imei_slice": "Unknown",
            "ro.build.id": "LRX21O",
            "build_detail":
                "google/razor/flo:5.0/LRX21O/1570415:userdebug/dev-keys",
            "serial": "07a00ca4",
            "ro.build.product": "flo",
            "adb_status": "device",
            "blacklisted": False,
            "usb_status": True,
          },
          {
            "adb_status": "offline",
            "blacklisted": True,
            "serial": "03e0363a003c6ad4",
            "usb_status": False,
          },
          {
            "adb_status": "unauthorized",
            "blacklisted": True,
            "serial": "03e0363a003c6ad5",
            "usb_status": True,
          },
          {
            "adb_status": "device",
            "blacklisted": True,
            "serial": "03e0363a003c6ad6",
            "usb_status": True,
          },
          {}
        ]))
    yield test
  yield(api.test('mojo_linux_try') +
      api.properties.tryserver(buildername="Mojo Linux Try"))
  yield(api.test('mojo_android_builder_tests_dbg_fail_device_check') +
      api.properties.tryserver(buildername="Mojo Android Builder Tests (dbg)") +
      api.step_data("device_status", retcode=1))
