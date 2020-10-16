# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single, Static
from recipe_engine.config_types import Path


def BaseConfig(CHECKOUT_PATH, **_kwargs):
  return ConfigGroup(
      staging=Single(bool, empty_val=False, required=False),

      # TODO(martiniss): Remove this and all uses
      CHECKOUT_PATH=Static(CHECKOUT_PATH),
      # TODO(894045): Remove once all tasks are switched to `swarming`
      use_swarming_recipe_to_trigger=Single(
          bool, empty_val=False, required=False),
      # TODO(crbug.com/chrome-operations/49):
      # Remove once all tasks are switched to `cas`
      use_cas=Single(bool, empty_val=False),
  )

config_ctx = config_item_context(BaseConfig)


@config_ctx()
def chromium(c):
  pass


@config_ctx()
def staging(c):
  c.staging = True


@config_ctx()
def use_swarming_recipe_to_trigger(c):
  c.use_swarming_recipe_to_trigger = True


@config_ctx()
def use_cas(c):
  c.use_cas = True
