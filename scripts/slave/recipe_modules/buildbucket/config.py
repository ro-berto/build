# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single, Static


def BaseConfig(PLATFORM='default'):
  return ConfigGroup(
      buildbucket_host = Single(str, required=True),
      buildbucket_client_path = Single(str, required=True),
      PLATFORM = Static(str(PLATFORM))
  )


config_ctx = config_item_context(BaseConfig)


@config_ctx(is_root=True)
def BASE(c):
  if c.PLATFORM == 'win':
    c.buildbucket_client_path = 'C:\\infra-tools\\buildbucket.exe'
  else:
    c.buildbucket_client_path = '/opt/infra-tools/buildbucket'


@config_ctx(group='host')
def production_buildbucket(c):
  c.buildbucket_host = 'cr-buildbucket.appspot.com'


@config_ctx(group='host')
def test_buildbucket(c):
  c.buildbucket_host = 'cr-buildbucket-test.appspot.com'


@config_ctx(group='host')
def dev_buildbucket(c):
  c.buildbucket_host = 'cr-buildbucket-dev.appspot.com'
