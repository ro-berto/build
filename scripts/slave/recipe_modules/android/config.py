# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_configs_util import config_item_context, ConfigGroup
from slave.recipe_configs_util import SimpleConfig, ListConfig, StaticConfig

def BaseConfig(USE_MIRROR=False):
  return ConfigGroup(
    lunch_flavor = SimpleConfig(basestring),
    repo = ConfigGroup(
      url = SimpleConfig(basestring),
      branch = SimpleConfig(basestring),
      sync_flags = ListConfig(basestring),
    ),
    USE_MIRROR = StaticConfig(bool(USE_MIRROR)),
  )

config_ctx = config_item_context(
  BaseConfig,
  {'USE_MIRROR': (False,)},
  'android')

@config_ctx()
def AOSP(c):
  c.lunch_flavor = 'full-eng'
  c.repo.url = 'https://android.googlesource.com/platform/manifest'
  c.repo.branch = 'android-4.3_r2.1'
  c.repo.sync_flags = ['-j16', '-d', '-f']
