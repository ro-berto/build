# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from slave.recipe_config import config_item_context, ConfigGroup, Single
from RECIPE_MODULES.syzygy import api as syzygy_api


def BaseConfig(**dummy_kwargs):
  return ConfigGroup(
    official_build = Single(bool, empty_val=False, required=False),
  )


config_ctx = config_item_context(BaseConfig, {}, 'syzygy')


@config_ctx(is_root=True)
def BASE(c):
  pass


@config_ctx()
def syzygy(c):
  c.official_build = False


@config_ctx()
def syzygy_official(c):
  c.official_build = True
