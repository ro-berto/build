# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_checkout',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'ios',
  'recipe_engine/buildbucket',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'webrtc'
]


_WEBRTC_CONFIGS = {
  'luci_webrtc_ci_ios32_debug': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'ios_enable_code_signing=false',
      'is_debug=true',
      'target_cpu="arm"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Debug',
    'sdk': 'iphoneos10.3',
    'tests': [
    ]
  },

  'luci_webrtc_ci_ios32_release': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'dcheck_always_on=true',
      'ios_enable_code_signing=false',
      'is_debug=false',
      'target_cpu="arm"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Release',
    'sdk': 'iphoneos10.3',
    'tests': [
    ]
  },

  'luci_webrtc_ci_ios64_debug': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'ios_enable_code_signing=false',
      'is_debug=true',
      'target_cpu="arm64"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Debug',
    'sdk': 'iphoneos10.3',
    'tests': [
    ]
  },

  'luci_webrtc_ci_ios64_release': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'dcheck_always_on=true',
      'ios_enable_code_signing=false',
      'is_debug=false',
      'target_cpu="arm64"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Release',
    'sdk': 'iphoneos10.3',
    'tests': [
    ]
  },

  'luci_webrtc_ci_ios64_sim_debug_ios_9_0': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'is_component_build=false',
      'is_debug=true',
      'target_cpu="x64"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Debug',
    'sdk': 'iphonesimulator9.3',
    'tests': [
      {
        'include': 'common_tests.json',
        'device type': 'iPhone 6s',
        'os': '9.3',
        'host os': 'Mac-10.13',
        'pool': 'Chrome',
        'priority': 30
      }
    ]
  },

  'luci_webrtc_ci_ios64_sim_debug_ios_10_0': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'is_component_build=false',
      'is_debug=true',
      'target_cpu="x64"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Debug',
    'sdk': 'iphonesimulator10.3',
    'tests': [
      {
        'include': 'common_tests.json',
        'device type': 'iPhone 6s',
        'os': '10.3',
        'host os': 'Mac-10.13',
        'pool': 'Chrome',
        'priority': 30
      }
    ]
  },

  'luci_webrtc_try_ios_compile_arm_dbg': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'ios_enable_code_signing=false',
      'is_debug=true',
      'target_cpu="arm"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Debug',
    'sdk': 'iphoneos10.3',
    'tests': [
    ]
  },

  'luci_webrtc_try_ios_compile_arm_rel': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'dcheck_always_on=true',
      'ios_enable_code_signing=false',
      'is_debug=false',
      'target_cpu="arm"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Release',
    'sdk': 'iphoneos10.3',
    'tests': [
    ]
  },

  'luci_webrtc_try_ios_compile_arm64_dbg': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'ios_enable_code_signing=false',
      'is_debug=true',
      'target_cpu="arm64"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Debug',
    'sdk': 'iphoneos10.3',
    'tests': [
    ]
  },

  'luci_webrtc_try_ios_compile_arm64_rel': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'dcheck_always_on=true',
      'ios_enable_code_signing=false',
      'is_debug=false',
      'target_cpu="arm64"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Release',
    'sdk': 'iphoneos10.3',
    'tests': [
    ]
  },

  'luci_webrtc_try_ios_sim_x64_dbg_ios9': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'is_debug=true',
      'target_cpu="x64"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Debug',
    'sdk': 'iphonesimulator9.3',
    'tests': [
      {
        'include': 'common_tests.json',
        'device type': 'iPhone 6s',
        'os': '9.3',
        'host os': 'Mac-10.13',
        'pool': 'Chrome',
        'priority': 30
      }
    ]
  },

  'luci_webrtc_try_ios_sim_x64_dbg_ios10': {
    'xcode build version': '10l232m',
    'gn_args': [
      'goma_dir="$(goma_dir)"',
      'is_debug=true',
      'target_cpu="x64"',
      'target_os="ios"',
      'use_goma=true'
    ],
    'additional_compile_targets': [ 'all' ],
    'configuration': 'Debug',
    'sdk': 'iphonesimulator10.3',
    'tests': [
      {
        'include': 'common_tests.json',
        'device type': 'iPhone 6s',
        'os': '10.3',
        'host os': 'Mac-10.13',
        'pool': 'Chrome',
        'priority': 30
      }
    ]
  },
}

_WEBRTC_COMMON_TESTS = {
  'tests': [
    {
      'app': 'apprtcmobile_tests',
      'xctest': True
    },
    {
       'app': 'sdk_unittests',
       'xctest': True
    },
    {
       'app': 'sdk_framework_unittests',
       'xctest': True
    },
    {
      'app': 'audio_decoder_unittests'
    },
    {
      'app': 'common_audio_unittests'
    },
    {
      'app': 'common_video_unittests'
    },
    {
      'app': 'modules_tests'
    },
    {
      'app': 'modules_unittests'
    },
    {
      'app': 'rtc_media_unittests'
    },
    {
      'app': 'rtc_pc_unittests'
    },
    {
      'app': 'rtc_stats_unittests'
    },
    {
      'app': 'rtc_unittests'
    },
    {
      'app': 'system_wrappers_unittests'
    },
    {
      'app': 'test_support_unittests'
    },
    {
      'app': 'tools_unittests'
    },
    {
      'app': 'video_capture_tests'
    },
    {
      'app': 'video_engine_tests'
    },
    {
      'app': 'webrtc_nonparallel_tests'
    }
  ]
}


def RunSteps(api):
  api.gclient.set_config('webrtc_ios')
  api.webrtc.checkout()

  build_config_base_dir = api.path['checkout'].join(
      'tools_webrtc',
      'ios',
  )
  buildername = api.buildbucket.builder_name.replace(' ', '_')
  api.ios.read_build_config(build_config_base_dir=build_config_base_dir,
                            buildername=buildername)
  mb_path = api.path['checkout'].join('tools_webrtc', 'mb')
  api.ios.build(mb_path=mb_path)
  api.ios.test_swarming()


def GenTests(api):
  for name, config in sorted(_WEBRTC_CONFIGS.items()):
    properties = dict(
        buildername=name.split('_', 3)[-1],
        buildnumber='0',
        mastername='chromium.fake',
        bot_id='fake-vm',
        path_config='kitchen')
    if '_try_' in name:
      properties['gerrit_project'] = 'webrtc'
      properties = api.properties.tryserver(**properties)
    else:
      properties = api.properties(**properties)
    test = (
        api.test(name) +
        api.runtime(is_luci=True, is_experimental=False) +
        api.platform('mac', 64) +
        properties +
        api.ios.make_test_build_config(config) +
        api.step_data('bootstrap swarming.swarming.py --version',
                      stdout=api.raw_io.output_text('1.2.3'))
    )
    if '_sim_' in name:
      test += api.step_data('include common_tests.json',
                            api.json.output(_WEBRTC_COMMON_TESTS))
    yield test

