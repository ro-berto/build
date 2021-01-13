# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""API for interacting with the re-client remote compiler."""

import socket

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
    self._jobs = props.jobs or None

    if self._test_data.enabled:
      self._hostname = 'fakevm999-m9'
    else:  #pragma: no cover
      # TODO: find a recipe way to get hostname
      self._hostname = socket.gethostname()

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
  def jobs(self):
    """Returns number of jobs for parallel build using reclient."""
    if self._jobs is None:
      # This heuristic is copied from Goma's recommended_jobs.
      self._jobs = min(10 * self.m.platform.cpu_count, 200)
    return self._jobs

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
      # This depends on where the reclient CIPD is checked out in DEPS,
      # https://source.chromium.org/chromium/chromium/src/+/master:DEPS;l=452-461;drc=6b88cf228d9d27f49e89f7c4d9ffb582771daa48
      reclient_cipd = self.m.path['checkout'].join('buildtools', 'reclient')
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
      self.m.step(
          'start reproxy via bootstrap',
          [self._bootstrap_bin_path, '-output_dir', log_dir],
          infra_step=True)

      # TODO: Shall we use the same project providing the RBE workers?
      cloudtail_project_id = 'goma-logs'
      self._start_cloudtail(cloudtail_project_id,
                            self.m.path.join(log_dir, 'reproxy.INFO'))

  def stop_reproxy(self, log_dir):
    """Stops the reproxy via bootstramp.

    After this, the rbe_metrics stats file will be inside log_dir
    Args
      log_dir (str): Directory that holds the reproxy log
    """
    step_result = self.m.step('shutdown reproxy via bootstrap', [
        self._bootstrap_bin_path, '-shutdown', '-server_address',
        self.rbe_service_addr, '-proxy_log_dir', log_dir, '-output_dir', log_dir
    ])
    self._stop_cloudtail()
    return step_result

  @property
  def _cloudtail_exe_path(self):
    if self.m.platform.is_win:
      return 'cloudtail.exe'
    return 'cloudtail'

  @property
  def _cloudtail_wrapper_path(self):
    return self.resource('cloudtail_wrapper.py')

  @property
  def _cloudtail_pid_file(self):
    return self.m.path['tmp_base'].join('cloudtail.pid')

  def _start_cloudtail(self, project_id, log_path):
    """Start cloudtail to upload reproxy INFO log.

    'cloudtail' binary should be in PATH already.

    Args:
      project_id (str): Cloud project ID
      log_path (str): Path to reproxy's INFO log.

    Raises:
      InfraFailure if it fails to start cloudtail
    """
    cloudtail_args = [
        'start', '--cloudtail-path', self._cloudtail_exe_path,
        '--cloudtail-project-id', project_id, '--cloudtail-log-path', log_path,
        '--pid-file',
        self.m.raw_io.output_text(leak_to=self._cloudtail_pid_file)
    ]

    step_result = self.m.build.python(
        name='start cloudtail',
        script=self._cloudtail_wrapper_path,
        args=cloudtail_args,
        step_test_data=(lambda: self.m.raw_io.test_api.output_text('12345')),
        infra_step=True)
    step_result.presentation.links['cloudtail'] = (
        'https://console.cloud.google.com/logs/viewer?'
        'project=%s&resource=gce_instance%%2F'
        'instance_id%%2F%s' % (project_id, self._hostname))

  def _stop_cloudtail(self):
    """Stop cloudtail started by _start_cloudtail

    Raises:
      InfraFailure if it fails to stop cloudtail
    """
    self.m.build.python(
        name='stop cloudtail',
        script=self._cloudtail_wrapper_path,
        args=['stop', '--killed-pid-file', self._cloudtail_pid_file],
        infra_step=True)
