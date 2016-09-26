# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from recipe_engine.config import (
    config_item_context, ConfigGroup, Single, Static)
from recipe_engine.config_types import Path
from . import api as syzygy_api


def BaseConfig(CHECKOUT_PATH, **dummy_kwargs):
  return ConfigGroup(
    CHECKOUT_PATH = Static(CHECKOUT_PATH),

    official_build = Single(bool, empty_val=False, required=False),
    unittests_gypi = Single(Path, required=False),
    version_file = Single(Path, required=False),
  )


config_ctx = config_item_context(BaseConfig)


@config_ctx(is_root=True)
def BASE(dummy_c):
  pass


@config_ctx()
def syzygy(c):
  c.official_build = False
  c.unittests_gypi = c.CHECKOUT_PATH.join('syzygy', 'unittests.gypi')
  c.version_file = c.CHECKOUT_PATH.join('syzygy', 'SYZYGY_VERSION')


@config_ctx(includes=['syzygy'])
def syzygy_x64(dummy_c):
  pass


@config_ctx()
def syzygy_official(c):
  c.official_build = True
  c.unittests_gypi = c.CHECKOUT_PATH.join('syzygy', 'unittests.gypi')
  c.version_file = c.CHECKOUT_PATH.join('syzygy', 'SYZYGY_VERSION')


@config_ctx()
def kasko_official(c):
  c.official_build = True
  c.unittests_gypi = c.CHECKOUT_PATH.join('syzygy', 'kasko', 'unittests.gypi')
  c.version_file = c.CHECKOUT_PATH.join('syzygy', 'kasko', 'VERSION')
