# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Static
from recipe_engine.config_types import Path

def BaseConfig(CHECKOUT_PATH, **_kwargs):
  return ConfigGroup(
      client_engine_integration_script = Static(
          CHECKOUT_PATH.join('blimp', 'tools',
                             'client_engine_integration.py')),
  )

config_ctx = config_item_context(BaseConfig)

@config_ctx()
def base_config(c):
  pass