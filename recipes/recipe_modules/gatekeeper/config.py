# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single


def BaseConfig(**_):
  return ConfigGroup(
    use_new_logic = Single(bool),
  )


config_ctx = config_item_context(BaseConfig)


@config_ctx()
def basic(c):
  c.use_new_logic = True
