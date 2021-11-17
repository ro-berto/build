# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import functools

from recipe_engine import post_process
from recipe_engine.engine_types import freeze
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb


PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'webrtc',
]

RECIPE_CONFIGS = freeze({
  'webrtc': {
    'chromium_config': 'webrtc_default',
    'gclient_config': 'webrtc',
    'test_suite': 'more_configs',
  },
  'webrtc_android': {
    'chromium_config': 'android',
    'gclient_config': 'webrtc',
    'gclient_apply_config': ['android'],
    'test_suite': 'more_configs',
  },
})

BUILDERS = freeze({
    'luci.webrtc.ci': {
        'settings': {
            'builder_group': 'client.webrtc',
        },
        'builders': {
            'Linux (more configs)': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-16.04',
                    'cpu': 'x86-64',
                },
            },
            'Android32 (more configs)': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Win (more configs)': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-7-SP1',
                    'cpu': 'x86-64',
                },
            },
        },
    },
    'luci.webrtc.try': {
        'settings': {
            'builder_group': 'tryserver.webrtc',
        },
        'builders': {
            'linux_more_configs': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-16.04',
                    'cpu': 'x86-64',
                },
            },
            'android_arm_more_configs': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'win_x86_more_configs': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-7-SP1',
                    'cpu': 'x86-64',
                },
            },
        },
    },
})


def RunSteps(api):
  webrtc = api.webrtc
  webrtc.apply_bot_config(BUILDERS, RECIPE_CONFIGS)

  webrtc.checkout()

  webrtc.configure_swarming()

  api.chromium.ensure_goma()
  api.chromium.runhooks()

  phases = ['bwe_test_logging',
            'dummy_audio_file_devices_no_protobuf',
            'rtti_no_sctp']
  for phase in phases:
    if not webrtc.is_compile_needed(phase=phase):
      step_result = api.step('No further steps are necessary.', cmd=None)
      step_result.presentation.status = api.step.SUCCESS
      return
    webrtc.configure_isolate(phase)
    webrtc.run_mb(phase)
    raw_result = webrtc.compile(phase)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result
    webrtc.isolate()

    if webrtc.bot.should_test:
      webrtc.runtests(phase)


def GenTests(api):
  builders = BUILDERS
  recipe_configs = RECIPE_CONFIGS
  generate_builder = functools.partial(api.webrtc.generate_builder, builders,
                                       recipe_configs)
  phases = [
      'bwe_test_logging', 'dummy_audio_file_devices_no_protobuf', 'rtti_no_sctp'
  ]

  for bucketname in builders.keys():
    group_config = builders[bucketname]
    for buildername in group_config['builders'].keys():
      yield generate_builder(
          bucketname, buildername, revision='a' * 40, phases=phases)

  yield (generate_builder(
      'luci.webrtc.ci',
      'Linux (more configs)',
      revision='b' * 40,
      suffix='_fail_compile',
      fail_compile=True,
      phases=phases) + api.post_process(post_process.StatusFailure) +
         api.post_process(post_process.DropExpectation))

  gn_analyze_no_deps_output = {'status': ['No dependency']}
  yield generate_builder(
      'luci.webrtc.try',
      'linux_more_configs',
      revision='a' * 40,
      suffix='_gn_analyze_no_dependency',
      gn_analyze_output=gn_analyze_no_deps_output)
