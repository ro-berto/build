# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_linux_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-linux-archive', **kwargs)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.linux.star
# * Cast Audio Linux
# * Cast Linux
# * Cast Linux ARM64
# * Cast Linux Debug
# * Linux Builder
# * Linux Builder (dbg)
# * Linux Builder (Wayland)
# * Linux Tests
# * Linux Tests (dbg)(1)
# * Linux Tests (Wayland)
# * linux-bfcache-rel
# * linux-extended-tracing-rel
# * Network Service Linux

SPEC = {
    'Leak Detection Linux':
        _chromium_linux_spec(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
}
