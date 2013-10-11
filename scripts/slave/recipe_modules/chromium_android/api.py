# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class AndroidApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(AndroidApi, self).__init__(**kwargs)
    self._env = dict()

  def get_env(self):
    env_dict = dict(self._env)
    env_dict.update(self.c.extra_env)
    env_dict['PATH'] = self.m.path.pathsep.join(filter(bool, (
      str(self.c.build_internal_android),
      self._env.get('PATH',''),
      '%(PATH)s'
    )))
    return env_dict

  def init_and_sync(self):
    internal = self.m.properties['internal']
    bot_id = self.m.properties['android_bot_id']
    target = self.m.properties.get('target', 'Debug')
    repo_name = self.m.properties['repo_name']
    repo_url = self.m.properties['repo_url']
    revision = self.m.properties.get('revision')
    gclient_custom_deps = self.m.properties.get('gclient_custom_deps')

    self.set_config(bot_id,
                    INTERNAL=internal,
                    REPO_NAME=repo_name,
                    REPO_URL=repo_url,
                    BUILD_CONFIG=target)

    # TODO(sivachandra): Move the setting of the gclient spec below to an
    # internal config extension when they are supported by the recipe system.
    spec = self.m.gclient.make_config('android_bare')
    spec.target_os = ['android']
    s = spec.solutions[0]
    s.name = repo_name
    s.url = repo_url
    s.custom_deps = gclient_custom_deps or {}
    if revision:
      s.revision = revision
    else:
      s.revision = 'refs/remotes/origin/master'

    yield self.m.gclient.checkout(spec)

    # TODO(sivachandra): Manufacture gclient spec such that it contains "src"
    # solution + repo_name solution. Then checkout will be automatically
    # correctly set by gclient.checkout
    self.m.path.set_dynamic_path('checkout', self.m.path.slave_build('src'))

    gyp_defs = self.m.chromium.c.gyp_env.GYP_DEFINES

    if internal:
      yield self.m.step(
          'get app_manifest_vars',
          [self.c.internal_dir('build', 'dump_app_manifest_vars.py'),
           '-b', self.m.properties['buildername'],
           '-v', self.m.path.checkout('chrome', 'VERSION'),
           '--output-json', self.m.json.output()]
      )

      app_manifest_vars = self.m.step_history.last_step().json.output
      gyp_defs = self.m.chromium.c.gyp_env.GYP_DEFINES
      gyp_defs['app_manifest_version_code'] = app_manifest_vars['version_code']
      gyp_defs['app_manifest_version_name'] = app_manifest_vars['version_name']
      gyp_defs['chrome_build_id'] = app_manifest_vars['build_id']

  def envsetup(self):
    envsetup_cmd = [self.m.path.checkout('build', 'android', 'envsetup.sh')]
    if self.c.target_arch:
      envsetup_cmd += ['--target-arch=%s' % self.c.target_arch]

    cmd = ([self.m.path.checkout('build', 'env_dump.py'),
            '--output-json', self.m.json.output()] + envsetup_cmd)
    yield self.m.step('envsetup', cmd, env=self.get_env())

    env_diff = self.m.step_history.last_step().json.output
    for key, value in env_diff.iteritems():
      if key.startswith('GYP_'):
        continue
      else:
        self._env[key] = value

  def clean_local_files(self):
    target = self.m.properties.get('target', 'Debug')
    debug_info_dumps = self.m.path.checkout('out', target, 'debug_info_dumps')
    test_logs = self.m.path.checkout('out', target, 'test_logs')
    return self.m.python.inline(
        'clean local files',
        """
          import shutil, sys, os
          shutil.rmtree(sys.argv[1], True)
          shutil.rmtree(sys.argv[2], True)
          for base, _dirs, files in os.walk(sys.argv[3]):
            for f in files:
              if f.endswith('.pyc'):
                os.remove(os.path.join(base, f))
        """,
        args=[debug_info_dumps, test_logs, self.m.path.checkout],
    )

  def run_tree_truth(self):
    # TODO(sivachandra): The downstream ToT builder will require
    # 'Show Revisions' step.
    repos = ['src', 'src-internal']
    if self.c.REPO_NAME not in repos:
      repos.append(self.c.REPO_NAME)
    # TODO(sivachandra): Disable subannottations after cleaning up
    # tree_truth.sh.
    yield self.m.step('tree truth steps',
                      [self.m.path.checkout('build', 'tree_truth.sh'),
                       self.m.path.checkout] + repos,
                      allow_subannotations=False)

  def runhooks(self):
    run_hooks_env = self.get_env()
    if self.m.properties.get('internal'):
      run_hooks_env['EXTRA_LANDMINES_SCRIPT'] = self.c.internal_dir(
        'build', 'get_internal_landmines.py')
    return self.m.chromium.runhooks(env=run_hooks_env)

  def apply_svn_patch(self):
    # TODO(sivachandra): We should probably pull this into its own module
    # (maybe a 'tryserver' module) at some point.
    return self.m.step(
        'apply_patch',
        [self.m.path.build('scripts', 'slave', 'apply_svn_patch.py'),
         '-p', self.m.properties['patch_url'],
         '-r', self.c.internal_dir()])

  def compile(self):
    return self.m.chromium.compile(env=self.get_env())

  def findbugs(self):
    cmd = [self.m.path.checkout('build', 'android', 'findbugs_diff.py')]
    if self.c.INTERNAL:
      cmd.extend(
          ['-b', self.c.internal_dir('bin', 'findbugs_filter'),
           '-o', 'com.google.android.apps.chrome.-,org.chromium.-'])
      yield self.m.step('findbugs internal', cmd, env=self.get_env())

  def checkdeps(self):
    if self.c.INTERNAL:
      yield self.m.step(
        'checkdeps',
        [self.m.path.checkout('tools', 'checkdeps', 'checkdeps.py'),
         '--root=%s' % self.c.internal_dir()],
        env=self.get_env())

  def lint(self):
    if self.c.INTERNAL:
      yield self.m.step(
          'lint',
          [self.c.internal_dir('bin', 'lint.py')],
          env=self.get_env())

  # TODO(sivachandra): Clean this step up after cleaning up the zip_build.py
  # script in scripts/slave. This step should ideally use that script.
  def upload_build(self):
    if self.c.INTERNAL:
      yield self.m.step(
          'upload_build',
          [self.c.internal_dir('build', 'upload_build.py'),
           '-b', self.m.properties['buildername'],
           '-t', self.m.chromium.c.BUILD_CONFIG,
           '-d', self.m.path.checkout('out'),
           '-r', (self.m.properties.get('revision') or
                  self.m.properties.get('buildnumber')),
           '-g', self.m.path.build('scripts', 'slave', 'gsutil')])

  # TODO(sivachandra): Clean this step up after cleaning up the extract_build.py
  # script in scripts/slave. This step should ideally use that script.
  def download_build(self):
    if self.c.INTERNAL:
      yield self.m.step(
          'download_build',
          [self.c.internal_dir('build', 'download_and_extract_build.py'),
           '-b', self.m.properties['parent_buildername'],
           '-d', self.m.path.checkout('out'),
           '-r', (self.m.properties.get('revision') or
                  self.m.properties.get('parent_buildnumber')),
           '-g', self.m.path.build('scripts', 'slave', 'gsutil')])

  def spawn_logcat_monitor(self):
    return self.m.step(
        'spawn_logcat_monitor',
        [self.m.path.build('scripts', 'slave', 'daemonizer.py'),
         '--', self.c.cr_build_android('adb_logcat_monitor.py'),
         self.m.chromium.c.build_dir('logcat')],
        env=self.get_env(), can_fail_build=False)

  def detect_and_setup_devices(self):
    yield self.m.step(
        'provision_devices',
        [self.c.cr_build_android('provision_devices.py'),
         '-t', self.m.chromium.c.BUILD_CONFIG],
        env=self.get_env(), can_fail_build=False)
    yield self.m.step(
        'device_status_check',
        [self.c.cr_build_android('buildbot', 'bb_device_status_check.py')],
        env=self.get_env())

    if self.c.INTERNAL:
      yield self.m.step(
          'setup_devices_for_testing',
          [self.c.internal_dir('build',  'setup_device_testing.py')],
          env=self.get_env(), can_fail_build=False)
      deploy_cmd = [
          self.c.internal_dir('build', 'full_deploy.py'),
          '-v', '--%s' % self.m.chromium.c.BUILD_CONFIG.lower()]
      if self.c.extra_deploy_opts:
        deploy_cmd.extend(self.c.extra_deploy_opts)
      yield self.m.step('deploy_on_devices', deploy_cmd, env=self.get_env())

  def instrumentation_tests(self, official=False):
    dev_status_step = self.m.step_history.get('device_status_check')
    setup_success = dev_status_step and dev_status_step.retcode == 0
    if self.c.INTERNAL:
      deploy_step = self.m.step_history.get('deploy_on_devices')
      setup_success = deploy_step and deploy_step.retcode == 0
    if setup_success:
      for test in self.c.instrumentation_tests:
        annotation = test.annotation
        cmd = [self.c.internal_dir('build', 'run_instrumentation_tests.py'),
               '-a', annotation, '-d', self.m.path.checkout()]
        if test.exclude_annotation:
          cmd.extend(['-e', test.exclude_annotation])
        yield self.m.step(annotation.lower() + '_instrumentation_tests',
                          cmd, env=self.get_env(), always_run=True)

  def logcat_dump(self):
    if self.m.step_history.get('spawn_logcat_monitor'):
      return self.m.step(
          'logcat_dump',
          [self.m.path.checkout('build', 'android', 'adb_logcat_printer.py'),
           self.m.path.checkout('out', 'logcat')], always_run=True)

  def stack_tool_steps(self):
    if self.c.run_stack_tool_steps:
      log_file = self.m.path.checkout('out', self.m.chromium.c.BUILD_CONFIG,
                                      'full_log')
      yield self.m.step(
          'stack_tool_with_logcat_dump',
          [self.m.path.checkout('third_party', 'android_platform', 'development',
                                'scripts', 'stack'),
           '--more-info', log_file], always_run=True)
      yield self.m.step(
          'stack_tool_for_tombstones',
          [self.m.path.checkout('build', 'android', 'tombstones.py'),
           '-a', '-s', '-w'], always_run=True)
      yield self.m.step(
          'stack_tool_for_asan',
          [self.m.path.checkout('build', 'android', 'asan_symbolize.py'),
           '-l', log_file], always_run=True)

  def test_report(self):
    return self.m.python.inline(
        'test_report',
         """
            import glob, os, sys
            for report in glob.glob(sys.argv[1]):
              with open(report, 'r') as f:
                for l in f.readlines():
                  print l
              os.remove(report)
         """,
         args=[self.m.path.checkout('out', self.m.chromium.c.BUILD_CONFIG,
                                    'test_logs', '*.log')],
         always_run=True
    )

  def common_tree_setup_steps(self):
    yield self.init_and_sync()
    yield self.envsetup()
    yield self.clean_local_files()
    if self.c.INTERNAL:
      yield self.run_tree_truth()
    
  def common_tests_setup_steps(self):
    yield self.spawn_logcat_monitor()
    yield self.detect_and_setup_devices()

  def common_tests_final_steps(self):
    yield self.logcat_dump()
    yield self.stack_tool_steps()
    yield self.test_report()
