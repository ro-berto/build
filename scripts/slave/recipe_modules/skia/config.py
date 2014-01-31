# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Dict, Static


# TODO(borenet): These properties can be parsed out from the builder name, since
# we construct the builder name from the properties.
GYP_DEFINES_MAP = {
  'Test-Ubuntu12-ShuttleA-NoGPU-x86_64-Debug':
      {'skia_arch_width': '64',
       'skia_gpu': '0',
       'skia_warnings_as_errors' :'0'},
}


def BaseConfig(BUILDER_NAME, **_kwargs):
  return ConfigGroup(
    BUILDER_NAME = Static(BUILDER_NAME),
    gyp_defines = Dict(),
  )


VAR_TEST_MAP = {
  'BUILDER_NAME': ('Test-Ubuntu12-ShuttleA-NoGPU-x86_64-Debug',),
}


config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, '%(BUILDER_NAME)s')


@config_ctx(is_root=True)
def skia(c):
  """Base config for Skia."""
  c.gyp_defines.update(GYP_DEFINES_MAP.get(c.BUILDER_NAME, {}))
