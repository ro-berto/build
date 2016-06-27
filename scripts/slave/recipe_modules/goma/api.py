# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

  def __init__(self, **kwargs):
    super(GomaApi, self).__init__(**kwargs)
    self._goma_dir = None
    self._goma_started = False

  @property
  def service_account_json_path(self):
    if self.m.platform.is_win:
      return 'C:\\creds\\service_accounts\\service-account-goma-client.json'
    return '/creds/service_accounts/service-account-goma-client.json'

  def ensure_goma(self, canary=False):
    with self.m.step.nest('ensure_goma'):
      try:
        self.m.cipd.set_service_account_credentials(
            self.service_account_json_path)

        self.m.cipd.install_client()
        goma_package = ('infra_internal/goma/client/%s' %
            self.m.cipd.platform_suffix())
        # For Windows there's only 64-bit goma client.
        if self.m.platform.is_win:
          goma_package = goma_package.replace('386', 'amd64')
        ref='release'
        if canary:
          ref='candidate'
        self._goma_dir = self.m.path['cache'].join('cipd', 'goma')
        self.m.cipd.ensure(self._goma_dir, {goma_package: ref})
        return self._goma_dir
      except self.m.step.StepFailure:  # pragma: no cover
        # TODO(phajdan.jr): make failures fatal after experiment.
        return None

  def start(self, env=None, **kwargs):
    """Start goma compiler_proxy.

    A user MUST execute ensure_goma beforehand.
    It is user's responsibility to handle failure of starting compiler_proxy.
    """
    assert self._goma_dir
    assert not self._goma_started
    if not env:
      env = {}
    env.update({'GOMA_SERVICE_ACCOUNT_JSON': self.service_account_json_path})
    self.m.python(
        name='start_goma',
        script=self.m.path.join(self._goma_dir, 'goma_ctl.py'),
        args=['restart'], env=env, **kwargs)
    self._goma_started = True

  def stop(self, goma_dir=None, **kwargs):
    """Stop goma compiler_proxy.

    A user MUST execute start beforehand.
    It is user's responsibility to handle failure of stopping compiler_proxy.
    """
    assert self._goma_dir
    assert self._goma_started
    self.m.python(
        name='stop_goma',
        script=self.m.path.join(self._goma_dir, 'goma_ctl.py'),
        args=['stop'], **kwargs)
    self._goma_started = False
