# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single


def BaseConfig():
  return ConfigGroup(
      priority=Single(int),
      expiration=Single(int),
      strategy_timeout=Single(int),
  )


config_ctx = config_item_context(BaseConfig)


@config_ctx(is_root=True)
def BASE(c):
  c.priority = 200
  c.expiration = 5 * 60 * 60  # 5 hours
  c.strategy_timeout = 60 * 60  # 1 hour


@config_ctx(group='trigger_mode')
def auto(c):
  pass


@config_ctx(group='trigger_mode')
def manual(c):
  c.priority = 20
  c.expiration = 60 * 60  # 1 hours
