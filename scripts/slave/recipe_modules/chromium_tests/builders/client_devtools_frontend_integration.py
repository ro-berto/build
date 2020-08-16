# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def _client_devtools_frontend_integration_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='devtools-frontend',
      luci_project='devtools-frontend',
      **kwargs)


SPEC = {
    'DevTools Linux':
        _client_devtools_frontend_integration_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'blink_tests',
            ],
            simulation_platform='linux',
        ),
}
