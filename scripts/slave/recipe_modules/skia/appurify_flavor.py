# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import android_devices
import copy
import default_flavor


"""Appurify flavor utils, used for building and running tests in Appurify."""


class AppurifyFlavorUtils(default_flavor.DefaultFlavorUtils):
  def __init__(self, skia_api):
    super(AppurifyFlavorUtils, self).__init__(skia_api)
    self.device = self._skia_api.builder_spec['device_cfg']
    slave_info = android_devices.SLAVE_INFO.get(
        self._skia_api.slave_name,
        android_devices.SLAVE_INFO['default'])
    self.android_tools = self._skia_api.m.path['slave_build'].join(
        'skia', 'platform_tools', 'android')
    self.android_bin = self.android_tools.join('bin')
    self.apk_dir = self.android_tools.join('apps', 'visualbench', 'build',
                                           'outputs', 'apk')
    self._android_sdk_root = slave_info.android_sdk_root
    self._default_env = {'ANDROID_SDK_ROOT': self._android_sdk_root,
                         'ANDROID_HOME': self._android_sdk_root,
                         'SKIA_ANDROID_VERBOSE_SETUP': 1}

  def step(self, name, cmd, env=None, **kwargs):
    # Extract the json file name from the command; ignore the rest.
    json_file = None
    for i, arg in enumerate(cmd):
      if str(arg) == '--outResultsFile':
        break

    if len(cmd) > i + 1:
      json_file = cmd[i + 1]

    main_apk = self.apk_dir.join('visualbench-arm-release.apk')
    test_apk = self.apk_dir.join(
        'visualbench-arm-debug-androidTest-unaligned.apk')
    cmd = ['python', self._skia_api.resource('appurify_wrapper.py'),
      '--test-type', 'robotium',
      '--device-type-id', '536',
      '--config-src', self.android_tools.join('apps', 'robotium.cfg'),
      '--app-src', main_apk,
      '--test-src', test_apk,
      '--result-dir', self._skia_api.device_dirs.tmp_dir,
    ]
    env = dict(env or {})
    env.update(self._default_env)
    env.update({
      'APPURIFY_API_HOST': '172.22.21.180',
      'APPURIFY_API_PORT': '80',
      'APPURIFY_API_PROTO': 'http',
    })

    result = self._skia_api.run(self._skia_api.m.step, name=name, cmd=cmd,
                                env=env, **kwargs)

    if json_file:
      # Unzip the results.
      cmd = ['unzip', '-o', self._skia_api.tmp_dir.join('results.zip'),
             '-d', self._skia_api.tmp_dir]
      self._skia_api.run(self._skia_api.m.step, name='unzip_results', cmd=cmd)

      # Copy the results file to the desired location.
      self._skia_api.m.file.copy(
          'copy_results',
          self._skia_api.tmp_dir.join(
              'appurify_results', 'artifacts_directory',
              'sdcard-skia_results', 'visualbench.json'),
          self._skia_api.perf_data_dir.join(json_file))
    return result

  def compile(self, target):
    """Build the given target."""
    env = dict(self._default_env)
    ccache = self._skia_api.ccache()
    if ccache:
      env['ANDROID_MAKE_CCACHE'] = ccache

    cmd = [self.android_bin.join('android_ninja'), target, '-d', self.device]
    self._skia_api.run(self._skia_api.m.step, 'build %s' % target, cmd=cmd,
                       env=env, cwd=self._skia_api.m.path['checkout'])
