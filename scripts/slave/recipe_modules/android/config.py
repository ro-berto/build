# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_configs_util import config_item_context, ConfigGroup
from slave.recipe_configs_util import Single, List, Static

def BaseConfig(USE_MIRROR=False):
  return ConfigGroup(
    lunch_flavor = Single(basestring),
    repo = ConfigGroup(
      url = Single(basestring),
      branch = Single(basestring),
      sync_flags = List(basestring),
    ),
    USE_MIRROR = Static(bool(USE_MIRROR)),
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
