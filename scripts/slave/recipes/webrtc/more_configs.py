# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze


DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'recipe_engine/step',
  'webrtc',
]

RECIPE_CONFIGS = freeze({
  'webrtc_minimal': {
    'chromium_config': 'webrtc_minimal',
    'gclient_config': 'webrtc',
  },
})

BUILDERS = freeze({
  'client.webrtc': {
    'builders': {
      'Linux (more configs)': {
        'recipe_config': 'webrtc_minimal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'linux_more_configs': {
        'recipe_config': 'webrtc_minimal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
})


def BuildSteps(api, gn_arg=None, name=None):
  if gn_arg:
    assert isinstance(gn_arg, basestring)
  api.chromium.c.gn_args = [gn_arg] if gn_arg else []
  api.chromium.run_gn(use_goma=True)
  api.step.active_result.presentation.step_text = 'gn (%s)' % (name or gn_arg)
  api.chromium.compile()


def RunSteps(api):
  webrtc = api.webrtc
  webrtc.apply_bot_config(BUILDERS, RECIPE_CONFIGS)

  api.webrtc.checkout()
  api.chromium.ensure_goma()
  api.chromium.runhooks()

  BuildSteps(api, name='minimal')
  BuildSteps(api, gn_arg='rtc_enable_intelligibility_enhancer=true')


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test
