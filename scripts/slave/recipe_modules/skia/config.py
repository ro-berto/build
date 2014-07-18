# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Dict, Set, Single, Static
from slave.recipe_config_types import Path
from slave.recipe_modules.skia import base_flavor
from slave.recipe_modules.skia import default_flavor

# TODO(borenet): Most of these properties can be parsed out from the builder
# name, since we construct the builder name from the properties.
CONFIG_MAP = {
  'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug': {
    'gyp_defines': {
      'skia_arch_width': '64',
      'skia_gpu': '0',
      'skia_warnings_as_errors' :'0',
    },
    'flavor': default_flavor.DefaultFlavorUtils,
  },
}


def BaseConfig(BUILDER_NAME, **_kwargs):
  equal_fn = lambda tup: ('%s=%s' % tup)
  return ConfigGroup(
    BUILDER_NAME = Static(BUILDER_NAME),
    build_config = Single(str),
    build_targets = Single(list),
    gyp_env = ConfigGroup(
      GYP_DEFINES = Dict(equal_fn, ' '.join, (basestring,int,Path)),
    ),
    flavor = Single(base_flavor.BaseFlavorUtils, repr),
  )


VAR_TEST_MAP = {
  'BUILDER_NAME': ('Test-Ubuntu12-ShuttleA-NoGPU-x86_64-Debug',),
}


config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, '%(BUILDER_NAME)s')


@config_ctx(is_root=True)
def skia(c):
  """Base config for Skia."""
  c.build_config = 'Debug' if 'Debug' in c.BUILDER_NAME else 'Release'
  c.build_targets = ['most']
  base_builder_name = c.BUILDER_NAME.rstrip('-Trybot')
  c.gyp_env.GYP_DEFINES.update(
      CONFIG_MAP.get(base_builder_name, {}).get('gyp_defines', {}))
  c.flavor = CONFIG_MAP.get(base_builder_name, {}).get(
      'flavor', default_flavor.DefaultFlavorUtils)()

