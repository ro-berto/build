# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'properties',
  'json',
  'path',
  'python',
]

BUILDERS = {
  'cronet_builder': {
    'run_tests': True,
  },
  'cronet_rel': {
    'run_tests': False,
  },
}

def GenSteps(api):
  droid = api.chromium_android

  buildername = api.properties['buildername']
  builder_config = BUILDERS.get(buildername, {})
  droid.set_config(buildername,
      REPO_NAME='src',
      REPO_URL='https://chromium.googlesource.com/chromium/src.git',
      INTERNAL=False)

  yield droid.init_and_sync()
  yield droid.envsetup()
  yield droid.clean_local_files()
  yield droid.runhooks()
  yield droid.compile()

  if builder_config['run_tests']:
    yield droid.device_status_check()
    install_cmd = api.path['checkout'].join('build',
                                            'android',
                                            'adb_install_apk.py')
    yield api.python('install CronetSample', install_cmd,
        args = ['--apk', 'CronetSample.apk'])
    test_cmd = api.path['checkout'].join('build',
                                         'android',
                                         'test_runner.py')
    yield api.python('test CronetSample', test_cmd,
        args = ['instrumentation', '--test-apk', 'CronetSampleTest'])
  yield droid.upload_build()
  yield droid.cleanup_build()

def GenTests(api):
  bot_ids = ['cronet_builder', 'cronet_rel']

  for bot_id in bot_ids:
    props = api.properties(
      buildername=bot_id,
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
    )
    yield api.test(bot_id) + props
