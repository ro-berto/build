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

  def __init__(self, properties, **kwargs):
    super(GomaApi, self).__init__(**kwargs)
    self._goma_dir = None

    # Flag to represent local goma module running.
    self._is_local = False

    self._goma_started = False

    self._goma_ctl_env = {}
    self._jobs = properties.get('jobs', None)
    self._recommended_jobs = None
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
  def counterz_path(self):
    assert self._goma_dir
    return self.m.path['tmp_base'].join('goma_counterz')

  @property
  def bigquery_service_account_json_path(self):
    return self.m.puppet_service_account.get_key_path('goma-bigquery')

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
    data_cache = self.default_cache_path_per_slave.join('data')
    return data_cache.join(safe_buildername)

  @property
  def default_client_path(self):
    return self.default_cache_path_per_slave.join('client')

  @property
  def jobs(self):
    """Returns number of jobs for parallel build using Goma.

    Uses value from property "$build/goma:{\"jobs\": JOBS}" if configured
    (typically in cr-buildbucket.cfg), else defaults to `recommended_goma_jobs`.
    """
    return self._jobs or self.recommended_goma_jobs

  @property
  def recommended_goma_jobs(self):
    """Return the recommended number of jobs for parallel build using Goma.

    Prefer to use just `goma.jobs` and configure it through default builder
    properties in cr-buildbucket.cfg.

    This function caches the _recommended_jobs.
    """
    if self._recommended_jobs is None:
      # When goma is used, 10 * self.m.platform.cpu_count is basically good in
      # various situations according to our measurement. Build speed won't
      # be improved if -j is larger than that.
      #
      # For safety, we'd like to set the upper limit to 200.
      # Note that currently most try-bot build slaves have 8 processors.
      self._recommended_jobs = min(10 * self.m.platform.cpu_count, 200)

    return self._recommended_jobs

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

    with self.m.step.nest('ensure_goma') as step_result:
      if canary:
        step_result.presentation.step_text = 'canary goma client is selected'
        step_result.presentation.status = self.m.step.WARNING

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
        self._goma_dir = self.default_client_path

        self.m.cipd.ensure(self._goma_dir, {goma_package: ref})
        return self._goma_dir

  @property
  def goma_ctl(self):
    return self.m.path.join(self._goma_dir, 'goma_ctl.py')

  @property
  def goma_dir(self):
    assert self._goma_dir
    return self._goma_dir

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
      self._goma_ctl_env['GOMA_DUMP_STATS_FILE'] = (
          self.m.path['tmp_base'].join('goma_stats'))
      self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'] = (
          self.m.path['tmp_base'].join('crash_report_id'))

      if not self._is_local:
        self._goma_ctl_env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = (
            self.service_account_json_path)

      # Do not continue to build when unsupported compiler is used.
      self._goma_ctl_env['GOMA_HERMETIC'] = 'error'

      self._goma_ctl_env['GOMA_DUMP_COUNTERZ_FILE'] = self.counterz_path
      self._goma_ctl_env['GOMA_ENABLE_COUNTERZ'] = 'true'

      # Set larger entry limit to store result of included file analysis.
      # TODO(tikuta): make this the default value of goma client's.
      self._goma_ctl_env['GOMA_DEPS_CACHE_TABLE_THRESHOLD'] = '70000'

      # GLOG_log_dir should not be set.
      assert 'GLOG_log_dir' not in env

      if 'GOMA_TMP_DIR' in env:
        self._goma_ctl_env['GOMA_TMP_DIR'] = env['GOMA_TMP_DIR']

      if 'GOMA_CACHE_DIR' not in env:
        self._goma_ctl_env['GOMA_CACHE_DIR'] = self.default_cache_path

      if self.m.platform.is_win:
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

  def stop(self, build_exit_status, ninja_log_outdir=None,
           ninja_log_compiler=None, ninja_log_command=None,
           build_step_name='', **kwargs):
    """Stop goma compiler_proxy.

    A user is expected to execute start beforehand.
    It is user's responsibility to handle failure of stopping compiler_proxy.

    Args:
      build_exit_status: Exit status of ninja or other build commands like
                         make. (e.g. 0)
      ninja_log_outdir: Directory of ninja log. (e.g. "out/Release")
      ninja_log_compiler: Compiler used in ninja. (e.g. "clang")
      ninja_log_command:
        Command used for build.
        (e.g. ['ninja', '-C', 'out/Release'])

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
          self._upload_logs(ninja_log_outdir=ninja_log_outdir,
                            ninja_log_compiler=ninja_log_compiler,
                            ninja_log_command=ninja_log_command,
                            build_exit_status=build_exit_status,
                            build_step_name=build_step_name)
          if self._cloudtail_running:
            self._stop_cloudtail()

        self._goma_started = False
        self._goma_ctl_env = {}
      except self.m.step.StepFailure:
        nested_result.presentation.status = self.m.step.EXCEPTION
        raise

  def _upload_logs(self, ninja_log_outdir=None, ninja_log_compiler=None,
                   ninja_log_command=None, build_exit_status=None,
                   build_step_name='', name=None):
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

      build_exit_status: Exit status of ninja or other build commands like
                         make. (e.g. 0)
      name: Step name of log upload.
      skip_sendgomatsmon:
        Represents whether sending log to goma tsmon.
    """

    args = [
        '--upload-compiler-proxy-info',
        '--log-url-json-file', self.m.json.output(),
        '--gsutil-py-path', self.m.depot_tools.gsutil_py_path,
        '--bigquery-service-account-json',
        self.bigquery_service_account_json_path,
    ]

    json_test_data = {
      'compiler_proxy_log': 'https://chromium-build-stats.appspot.com/compiler_proxy_log/2017/03/30/build11-m1/compiler_proxy.exe.BUILD11-M1.chrome-bot.log.INFO.20170329-222936.4420.gz'
    }

    assert self._goma_jsonstatus_called
    args.extend(['--json-status', self.json_path])

    if ninja_log_outdir:
      assert ninja_log_command is not None

      # Since ninja_log_command can be long, it exceeds command line length
      # limit. So we write it to a file.
      args.extend([
          '--ninja-log-outdir', ninja_log_outdir,
          '--ninja-log-command-file', self.m.json.input(ninja_log_command),
      ])
      json_test_data['ninja_log'] = 'https://chromium-build-stats.appspot.com/ninja_log/2017/03/30/build11-m1/ninja_log.build11-m1.chrome-bot.20170329-224321.9976.gz'

    if build_exit_status is not None:
      args.extend(['--build-exit-status', build_exit_status])

    if build_step_name:
      args.extend([
          '--build-step-name', build_step_name,
      ])

    if ninja_log_compiler:
      args.extend(['--ninja-log-compiler', ninja_log_compiler])

    if self._goma_ctl_env.get('GOMA_DUMP_STATS_FILE'):
      args.extend([
          '--goma-stats-file', self._goma_ctl_env['GOMA_DUMP_STATS_FILE'],
      ])

      # We upload counterz stats when we upload goma_stats.
      if 'GOMA_DUMP_COUNTERZ_FILE' in self._goma_ctl_env:
        args.extend([
            '--goma-counterz-file',
            self._goma_ctl_env['GOMA_DUMP_COUNTERZ_FILE'],
        ])

    if self._goma_ctl_env.get('GOMACTL_CRASH_REPORT_ID_FILE'):
      args.extend([
          '--goma-crash-report-id-file',
          self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'],
      ])

    build_id = self.m.buildbucket.build_id
    if build_id:
      args.extend(['--build-id', build_id])

    builder_id = self.m.buildbucket.builder_id
    if builder_id:
      args.extend(['--builder-id-json',
                   self.m.json.input({
                       'project': builder_id.project,
                       'bucket': builder_id.bucket,
                       'builder': builder_id.builder,
                   })])
    if self.m.runtime.is_luci:
      args.append('--is-luci')

    if self.m.runtime.is_experimental:
      args.append('--is-experimental')

    # Set buildbot info used in goma_utils.MakeGomaStatusCounter etc.
    keys = [
      ('buildername', 'buildername'),
      ('mastername', 'mastername'),
      ('bot_id', 'slavename'),
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
      venv=True,
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
    build_exit_status = None

    if ninja_env is None:
      ninja_env = {}
    if goma_env is None:
      goma_env = {}

    # TODO(tikuta): Remove -j flag from ninja_command and set appropriate value.

    self.start(goma_env)

    build_step_name = name or 'compile'
    try:
      with self.m.context(env=ninja_env):
        self.m.step(build_step_name, ninja_command, **kwargs)
      build_exit_status = 0
    except self.m.step.StepFailure as e:
      build_exit_status = e.retcode
      raise e
    finally:
      self.stop(ninja_log_outdir=ninja_log_outdir,
                ninja_log_compiler=ninja_log_compiler,
                ninja_log_command=ninja_command,
                build_exit_status=build_exit_status,
                build_step_name=build_step_name)
