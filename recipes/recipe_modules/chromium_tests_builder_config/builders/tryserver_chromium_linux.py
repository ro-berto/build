# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

# The config for the following builder(s) is now specified src-side in
# //infra/config/subprojects/chromium/try/tryserver.chromium.linux.star
# * linux-blink-web-tests-force-accessibility-rel
# * linux_layout_tests_layout_ng_disabled
# * linux_optional_gpu_tests_rel

SPEC = {
    'linux-layout-tests-edit-ng':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
}
