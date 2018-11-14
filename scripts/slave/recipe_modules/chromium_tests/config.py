# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single, Static
from recipe_engine.config_types import Path


def BaseConfig(CHECKOUT_PATH, **_kwargs):
  return ConfigGroup(
    staging = Single(bool, empty_val=False, required=False),
    source_side_spec_dir = Single(Path),
    # TODO(martiniss): Remove this and all uses
    test_spec_dir = Single(Path),
    CHECKOUT_PATH = Static(CHECKOUT_PATH),
    # If set, bypass the deapply patch and retry.
    only_with_patch = Single(bool, empty_val=False, required=False)
  )

config_ctx = config_item_context(BaseConfig)


@config_ctx()
def chromium(c):
  c.source_side_spec_dir = c.CHECKOUT_PATH.join('testing', 'buildbot')
  c.test_spec_dir = c.CHECKOUT_PATH.join('testing', 'buildbot')

@config_ctx()
def staging(c):
  c.staging = True

@config_ctx()
def code_coverage_trybot(c):
  c.only_with_patch = True
