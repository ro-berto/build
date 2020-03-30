# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

COMPILE_TARGETS = [
  'chrome/browser/media/router',
  'chrome/browser/media/router:openscreen_unittests',
  'chrome/browser/media/router:unittests',
  'components/cast_certificate',
  'components/cast_certificate:unit_tests',
  'components/cast_channel',
  'components/cast_channel:unit_tests',
  'components/mirroring/browser',
  'components/mirroring/service:mirroring_service',
  'components/mirroring:mirroring_tests',
  'components/mirroring:mirroring_unittests',
  'components/openscreen_platform',
]


def _client_openscreen_chromium_spec(**kwargs):
  return bot_spec.BotSpec.create(luci_project='openscreen', **kwargs)


SPEC = {
    'builders': {
        'chromium_linux64_debug':
            _client_openscreen_chromium_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['openscreen_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                compile_targets=COMPILE_TARGETS,
                testing={
                    'platform': 'linux',
                },
            ),
        'chromium_mac_debug':
            _client_openscreen_chromium_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['openscreen_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                compile_targets=COMPILE_TARGETS,
                testing={
                    'platform': 'mac',
                },
            ),
    },
}
