# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec, steps


def _chromium_devtools_frontend_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='devtools-frontend',
      luci_project='devtools-frontend',
      **kwargs)


SPEC = {
    'DevTools Linux (chromium)':
        _chromium_devtools_frontend_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type='builder',
            compile_targets=[
                'blink_tests',
            ],
            testing={
                'platform': 'linux',
            },
        ),
}
