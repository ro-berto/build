# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""**[DEPRECATED]** API for generating OAuth2 access tokens from service account
keys predeployed to Chrome Ops bots via Puppet.

Depends on 'authutil' being in PATH.

This module exists only to support Buildbot code. On LUCI use default account
exposed through 'recipe_engine/service_account' module.
"""

from recipe_engine import recipe_api


class PuppetServiceAccountApi(recipe_api.RecipeApi):
  @property
  def keys_path(self):
    """Path to a directory where ChromeOps Puppet drops service account keys."""
    if self.m.platform.is_win:
      return 'C:\\creds\\service_accounts'
    return '/creds/service_accounts'

  def get_key_path(self, account):
    """Path to a particular JSON key (as str)."""
    return self.m.path.join(self.keys_path, 'service-account-%s.json' % account)

  def get_access_token(self, account, scopes=None, lifetime_sec=None):
    """Returns an access token for a service account.

    Args:
      account: a name of the service account, as defined in Puppet config.
      scopes: list of OAuth scopes for new token, default is [userinfo.email].
      lifetime_sec: minimum allowed lifetime of the returned token (the token
          may live longer). Should be under 45m. Default is 10m.
    """
    return self.m.service_account.from_credentials_json(
        self.get_key_path(account)).get_access_token(scopes, lifetime_sec)
