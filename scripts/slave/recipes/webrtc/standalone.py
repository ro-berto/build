# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building and running tests for WebRTC stand-alone.

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'tryserver',
  'webrtc',
]

class WebRTCNormalTests(object):
  @staticmethod
  def run(api):
    c = api.chromium
    steps = []
    for test in api.webrtc.NORMAL_TESTS:
      steps.append(c.runtest(test))

    if api.platform.is_mac and api.platform.bits == 64:
      test = api.path.join('libjingle_peerconnection_objc_test.app', 'Contents',
                           'MacOS', 'libjingle_peerconnection_objc_test')
      steps.append(c.runtest(test, name='libjingle_peerconnection_objc_test'))
    return steps


class WebRTCBaremetalTests(object):
  @staticmethod
  def run(api):
    """Adds baremetal tests, which are different depending on the platform."""
    c = api.chromium
    path = api.path
    steps = []

    if api.platform.is_win or api.platform.is_mac:
      steps.append(c.runtest('audio_device_tests'))
    elif api.platform.is_linux:
      steps.append(c.runtest(
          'audioproc', name='audioproc_perf',
          args=['-aecm', '-ns', '-agc', '--fixed_digital', '--perf', '-pb',
                path['checkout'].join('resources', 'audioproc.aecdump')]))
      steps.append(c.runtest(
          'iSACFixtest', name='isac_fixed_perf',
          args=['32000', path['checkout'].join('resources',
                                               'speech_and_misc_wb.pcm'),
                'isac_speech_and_misc_wb.pcm']))
      steps.append(c.runtest(
          'libjingle_peerconnection_java_unittest',
          env={'LD_PRELOAD': '/usr/lib/x86_64-linux-gnu/libpulse.so.0'}))

    steps.append(c.runtest(
        'vie_auto_test',
        args=['--automated',
              '--capture_test_ensure_resolution_alignment_in_capture_device='
              'false']))
    steps.append(c.runtest('voe_auto_test', args=['--automated']))
    steps.append(c.runtest('video_capture_tests'))
    steps.append(c.runtest('webrtc_perf_tests'))
    return steps


BUILDERS = {
  # TODO(kjellander): Deal with the massive code duplication below.
  'client.webrtc': {
    'builders': {
      'Win32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win32 Release [large tests]': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Mac32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac Asan': {
        'recipe_config': 'webrtc_asan',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac32 Release [large tests]': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Linux32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Asan': {
        'recipe_config': 'webrtc_asan',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Release [large tests]': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Android': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android (dbg)': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Clang': {
        'recipe_config': 'webrtc_android_clang',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'win': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'win_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'win_x64_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'win_baremetal': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'mac': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_x64_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_asan': {
        'recipe_config': 'webrtc_asan',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_baremetal': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'linux': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_asan': {
        'recipe_config': 'webrtc_asan',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_baremetal': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'android': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'android_rel': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'android_clang': {
        'recipe_config': 'webrtc_android_clang',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
}

RECIPE_CONFIGS = {
  'webrtc': {
    'webrtc_config': 'webrtc',
  },
  'webrtc_asan': {
    'webrtc_config': 'webrtc_asan',
  },
  'webrtc_android': {
    'webrtc_config': 'webrtc_android',
  },
  'webrtc_android_clang': {
    'webrtc_config': 'webrtc_android_clang',
  },
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  assert recipe_config_name, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.webrtc.set_config(recipe_config['webrtc_config'],
                        **bot_config.get('webrtc_config_kwargs', {}))

  if api.tryserver.is_tryserver:
    api.chromium.apply_config('trybot_flavor')

  yield api.gclient.checkout()
  steps = [api.chromium.runhooks()]
  if api.tryserver.is_tryserver:
    steps.append(api.webrtc.apply_svn_patch())

  steps.append(api.chromium.compile())
  steps.extend([t.run(api) for t in bot_config.get('tests', [])])
  yield steps


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config.get('parent_buildername') is None, (
            'Unexpected parent_buildername for builder %r on master %r.' %
                (buildername, mastername))

      # Trybots get these properties set.
      revision = None
      patch_url = None
      if mastername.startswith('tryserver'):
        revision = '12345'
        patch_url = 'try_job_svn_patch'

      webrtc_config_kwargs = bot_config.get('webrtc_config_kwargs', {})
      yield (
        api.test('%s_%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername))) +
        api.properties(mastername=mastername,
                       buildername=buildername,
                       slavename='slavename',
                       revision=revision,
                       patch_url=patch_url) +
        api.platform(bot_config['testing']['platform'],
                     webrtc_config_kwargs.get('TARGET_BITS', 64))
      )
