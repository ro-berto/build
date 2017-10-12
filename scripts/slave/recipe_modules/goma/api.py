# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import socket

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """
  GomaApi contains helper functions for using goma.

  For local running of goma recipe module,
  set local goma dir like below at the beginning of recipe running.
  `api.goma.set_goma_dir_for_local_test(goma_dir)`
  """

  def __init__(self, **kwargs):
    super(GomaApi, self).__init__(**kwargs)
    self._goma_dir = None

    # Flag to represent local goma module running.
    self._is_local = False

    self._goma_started = False

    self._goma_ctl_env = {}
    self._goma_jobs = None
    self._jsonstatus = None
    self._goma_jsonstatus_called = False
    self._cloudtail_running = False

    self._is_canary = False

    if self._test_data.enabled:
      self._hostname = 'fakevm999-m9'
    else:  #pragma: no cover
      # TODO(tikuta): find a recipe way to get hostname
      self._hostname = socket.gethostname()

  @property
  def service_account_json_path(self):
    return self.m.puppet_service_account.get_key_path('goma-client')

  @property
  def cloudtail_service_account_json_path(self):
    return self.m.puppet_service_account.get_key_path('goma-cloudtail')

  @property
  def cloudtail_exe(self):
    assert self._goma_dir
    if self.m.platform.is_win:
      return 'cloudtail.exe'
    return 'cloudtail'

  @property
  def cloudtail_pid_file(self):
    return self.m.path['tmp_base'].join('cloudtail.pid')

  @property
  def json_path(self):
    assert self._goma_dir
    return self.m.path['tmp_base'].join('goma_jsonstatus.json')

  @property
  def jsonstatus(self):
    assert self._jsonstatus
    return self._jsonstatus

  @property
  def default_cache_path_per_slave(self):
    try:
      # Legacy Buildbot cache path:
      return self.m.path['goma_cache']
    except KeyError:
      # New more generic cache path
      return self.m.path['cache'].join('goma')

  @property
  def default_cache_path(self):
    safe_buildername = re.sub(r'[^a-zA-Z0-9]', '_',
                              self.m.properties['buildername'])
    return self.default_cache_path_per_slave.join(safe_buildername)

  @property
  def recommended_goma_jobs(self):
    """
    Return the recommended number of jobs for parallel build using Goma.

    This function caches the _goma_jobs.
    """
    if self._goma_jobs:
      return self._goma_jobs

    step_result = self.m.build.python(
      'calculate the number of recommended jobs',
      self.resource('utils.py'),
      args=[
          'jobs',
          '--file-path', self.m.raw_io.output_text()
      ],
      step_test_data=(
          lambda: self.m.raw_io.test_api.output_text('50'))
    )
    self._goma_jobs = int(step_result.raw_io.output_text)

    return self._goma_jobs

  def set_goma_dir_for_local_test(self, goma_dir):
    """
    This function is made for local recipe test only.
    Do not use in recipes used by buildbots.
    """
    self._goma_dir = goma_dir
    self._is_local = True

  def ensure_goma(self, canary=False):
    if self._is_local:
      # When using goma module on local debug, we need to skip cipd step.
      return self._goma_dir

    self._is_canary = canary

    with self.m.step.nest('ensure_goma'):
      with self.m.context(infra_steps=True):
        self.m.cipd.set_service_account_credentials(
            self.service_account_json_path)

        goma_package = ('infra_internal/goma/client/%s' %
            self.m.cipd.platform_suffix())
        # For Windows there's only 64-bit goma client.
        if self.m.platform.is_win:
          goma_package = goma_package.replace('386', 'amd64')
        ref='release'
        if canary:
          ref='candidate'
        self._goma_dir = self.m.path['cache'].join('goma_client')

        self.m.cipd.ensure(self._goma_dir, {goma_package: ref})
        return self._goma_dir

  @property
  def goma_ctl(self):
    return self.m.path.join(self._goma_dir, 'goma_ctl.py')

  @property
  def goma_dir(self):
    assert self._goma_dir
    return self._goma_dir

  @property
  def build_data_dir(self):
    return self.m.properties.get('build_data_dir')

  def _make_goma_cache_dir(self, goma_cache_dir):
    """Ensure goma_cache_dir exist. Make it if not exists."""

    self.m.file.ensure_directory('goma cache directory', goma_cache_dir)

  def _start_cloudtail(self):
    """Start cloudtail to upload compiler_proxy.INFO.

    'cloudtail' binary should be in PATH already.

    Raises:
      InfraFailure if it fails to start cloudtail
    """

    self.m.build.python(
      name='start cloudtail',
      script=self.resource('cloudtail_utils.py'),
      args=['start', '--cloudtail-path', self.cloudtail_exe,
            '--cloudtail-service-account-json',
            self.cloudtail_service_account_json_path,
            '--pid-file', self.m.raw_io.output_text(
                leak_to=self.cloudtail_pid_file)],
      step_test_data=(
          lambda: self.m.raw_io.test_api.output_text('12345')),
      infra_step=True)
    self._cloudtail_running = True

  def _run_jsonstatus(self):
    with self.m.context(env=self._goma_ctl_env):
      jsonstatus_result = self.m.python(
          name='goma_jsonstatus', script=self.goma_ctl,
          args=['jsonstatus',
                self.m.json.output(leak_to=self.json_path)],
          step_test_data=lambda: self.m.json.test_api.output(
              data={'notice':[{
                  'infra_status': {
                      'ping_status_code': 200,
                      'num_user_error': 0,
                  }
              }]}))
    self._goma_jsonstatus_called = True

    self._jsonstatus = jsonstatus_result.json.output
    if self._jsonstatus is None:
      jsonstatus_result.presentation.status = self.m.step.WARNING

  def _stop_cloudtail(self):
    """Stop cloudtail started by _start_cloudtail

    Raises:
      InfraFailure if it fails to stop cloudtail
    """

    self.m.build.python(
        name='stop cloudtail',
        script=self.resource('cloudtail_utils.py'),
        args=['stop', '--killed-pid-file', self.cloudtail_pid_file],
        infra_step=True)

  def start(self, env=None, **kwargs):
    """Start goma compiler_proxy.

    A user MUST execute ensure_goma beforehand.
    It is user's responsibility to handle failure of starting compiler_proxy.
    """
    assert self._goma_dir
    assert not self._goma_started

    if env is None:
      env = {}

    with self.m.step.nest('preprocess_for_goma') as nested_result:
      if self.build_data_dir:
        self._goma_ctl_env['GOMA_DUMP_STATS_FILE'] = (
            self.m.path.join(self.build_data_dir, 'goma_stats_proto'))
        self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'] = (
            self.m.path.join(self.build_data_dir, 'crash_report_id_file'))

      if not self._is_local:
        self._goma_ctl_env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = (
            self.service_account_json_path)

      # Do not continue to build when unsupported compiler is used.
      self._goma_ctl_env['GOMA_HERMETIC'] = 'error'

      self._goma_ctl_env['GOMA_BACKEND_SOFT_STICKINESS'] = 'false'

      if self._is_canary:
        # Set larger entry limit to store result of included file analysis.
        # TODO(tikuta): make this default
        self._goma_ctl_env['GOMA_DEPS_CACHE_TABLE_THRESHOLD'] = '70000'

      # GLOG_log_dir should not be set.
      assert 'GLOG_log_dir' not in env

      if 'GOMA_TMP_DIR' in env:
        self._goma_ctl_env['GOMA_TMP_DIR'] = env['GOMA_TMP_DIR']

      if 'GOMA_CACHE_DIR' not in env:
        self._goma_ctl_env['GOMA_CACHE_DIR'] = self.default_cache_path

      if self._is_canary and self.m.platform.is_win:
        self._goma_ctl_env['GOMA_ENABLE_MACRO_CACHE'] = 'true'

      goma_ctl_start_env = self._goma_ctl_env.copy()

      goma_ctl_start_env.update(env)

      try:
        self._make_goma_cache_dir(self.default_cache_path)
        with self.m.context(env=goma_ctl_start_env):
          result = self.m.python(
              name='start_goma',
              script=self.goma_ctl,
              args=['restart'], infra_step=True, **kwargs)
          if not self._is_local:
            result.presentation.links['cloudtail'] = (
                'https://console.cloud.google.com/logs/viewer?'
                'project=goma-logs&resource=gce_instance%%2F'
                'instance_id%%2F%s&timestamp=%s' %
                (self._hostname, self.m.time.utcnow().isoformat()))

        self._goma_started = True
        if not self._is_local:
          self._start_cloudtail()

      except self.m.step.InfraFailure as e:
        with self.m.step.defer_results():
          self._run_jsonstatus()

          with self.m.context(env=self._goma_ctl_env):
            self.m.python(
                name='stop_goma (start failure)',
                script=self.goma_ctl,
                args=['stop'], **kwargs)
          self._upload_logs(name='upload_goma_start_failed_logs')
        nested_result.presentation.status = self.m.step.EXCEPTION
        raise e

  def stop(self, ninja_log_outdir=None, ninja_log_compiler=None,
           ninja_log_command=None, ninja_log_exit_status=None, **kwargs):
    """Stop goma compiler_proxy.

    A user is expected to execute start beforehand.
    It is user's responsibility to handle failure of stopping compiler_proxy.

    Raises:
      StepFailure if it fails to stop goma or upload logs.
    """
    assert self._goma_dir

    with self.m.step.nest('postprocess_for_goma') as nested_result:
      try:
        with self.m.step.defer_results():
          self._run_jsonstatus()

          with self.m.context(env=self._goma_ctl_env):
            self.m.python(name='goma_stat', script=self.goma_ctl,
                          args=['stat'],
                          **kwargs)
            self.m.python(name='stop_goma', script=self.goma_ctl,
                          args=['stop'], **kwargs)
          self._upload_logs(ninja_log_outdir, ninja_log_compiler,
                            ninja_log_command, ninja_log_exit_status)
          if self._cloudtail_running:
            self._stop_cloudtail()

        self._goma_started = False
        self._goma_ctl_env = {}
      except self.m.step.StepFailure:
        nested_result.presentation.status = self.m.step.EXCEPTION
        raise

  def _upload_logs(self, ninja_log_outdir=None, ninja_log_compiler=None,
                   ninja_log_command=None, ninja_log_exit_status=None,
                   name=None):
    """
    Upload some logs to goma client log/monitoring server.
    * log of compiler_proxy
    * log of ninja
    * command line args for ninja
    * build exit status and etc.

    Args:
      ninja_log_outdir: Directory of ninja log. (e.g. "out/Release")
      ninja_log_compiler: Compiler used in ninja. (e.g. "clang")
      ninja_log_command:
        Command used for build.
        (e.g. ['ninja', '-C', 'out/Release'])

      ninja_log_exit_status: Exit status of ninja. (e.g. 0)
      name: Step name of log upload.
      skip_sendgomatsmon:
        Represents whether sending log to goma tsmon.
    """

    args = [
        '--upload-compiler-proxy-info',
        '--log-url-json-file', self.m.json.output(),
        '--gsutil-py-path', self.m.depot_tools.gsutil_py_path,
    ]

    json_test_data = {
      'compiler_proxy_log': 'http://chromium-build-stats.appspot.com/compiler_proxy_log/2017/03/30/build11-m1/compiler_proxy.exe.BUILD11-M1.chrome-bot.log.INFO.20170329-222936.4420.gz'
    }

    assert self._goma_jsonstatus_called
    args.extend(['--json-status', self.json_path])

    if ninja_log_outdir:
      assert ninja_log_command is not None

      args.extend([
          '--ninja-log-outdir', ninja_log_outdir,
          '--ninja-log-command', str(ninja_log_command)
      ])
      json_test_data['ninja_log'] = 'http://chromium-build-stats.appspot.com/ninja_log/2017/03/30/build11-m1/ninja_log.build11-m1.chrome-bot.20170329-224321.9976.gz'

    if ninja_log_exit_status is not None:
      args.extend(['--ninja-log-exit-status', ninja_log_exit_status])

    if ninja_log_compiler:
      args.extend(['--ninja-log-compiler', ninja_log_compiler])

    if self.build_data_dir:
      args.extend([
          '--goma-stats-file', self._goma_ctl_env['GOMA_DUMP_STATS_FILE'],
          '--goma-crash-report-id-file',
          self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'],
          '--build-data-dir', self.build_data_dir,
      ])

    # Set buildbot info used in goma_utils.MakeGomaStatusCounter etc.
    keys = [
      ('buildername', 'buildername'),
      ('mastername', 'mastername'),
      ('bot_id', 'slavename'),
      ('clobber', 'clobber'),
    ]
    for prop_name, flag_suffix in keys:
      if prop_name in self.m.properties:
        args.extend([
            '--buildbot-%s' % flag_suffix, self.m.properties[prop_name]
        ])

    result = self.m.build.python(
      name=name or 'upload_log',
      script=self.package_repo_resource('scripts', 'slave',
                                        'upload_goma_logs.py'),
      args=args,
      step_test_data=(lambda: self.m.json.test_api.output(json_test_data)))

    for log in ('compiler_proxy_log', 'ninja_log'):
      if log in result.json.output:
        result.presentation.links[log] = result.json.output[log]

  def build_with_goma(self, ninja_command, name=None, ninja_log_outdir=None,
                      ninja_log_compiler=None, goma_env=None, ninja_env=None,
                      **kwargs):
    """Build with ninja_command using goma

    Args:
      ninja_command: Command used for build.
                     This is sent as part of log.
                     (e.g. ['ninja', '-C', 'out/Release'])
      name: Name of compile step.
      ninja_log_outdir: Directory of ninja log. (e.g. "out/Release")
      ninja_log_compiler: Compiler used in ninja. (e.g. "clang")
      goma_env: Environment controlling goma behavior.
      ninja_env: Environment for ninja.

    Returns:
      TODO(tikuta): return step_result

    Raises:
      StepFailure or InfraFailure if it fails to build or
      occurs something failure on goma steps.
    """
    ninja_log_exit_status = None

    if ninja_env is None:
      ninja_env = {}
    if goma_env is None:
      goma_env = {}

    # TODO(tikuta): Remove -j flag from ninja_command and set appropriate value.

    self.start(goma_env)

    try:
      with self.m.context(env=ninja_env):
        self.m.step(name or 'compile', ninja_command, **kwargs)
      ninja_log_exit_status = 0
    except self.m.step.StepFailure as e:
      ninja_log_exit_status = e.retcode
      raise e
    finally:
      self.stop(ninja_log_outdir=ninja_log_outdir,
                ninja_log_compiler=ninja_log_compiler,
                ninja_log_command=ninja_command,
                ninja_log_exit_status=ninja_log_exit_status)
