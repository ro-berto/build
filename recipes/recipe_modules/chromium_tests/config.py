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

      # TODO(crbug.com/816629): Flip all bots to True and then remove
      # this option.
      use_swarming_command_lines=Single(bool, empty_val=True, required=False),
  )

config_ctx = config_item_context(BaseConfig)


@config_ctx()
def chromium(c):
  pass


@config_ctx()
def staging(c):
  c.staging = True


@config_ctx()
def use_swarming_command_lines(c):
  c.use_swarming_command_lines = True


@config_ctx()
def do_not_use_swarming_command_lines(c):
  c.use_swarming_command_lines = False
