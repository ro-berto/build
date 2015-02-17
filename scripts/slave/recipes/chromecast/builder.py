# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'path',
  'properties',
  'python',
  'step',
  'tryserver',
]

CAST_TESTS = [
    'base_unittests',
    'cacheinvalidation_unittests',
    'cast_media_unittests',
    'cast_shell_browser_test',
    'content_unittests',
    'crypto_unittests',
    'gpu_unittests',
    'ipc_tests',
    'jingle_unittests',
    'media_unittests',
    'net_unittests',
    'sandbox_linux_unittests',
    'sql_unittests',
    'sync_unit_tests',
    'ui_base_unittests',
    'url_unittests',
]

BUILDERS = {
  'cast_shell': {
    'configuration': 'Debug',
    'targets': ['cast_shell'],
    'tests': CAST_TESTS,
  },
  'cast_shell_apk': {
    'configuration': 'Release',
    'configure_droid': True,
    'gclient_apply_config': ['android'],
    'targets': ['cast_shell_apk'],
  },
}

def GenSteps(api):

  buildername = api.properties['buildername']
  bot_config = BUILDERS[buildername]
  build_configuration = bot_config.get('configuration', 'Debug')

  if bot_config.get('configure_droid', False):
    api.chromium_android.set_config(
        'base_config',
        REPO_URL='https://chromium.googlesource.com/chromium/src.git',
        INTERNAL=False,
        REPO_NAME='src',
        BUILD_CONFIG=build_configuration)
  else:
    api.chromium.set_config('chromium', BUILD_CONFIG=build_configuration)

  api.gclient.set_config('chromium')

  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  api.bot_update.ensure_checkout(force=True)
  api.tryserver.maybe_apply_issue()

  api.chromium.c.gyp_env.GYP_DEFINES['chromecast'] = 1
  api.chromium.c.gyp_env.GYP_DEFINES['component'] = 'static_library'

  api.chromium.runhooks()
  api.chromium.compile(bot_config.get('targets'), name='compile cast_shell')

  tests = bot_config.get('tests', [])
  if len(tests) > 0:
    api.chromium.compile(tests, name='compile tests')

    with api.step.defer_results():
      for x in tests:
        api.chromium.runtest(x, xvfb=False)

def GenTests(api):
  for buildername in BUILDERS:
    yield (
      api.test('basic_%s' % buildername) +
      api.properties.tryserver(
          buildername=buildername,
          mastername='tryserver.chromium.linux'))
