# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_devtools_frontend_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='devtools-frontend',
      luci_project='devtools-frontend',
      **kwargs)


SPEC = {
    'DevTools Linux (chromium)':
        _chromium_devtools_frontend_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
}
