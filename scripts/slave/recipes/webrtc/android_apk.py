# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'base_android',
  'chromium',
  'chromium_android',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step',
  'tryserver',
  'webrtc',
]



BUILDERS = {
  'tryserver.webrtc': {
    'builders': {
      'android_apk': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android_apk_rel': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
    },
  },
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, ('Unrecognized builder name %r for master %r.' %
                      (buildername, mastername))

  api.webrtc.set_config('webrtc_android_apk',
                        **bot_config.get('webrtc_config_kwargs', {}))
  if api.tryserver.is_tryserver:
    api.webrtc.apply_config('webrtc_android_apk_try_builder')

    # Replace src/third_party/webrtc with a WebRTC ToT checkout and force the
    # Chromium code to sync ToT.
    api.gclient.c.solutions[0].revision = 'HEAD'
    # TODO(kjellander): Switch to use the webrtc_revision gyp variable in DEPS
    # as soon we've switched over to use the trunk branch instead of the stable
    # branch (which is about to be retired).
    api.gclient.c.solutions[0].custom_deps['src/third_party/webrtc'] += (
        '@' + api.properties.get('revision'))

  api.step.auto_resolve_conflicts = True

  yield api.gclient.checkout()

  if api.tryserver.is_tryserver:
    yield api.webrtc.apply_svn_patch()
  yield api.base_android.envsetup()
  yield api.base_android.runhooks()
  yield api.chromium.cleanup_temp()
  yield api.base_android.compile()

  yield api.chromium_android.common_tests_setup_steps()

  for test in api.webrtc.ANDROID_APK_TESTS:
    yield api.base_android.test_runner(test)

  yield api.chromium_android.common_tests_final_steps()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config.get('parent_buildername') is None, (
            'Unexpected parent_buildername for builder %r on master %r.' %
                (buildername, mastername))

      webrtc_config_kwargs = bot_config.get('webrtc_config_kwargs', {})
      test = (
        api.test('%s_%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername))) +
        api.properties(mastername=mastername,
                       buildername=buildername,
                       parent_buildername=bot_config.get('parent_buildername'),
                       TARGET_PLATFORM=webrtc_config_kwargs['TARGET_PLATFORM'],
                       TARGET_ARCH=webrtc_config_kwargs['TARGET_ARCH'],
                       TARGET_BITS=webrtc_config_kwargs['TARGET_BITS'],
                       BUILD_CONFIG=webrtc_config_kwargs['BUILD_CONFIG']) +
        api.platform(bot_config['testing']['platform'],
                     webrtc_config_kwargs.get('TARGET_BITS', 64)) +
        api.step_data('envsetup',
            api.json.output({
                'FOO': 'bar',
                'GYP_DEFINES': 'my_new_gyp_def=aaa',
            }))
      )
      if mastername.startswith('tryserver'):
        test += api.properties(revision='12345',
                               patch_url='try_job_svn_patch')

      yield test

