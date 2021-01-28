# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""API for interacting with the re-client remote compiler."""

import contextlib
import gzip
import io
import json
import socket
import time

from recipe_engine import recipe_api

from google.protobuf import json_format
from PB.recipe_modules.build.reclient import rbe_metrics_bq


def make_test_rbe_stats_pb():
  stats = rbe_metrics_bq.RbeMetricsBq().stats
  stats.environment['foo'] = 'false'
  stats.environment['bar'] = '42'
  return stats


class MalformedREWrapperFlag(Exception):

  def __init__(self, flag):
    full_message = 'Flag "{}" doesn\'t start with "RBE_"'.format(flag)
    super(MalformedREWrapperFlag, self).__init__(full_message)


class BuildResultReceiver(object):

  def __init__(self):
    self.build_exit_status = -1


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
    self._rewrapper_env = None
    self._reclient_log_dir = None

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
  def rewrapper_env(self):
    # While this verification would better be placed at __init__, the test
    # framework 1) doesn't check for exceptions thrown during object creation,
    # 2) requires 100% code coverage. Thus we have to move any exception
    # throwing code -- such as checking validity of props inputs -- outside
    # __init__.
    if self._rewrapper_env is None:
      self._rewrapper_env = self._verify_rewrapper_flags(
          self._props.rewrapper_env)

    # While it'd make more sense to set this during __init__, deciding the
    # server_address requires knowing which platform we're running on - and
    # accessing the recipe deps that provides platform can't happen until
    # _after_ the object is created.
    if 'RBE_server_address' not in self._rewrapper_env:
      self._rewrapper_env['RBE_server_address'] = self.server_address
    return self._rewrapper_env

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
    # Shrink the size if the domain socket path length becomes a problem.
    return 'unix:///%s' % self._tmp_base_dir.join('reproxy.sock')

  @property
  def _tmp_base_dir(self):
    return self.m.path['tmp_base']

  @contextlib.contextmanager
  def process(self, ninja_step_name, ninja_command):
    """Do preparation and cleanup steps for running the ninja command.

    Args:
      ninja_step_name: Step name of the ninja build.
      ninja_command: Command used for build.
                     (e.g. ['ninja', '-C', 'out/Release'])
    """
    reclient_log_dir = self.m.path.mkdtemp('reclient_log')
    with self.m.step.nest('preprocess for reclient'):
      self._start_reproxy(reclient_log_dir)

      # TODO: Shall we use the same project providing the RBE workers?
      cloudtail_project_id = 'goma-logs'
      self._start_cloudtail(cloudtail_project_id,
                            reclient_log_dir.join('reproxy.INFO'))
    p = BuildResultReceiver()
    try:
      with self.m.context(env=self.rewrapper_env):
        yield p
    finally:
      with self.m.step.nest('postprocess for reclient'):
        self._stop_reproxy(reclient_log_dir)
        self._stop_cloudtail()
        self._upload_rbe_metrics(reclient_log_dir)
        if ninja_command:
          self._upload_ninja_log(ninja_step_name, ninja_command,
                                 p.build_exit_status)
        self.m.file.rmtree('cleanup reclient log dir', reclient_log_dir)

  def _start_reproxy(self, reclient_log_dir):
    """Starts the reproxy via bootstramp.

    Args:
      reclient_log_dir: Directory to hold the logs produced by reclient.
                        Specifically, it contains the .rpl file, which can be of
                        several GB. 
    """
    reproxy_bin_path = self._get_exe_path('reproxy')
    env = {
        'RBE_instance': self.instance,
        'RBE_log_dir': reclient_log_dir,
        'RBE_proxy_log_dir': reclient_log_dir,
        'RBE_re_proxy': reproxy_bin_path,
        'RBE_service': self._service,
        'RBE_server_address': self.server_address,
        'RBE_use_application_default_credentials': 'false',
        'RBE_use_gce_credentials': 'true',
    }

    with self.m.context(env=env):
      self.m.step(
          'start reproxy via bootstrap',
          [self._bootstrap_bin_path, '-output_dir', reclient_log_dir],
          infra_step=True)

  def _stop_reproxy(self, reclient_log_dir):
    """Stops the reproxy via bootstramp.

    Args:
      reclient_log_dir: Directory to hold the logs produced by reclient.
    """
    self.m.step(
        'shutdown reproxy via bootstrap', [
            self._bootstrap_bin_path, '-shutdown', '-server_address',
            self.server_address, '-proxy_log_dir', reclient_log_dir,
            '-output_dir', reclient_log_dir
        ],
        infra_step=True)

  def _upload_rbe_metrics(self, reclient_log_dir):
    bq_pb = rbe_metrics_bq.RbeMetricsBq()
    bq_pb.build_id = self.m.buildbucket.build.id
    bq_pb.created_at.FromDatetime(self.m.time.utcnow())
    stats_raw = self.m.file.read_raw(
        'load rbe_metrics.pb',
        reclient_log_dir.join('rbe_metrics.pb'),
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
        stdin=self.m.raw_io.input(data=json.dumps(bq_json_dict)),
        infra_step=True)
    step_result.presentation.logs['rbe_metrics'] = json.dumps(
        bq_json_dict, indent=2)

  def _upload_ninja_log(self, name, ninja_command, build_exit_status):
    """
    Upload several logs to GCS, including:
    * ninja command line args
    * ninja logs
    * build id, build exit status, etc.

    Args:
      name: Name of the build step
      ninja_command: Command used for build.
                     (e.g. ['ninja', '-C', 'out/Release'])
      build_exit_status: Exit status of ninja or other build commands like
                         make. (e.g. 0)

    Raises:
      InfraFailure: If there is an error during the GCS uploading.
    """
    log_index = ninja_command.index('-C') + 1
    ninja_log_outdir = ninja_command[log_index].replace('/', self.m.path.sep)

    # Metadata schema:
    # https://source.chromium.org/chromium/infra/infra/+/master:go/src/infra/appengine/chromium_build_stats/ninjalog/ninjalog.go;l=94-145;drc=deb62f6ebdf51d5187830310eddc9826d53dcc85
    metadata = {
        'cmdline': ninja_command,
        'cwd': str(self.m.context.cwd),  # make it serializable
        'platform': self.m.platform.name,
        'build_id': self.m.buildbucket.build.id,
        'step_name': name,
        'exit': build_exit_status,
        'env': self.m.context.env.copy(),
    }
    time_now = self.m.time.utcnow()
    # Must start with 'ninja_log' prefix, see
    # https://source.chromium.org/chromium/infra/infra/+/master:go/src/infra/appengine/chromium_build_stats/app/ninja_log.go;l=311-314;drc=e507df6040ea871ba6ef6b5e7da00d8cb186a1bd
    gzip_filename = 'ninja_log.%s.%s.gz' % (time_now.strftime('%Y%m%d-%H%M%S'),
                                            self.m.uuid.random())
    gzip_path = self._tmp_base_dir.join(gzip_filename)
    # This assumes that ninja_log is small enough to be loaded into RAM. (As of
    # 2021/01, it's around 3MB.)
    data_txt = self.m.file.read_text(
        'read ninja log', self.m.path.join(ninja_log_outdir, '.ninja_log'))
    data_txt += '\n# end of ninja log\n' + json.dumps(metadata)
    with io.BytesIO() as f_out:
      # |gzip_out| is created at the inner `with` clause intentionally, so that
      # its content is all flushed to |f_out| before writing the stream.
      #
      # Set a fixed mtime in the test, since gzip writes mtime as part of the
      # header, see
      # https://github.com/python/cpython/blob/8dfe15625e6ea4357a13fec7989a0e6ba2bf1359/Lib/gzip.py#L259
      mtime = time.mktime(time_now.timetuple())
      with gzip.GzipFile(fileobj=f_out, mode='w', mtime=mtime) as gzip_out:
        gzip_out.write(data_txt)

      gzip_data = f_out.getvalue()
      if self._test_data.enabled:
        gzip_data = 'fake gzip data'
      self.m.file.write_raw('create ninja log gzip', gzip_path, gzip_data)

    GS_BUCKET = 'chrome-goma-log'
    gs_filename = '%s/reclient/%s' % (time_now.date().strftime('%Y/%m/%d'),
                                      gzip_filename)
    step_result = self.m.gsutil.upload(gzip_path, GS_BUCKET, gs_filename)
    viewer_url = ('https://chromium-build-stats.appspot.com/ninja_log/' +
                  gs_filename)
    step_result.presentation.links['ninja_log'] = viewer_url

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
    return self._tmp_base_dir.join('cloudtail.pid')

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

  def _verify_rewrapper_flags(self, rewrapper_env):
    str_rewrapper_env = {}

    for flag, value in rewrapper_env.items():
      if not flag.startswith('RBE_'):
        raise MalformedREWrapperFlag(flag)
      else:
        str_rewrapper_env[str(flag)] = str(value)

    return str_rewrapper_env
