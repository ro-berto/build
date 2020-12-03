# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""API for interacting with the re-client remote compiler."""

from recipe_engine import recipe_api


class ReclientApi(recipe_api.RecipeApi):
  """A module for interacting with re-client."""

  def __init__(self, props, **kwargs):
    super(ReclientApi, self).__init__(**kwargs)

    self._props = props
    self._instance = None
    DEFAULT_SERVICE = 'remotebuildexecution.googleapis.com:443'
    self._rbe_service = props.rbe_service or DEFAULT_SERVICE
    # Initialization is delayed until the first call for reclient exe
    self._reclient_cipd_dir = None

  @property
  def instance(self):
    if self._instance:
      return self._instance

    self._instance = self._props.instance
    if not self._instance and self._test_data.enabled:
      self._instance = 'test-rbe-project'

    if self._instance and '/' not in self._instance:
      # Set full instance name if only project ID is given.
      self._instance = 'projects/%s/instances/default_instance' % self._instance

    return self._instance

  @property
  def rewrapper_path(self):
    return self._get_exe_path('rewrapper')

  @property
  def _bootstrap_bin_path(self):
    return self._get_exe_path('bootstrap')

  def _get_exe_path(self, exe_name):
    if self.m.platform.is_win:
      exe_name += '.exe'
    if self._reclient_cipd_dir is None:
      reclient_cipd = self.m.path['checkout'].join('tools', 'reclient')
      self._reclient_cipd_dir = str(reclient_cipd)
    return self.m.path.join(self._reclient_cipd_dir, exe_name)

  @property
  def rbe_service_addr(self):
    if self.m.platform.is_win:
      return 'pipe://reproxy.pipe'
    return 'unix:///%s' % self.m.path['tmp_base'].join('reproxy.sock')

  def start_reproxy(self, log_dir):
    """Starts the reproxy via bootstramp.

    Args
      log_dir (str): Directory that holds the reproxy log
    """
    reproxy_bin_path = self._get_exe_path('reproxy')
    env = {
        'RBE_instance': self.instance,
        'RBE_log_dir': log_dir,
        'RBE_proxy_log_dir': log_dir,
        'RBE_re_proxy': reproxy_bin_path,
        'RBE_service': self._rbe_service,
        'RBE_server_address': self.rbe_service_addr,
        'RBE_use_application_default_credentials': 'false',
        'RBE_use_gce_credentials': 'true',
    }
    with self.m.context(env=env):
      return self.m.step('start reproxy via bootstrap',
                         [self._bootstrap_bin_path, '-output_dir', log_dir])

  def stop_reproxy(self, log_dir):
    """Stops the reproxy via bootstramp.

    After this, the rbe_metrics stats file will be inside log_dir
    Args
      log_dir (str): Directory that holds the reproxy log
    """
    return self.m.step('shutdown reproxy via bootstrap', [
        self._bootstrap_bin_path, '-shutdown', '-proxy_log_dir', log_dir,
        '-output_dir', log_dir
    ])
