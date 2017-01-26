# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

  def __init__(self, **kwargs):
    super(GomaApi, self).__init__(**kwargs)
    self._goma_dir = None
    self._goma_started = False

    self._goma_ctl_env = {}
    self._goma_jobs = None
    self._jsonstatus = None
    self._goma_jsonstatus_called = False

  @property
  def service_account_json_path(self):
    if self.m.platform.is_win:
      return 'C:\\creds\\service_accounts\\service-account-goma-client.json'
    return '/creds/service_accounts/service-account-goma-client.json'

  @property
  def cloudtail_service_account_json_path(self):
    if self.m.platform.is_win:
      return 'C:\\creds\\service_accounts\\service-account-goma-cloudtail.json'
    return '/creds/service_accounts/service-account-goma-cloudtail.json'

  @property
  def cloudtail_path(self):
    assert self._goma_dir
    return self.m.path.join(self._goma_dir, 'cloudtail')

  @property
  def cloudtail_pid_file(self):
    return self.m.path['tmp_base'].join('cloudtail.pid')

  @property
  def json_path(self):
    assert self._goma_dir
    return self.m.path.join(self._goma_dir, 'jsonstatus')

  @property
  def jsonstatus(self):
    assert self._jsonstatus
    return self._jsonstatus

  @property
  def default_cache_path(self):
    safe_buildername = re.sub(r'[^a-zA-Z0-9]', '_',
                              self.m.properties['buildername'])
    try:
      # Legacy Buildbot cache path:
      return self.m.path['goma_cache'].join(safe_buildername)
    except KeyError:
      # New more generic cache path
      return self.m.path['cache'].join('goma', safe_buildername)

  @property
  def recommended_goma_jobs(self):
    """
    Return the recommended number of jobs for parallel build using Goma.

    This function caches the _goma_jobs.
    """
    if self._goma_jobs:
      return self._goma_jobs

    step_result = self.m.python(
      'calculate the number of recommended jobs',
      self.package_repo_resource('scripts', 'tools', 'runit.py'),
      args=[
          '--show-path', 'python', self.resource('utils.py'), 'jobs',
          '--file-path', self.m.raw_io.output()
      ],
      step_test_data=(
          lambda: self.m.raw_io.test_api.output('50'))
    )
    self._goma_jobs = int(step_result.raw_io.output)

    return self._goma_jobs

  def ensure_goma(self, canary=False):
    with self.m.step.nest('ensure_goma'):
      with self.m.step.context({'infra_step': True}):
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

          # To update:
          # ./cipd set-ref infra/tools/cloudtail/ \
          #     -ref goma_recipe_module \
          #     -version git_revision:c6b17d5aa4fa6396c5f971248120e0e624c21fb3
          #
          # To see tags (e.g. git_revision:*):
          # ./cipd describe infra/tools/cloudtail/linux-amd64 \
          #     -version goma_recipe_module
          cloudtail_package = (
              'infra/tools/cloudtail/%s' % self.m.cipd.platform_suffix())
          cloudtail_version = 'goma_recipe_module'

          self.m.cipd.ensure(self._goma_dir,
                             {goma_package: ref,
                              cloudtail_package: cloudtail_version})

          return self._goma_dir
        except self.m.step.StepFailure:
          # TODO(phajdan.jr): make failures fatal after experiment.
          return None

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

    self.m.file.makedirs('goma cache directory', goma_cache_dir)

  def _start_cloudtail(self):
    """Start cloudtail to upload compiler_proxy.INFO

    Raises:
      InfraFailure if it fails to start cloudtail
    """

    self.m.python(
      name='start cloudtail',
      script=self.resource('cloudtail_utils.py'),
      args=['start',
            '--cloudtail-path', self.cloudtail_path,
            '--cloudtail-service-account-json',
            self.cloudtail_service_account_json_path,
            '--pid-file', self.m.raw_io.output(
                leak_to=self.cloudtail_pid_file)],
      step_test_data=(
          lambda: self.m.raw_io.test_api.output('12345')),
      infra_step=True)

  def _run_jsonstatus(self):
    jsonstatus_result = self.m.python(
        name='goma_jsonstatus', script=self.goma_ctl,
        args=['jsonstatus'],
        stdout=self.m.json.output(),
        step_test_data=lambda: self.m.json.test_api.output_stream(
            {'notice':[{
                'infra_status': {
                    'ping_status_code': 200,
                    'num_user_error': 0,
                }
            }]}),
        env=self._goma_ctl_env)
    self._goma_jsonstatus_called = True

    self._jsonstatus = jsonstatus_result.stdout
    self.m.shutil.write('write_jsonstatus',
                        path=self.json_path,
                        data=json.dumps(self._jsonstatus))

  def _stop_cloudtail(self):
    """Stop cloudtail started by _start_cloudtail

    Raises:
      InfraFailure if it fails to stop cloudtail
    """

    self.m.python(
        name='stop cloudtail',
        script=self.resource('cloudtail_utils.py'),
        args=['stop',
              '--killed-pid-file', self.cloudtail_pid_file],
        infra_step=True)

  def start(self, env=None, **kwargs):
    """Start goma compiler_proxy.

    A user MUST execute ensure_goma beforehand.
    It is user's responsibility to handle failure of starting compiler_proxy.
    """
    assert self._goma_dir
    assert not self._goma_started

    with self.m.step.nest('preprocess_for_goma'):
      if self.build_data_dir:
        self._goma_ctl_env['GOMA_DUMP_STATS_FILE'] = (
            self.m.path.join(self.build_data_dir, 'goma_stats_proto'))
        self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'] = (
            self.m.path.join(self.build_data_dir, 'crash_report_id_file'))

      self._goma_ctl_env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = (
          self.service_account_json_path)

      # GLOG_log_dir should not be set.
      assert env is None or 'GLOG_log_dir' not in env

      goma_ctl_start_env = self._goma_ctl_env.copy()

      if env is not None:
        goma_ctl_start_env.update(env)

      try:
        self._make_goma_cache_dir(self.default_cache_path)
        self.m.python(
            name='start_goma',
            script=self.goma_ctl,
            args=['restart'], env=goma_ctl_start_env, infra_step=True, **kwargs)
        self._goma_started = True

        self._start_cloudtail()

      except self.m.step.InfraFailure as e:
        with self.m.step.defer_results():
          self._run_jsonstatus()

          self.m.python(
              name='stop_goma (start failure)',
              script=self.goma_ctl,
              args=['stop'], env=self._goma_ctl_env, **kwargs)
          self._upload_logs(name='upload_goma_start_failed_logs')

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

    with self.m.step.nest('postprocess_for_goma'):
      with self.m.step.defer_results():
        self._run_jsonstatus()

        self.m.python(name='goma_stat', script=self.goma_ctl,
                      args=['stat'],
                      env=self._goma_ctl_env, **kwargs)
        self.m.python(name='stop_goma', script=self.goma_ctl,
                      args=['stop'], env=self._goma_ctl_env, **kwargs)
        self._upload_logs(ninja_log_outdir, ninja_log_compiler,
                          ninja_log_command, ninja_log_exit_status)
        self._stop_cloudtail()

      self._goma_started = False
      self._goma_ctl_env = {}

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
        '--gsutil-py-path', self.m.depot_tools.gsutil_py_path,
    ]

    assert self._goma_jsonstatus_called
    args.extend(['--json-status', self.json_path])

    if ninja_log_outdir:
      assert ninja_log_command is not None

      args.extend([
          '--ninja-log-outdir', ninja_log_outdir,
          '--ninja-log-command', str(ninja_log_command)
      ])

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
    for key in ['buildername', 'mastername', 'slavename', 'clobber']:
      if key in self.m.properties:
        args.extend([
            '--buildbot-%s' % key, self.m.properties[key]
        ])

    self.m.python(
      name=name or 'upload_log',
      script=self.package_repo_resource(
          'scripts', 'slave', 'upload_goma_logs.py'),
      args=args)

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
      self.m.step(name or 'compile', ninja_command,
                  env=ninja_env, **kwargs)
      ninja_log_exit_status = 0
    except self.m.step.StepFailure as e:
      ninja_log_exit_status = e.retcode
      raise e
    finally:
      self.stop(ninja_log_outdir=ninja_log_outdir,
                ninja_log_compiler=ninja_log_compiler,
                ninja_log_command=ninja_command,
                ninja_log_exit_status=ninja_log_exit_status)
