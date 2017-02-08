# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""API for generating oauth2 tokens from locally stored secrets.

This is a thin wrapper over the authutil go executable, which itself calls
https://github.com/luci/luci-go/blob/master/client/authcli/authcli.go
"""

from recipe_engine import recipe_api


class ServiceAccountApi(recipe_api.RecipeApi):

  def _config_defaults(self):
    if self.m.platform.is_win:
      self.set_config('service_account_windows')
    else:
      self.set_config('service_account_default')

  def get_json_path(self, account):
    if self.c is None:
      self._config_defaults()
    return self.m.path.join(self.c.accounts_path,
                            'service-account-%s.json' % account)

  def get_token(self, account, scopes=None, lifetime_sec=None):
    if self.c is None:
      self._config_defaults()
    account_file = self.get_json_path(account)
    cmd = [self.c.authutil_path, 'token',
           '-service-account-json=' + account_file]
    if scopes:
      cmd += ['-scopes', ' '.join(scopes)]
    if lifetime_sec is not None:
      cmd += ['-lifetime',  '%ds' % lifetime_sec]

    try:
      # TODO: authutil is to be deployed using cipd.
      step_result = self.m.step(
          'get access token', cmd, stdout=self.m.raw_io.output_text(),
          step_test_data=lambda: self.m.raw_io.test_api.stream_output(
              'abc124', stream='stdout'))
    except self.m.step.StepFailure as ex:
      if not self.m.path.exists(self.c.authutil_path):
        ex.result.presentation.logs['Authutil not found'] = [
            'The authutil binary was not found at the default location.',
            '',
            'Build the following go module: infra/go/infra/tools/authutil',
            'and deploy it to: ' + self.c.authutil_path ]
      raise

    return step_result.stdout.strip()
