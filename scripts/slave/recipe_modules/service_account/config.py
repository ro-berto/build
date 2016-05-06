# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single


def BaseConfig():
  return ConfigGroup(
      accounts_path = Single(str, required=True),
      authutil_path = Single(str, required=True))


config_ctx = config_item_context(BaseConfig)


@config_ctx()
def service_account_windows(c):
  c.accounts_path = 'C:\\creds\\service_accounts'
  c.authutil_path = 'C:\\infra-tools\\authutil.exe'


@config_ctx()
def service_account_default(c):
  c.accounts_path =  '/creds/service_accounts'
  c.authutil_path = '/opt/infra-tools/authutil'
