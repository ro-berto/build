# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single


def BaseConfig(BASE_URL, **_):
  return ConfigGroup(
    base_url = Single(basestring, empty_val=BASE_URL),
    auth_token = Single(basestring),
  )


config_ctx = config_item_context(BaseConfig)


@config_ctx()
def basic(_):
  pass
