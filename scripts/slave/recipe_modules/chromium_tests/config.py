# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single, Static
from recipe_engine.config_types import Path


def BaseConfig(CHECKOUT_PATH, **_kwargs):
  return ConfigGroup(
    test_spec_dir = Single(Path),
    CHECKOUT_PATH = Static(CHECKOUT_PATH),
  )

config_ctx = config_item_context(BaseConfig)


@config_ctx()
def chromium(c):
  c.test_spec_dir = c.CHECKOUT_PATH.join('testing', 'buildbot')