# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""API for interacting with the re-client remote compiler."""

import json
import socket

from recipe_engine import recipe_api

from google.protobuf import json_format
from PB.recipe_modules.build.reclient import rbe_metrics_bq


def make_test_rbe_stats_pb():
  stats = rbe_metrics_bq.RbeMetricsBq().stats
  stats.environment['foo'] = 'false'
  stats.environment['bar'] = '42'
  return stats


class ReclientApi(recipe_api.RecipeApi):
  """A module for interacting with re-client."""

  def __init__(self, props, **kwargs):
    super(ReclientApi, self).__init__(**kwargs)

    self._props = props
    self._instance = None
    DEFAULT_SERVICE = 'remotebuildexecution.googleapis.com:443'
    self._service = props.service or DEFAULT_SERVICE
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
  def server_address(self):
    if self.m.platform.is_win:
      return 'pipe://reproxy.pipe'
    return 'unix:///%s' % self.m.path['tmp_base'].join('reproxy.sock')

  @property
  def rbe_service_addr(self):  #pragma: no cover
    # TODO(crbug.com/1141780): Deprecate this
    return self.server_address

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
        'RBE_service': self._service,
        'RBE_server_address': self.server_address,
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
        self.server_address, '-proxy_log_dir', log_dir, '-output_dir', log_dir
    ])
    self._stop_cloudtail()
    self._upload_rbe_metrics(log_dir)

    return step_result

  def _upload_rbe_metrics(self, log_dir):
    bq_pb = rbe_metrics_bq.RbeMetricsBq()
    bq_pb.build_id = self.m.buildbucket.build.id
    bq_pb.created_at.FromDatetime(self.m.time.utcnow())
    stats_raw = self.m.file.read_raw(
        'load rbe_metrics.pb',
        self.m.path.join(log_dir, 'rbe_metrics.pb'),
        test_data=make_test_rbe_stats_pb().SerializeToString())
    bq_pb.stats.ParseFromString(stats_raw)
    bq_json_dict = json_format.MessageToDict(
        message=bq_pb, preserving_proto_field_name=True)
    # "environment" is a map field and gets serialized to a JSON map.
    # Unfortunately, this is incompatible with the corresponding BQ schema,
    # which is a repeated field and thus expects a JSON array.
    envs = bq_pb.stats.environment
    if envs:
      bq_json_dict['stats']['environment'] = [{
          'key': k,
          'value': envs[k]
      } for k in envs]

    bqupload_cipd_path = self.m.cipd.ensure_tool(
        'infra/tools/bqupload/${platform}', 'latest')
    BQ_TABLE_NAME = 'goma-logs.experimental_rbe_metrics.rbe_metrics'
    # `bqupload`'s expected JSON proto format is different from that of the
    # protobuf's native MessageToJson, so we have to dump this json to string on
    # our own.
    step_result = self.m.step(
        'upload RBE metrics to BigQuery', [
            bqupload_cipd_path,
            BQ_TABLE_NAME,
        ],
        stdin=self.m.raw_io.input(data=json.dumps(bq_json_dict)))
    step_result.presentation.logs['rbe_metrics'] = json.dumps(
        bq_json_dict, indent=2)

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
