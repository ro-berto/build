# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

from slave import recipe_api

class AndroidApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(AndroidApi, self).__init__(**kwargs)
    self._env = dict()
    self._internal_names = dict()
    self._cleanup_list = []

  def get_env(self):
    env_dict = dict(self._env)
    internal_path = None
    if self.c is not None:
      env_dict.update(self.c.extra_env)
      internal_path = str(self.c.build_internal_android)
    env_dict['PATH'] = self.m.path.pathsep.join(filter(bool, (
      internal_path,
      self._env.get('PATH',''),
      '%(PATH)s'
    )))
    return env_dict

  def configure_from_properties(self, config_name, **kwargs):
    def set_property(prop, var):
      if prop in self.m.properties:
        if var in kwargs:
          assert kwargs[var] == self.m.properties[prop], (
              "Property/Config conflict: %s=%s but %s=%s", (
                  prop, self.m.properties[prop],
                  var, kwargs[var]))
        kwargs[var] = self.m.properties[prop]

    set_property('target', 'BUILD_CONFIG')
    set_property('internal', 'INTERNAL')
    set_property('repo_name', 'REPO_NAME')
    set_property('repo_url', 'REPO_URL')

    self.set_config(config_name, **kwargs)

  def make_zip_archive(self, step_name, archive_name, files=None,
                       preserve_paths=True, **kwargs):
    """Creates and stores the archive file.

    Args:
      step_name: Name of the step.
      archive_name: Name of the archive file.
      files: List of files. Files can be glob's or file paths. If no files
        are provided, everything in the target directory will be included.
      preserve_paths: If True, files will be stored using the subdolders
        in the archive.
    """
    archive_args = ['--target', self.m.chromium.c.BUILD_CONFIG,
                    '--name', archive_name]
    if files:
      archive_args.extend(['--files', ','.join(files)])
    if not preserve_paths:
      archive_args.append('--ignore-subfolder-names')

    yield self.m.python(
      step_name,
      str(self.m.path['build'].join(
          'scripts', 'slave', 'android', 'archive_build.py')),
      archive_args,
      always_run=True,
      **kwargs
    )

  def unzip_archive(self, step_name, zip_file, **kwargs):
    yield self.m.step(
      step_name,
      ['unzip', '-o', zip_file],
      **kwargs
    )

  def init_and_sync(self):
    # TODO(sivachandra): Move the setting of the gclient spec below to an
    # internal config extension when they are supported by the recipe system.
    spec = self.m.gclient.make_config('android_bare')
    spec.target_os = ['android']
    s = spec.solutions[0]
    s.name = self.c.deps_dir
    s.url = self.c.REPO_URL
    s.custom_deps = self.c.gclient_custom_deps or {}
    s.deps_file = self.c.deps_file
    s.custom_vars = self.c.gclient_custom_vars or {}
    s.managed = self.c.managed
    s.revision = self.m.properties.get('revision') or self.c.revision

    yield self.m.gclient.checkout(spec)

    # TODO(sivachandra): Manufacture gclient spec such that it contains "src"
    # solution + repo_name solution. Then checkout will be automatically
    # correctly set by gclient.checkout
    self.m.path['checkout'] = self.m.path['slave_build'].join('src')

    gyp_defs = self.m.chromium.c.gyp_env.GYP_DEFINES

    if self.c.INTERNAL and self.c.get_app_manifest_vars:
      yield self.m.step(
          'get app_manifest_vars',
          [self.c.internal_dir.join('build', 'dump_app_manifest_vars.py'),
           '-b', self.m.properties['buildername'],
           '-v', self.m.path['checkout'].join('chrome', 'VERSION'),
           '--output-json', self.m.json.output()]
      )

      app_manifest_vars = self.m.step_history.last_step().json.output
      gyp_defs = self.m.chromium.c.gyp_env.GYP_DEFINES
      gyp_defs['app_manifest_version_code'] = app_manifest_vars['version_code']
      gyp_defs['app_manifest_version_name'] = app_manifest_vars['version_name']
      gyp_defs['chrome_build_id'] = app_manifest_vars['build_id']

      yield self.m.step(
          'get_internal_names',
          [self.c.internal_dir.join('build', 'dump_internal_names.py'),
           '--output-json', self.m.json.output()]
      )

      self._internal_names = self.m.step_history.last_step().json.output

  @property
  def version_name(self):
    app_manifest_vars = self.m.step_history['get app_manifest_vars']
    return app_manifest_vars.json.output['version_name']

  def dump_version(self):
    yield self.m.step('Version: %s' % str(self.version_name), ['true'])

  def envsetup(self):
    envsetup_cmd = [self.m.path['checkout'].join('build',
                                                 'android',
                                                 'envsetup.sh')]

    cmd = ([self.m.path['build'].join('scripts', 'slave', 'env_dump.py'),
            '--output-json', self.m.json.output()] + envsetup_cmd)

    def update_self_env(step_result):
      env_diff = step_result.json.output
      for key, value in env_diff.iteritems():
        if key.startswith('GYP_'):
          continue
        else:
          self._env[key] = value

    return self.m.step('envsetup', cmd, env=self.get_env(),
                       followup_fn=update_self_env,
                       step_test_data=self.test_api.envsetup)


  def clean_local_files(self):
    target = self.c.BUILD_CONFIG
    debug_info_dumps = self.m.path['checkout'].join('out',
                                                    target,
                                                    'debug_info_dumps')
    test_logs = self.m.path['checkout'].join('out', target, 'test_logs')
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
        args=[debug_info_dumps, test_logs, self.m.path['checkout']],
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
                      [self.m.path['checkout'].join('build', 'tree_truth.sh'),
                       self.m.path['checkout']] + repos,
                      allow_subannotations=False)

  def runhooks(self, extra_env=None):
    run_hooks_env = self.get_env()
    if self.c.INTERNAL:
      run_hooks_env['EXTRA_LANDMINES_SCRIPT'] = self.c.internal_dir.join(
        'build', 'get_internal_landmines.py')
    if extra_env:
      run_hooks_env.update(extra_env)
    return self.m.chromium.runhooks(env=run_hooks_env)

  def apply_svn_patch(self):
    # TODO(sivachandra): We should probably pull this into its own module
    # (maybe a 'tryserver' module) at some point.
    return self.m.step(
        'apply_patch',
        [self.m.path['build'].join('scripts', 'slave', 'apply_svn_patch.py'),
         '-p', self.m.properties['patch_url'],
         '-r', self.c.internal_dir])

  def compile(self, **kwargs):
    assert 'env' not in kwargs, (
        "chromium_andoid compile clobbers env in keyword arguments")
    kwargs['env'] = self.get_env()
    return self.m.chromium.compile(**kwargs)

  def findbugs(self):
    cmd = [self.m.path['checkout'].join('build', 'android', 'findbugs_diff.py')]
    if self.c.INTERNAL:
      cmd.extend(
          ['-b', self.c.internal_dir.join('bin', 'findbugs_filter'),
           '-o', 'com.google.android.apps.chrome.-,org.chromium.-'])
      yield self.m.step('findbugs internal', cmd, env=self.get_env())

  def checkdeps(self):
    if self.c.INTERNAL:
      yield self.m.step(
        'checkdeps',
        [self.m.path['checkout'].join('tools', 'checkdeps', 'checkdeps.py'),
         '--root=%s' % self.c.internal_dir],
        env=self.get_env())

  def lint(self):
    if self.c.INTERNAL:
      yield self.m.step(
          'lint',
          [self.c.internal_dir.join('bin', 'lint.py')],
          env=self.get_env())

  def git_number(self):
    yield self.m.step(
        'git_number',
        [self.m.path['depot_tools'].join('git_number.py')],
        stdout = self.m.raw_io.output(),
        step_test_data=(
          lambda:
            self.m.raw_io.test_api.stream_output('3000\n')
        ),
        cwd=self.m.path['checkout'])

  def _upload_build(self, bucket, path):
    archive_name = 'build_product.zip'

    zipfile = self.m.path['checkout'].join('out', archive_name)
    self._cleanup_list.append(zipfile)

    yield self.make_zip_archive(
      'zip_build_product',
      archive_name,
      preserve_paths=True,
      cwd=self.m.path['checkout']
    )

    yield self.m.gsutil.upload(
        name='upload_build_product',
        source=zipfile,
        bucket=bucket,
        dest=path,
        use_retry_wrapper=True
    )

  def upload_clusterfuzz(self):
    revision = self.m.properties['revision']
    # When unpacking, ".." will be stripped from the path and the library will
    # end up in ./third_party/llvm-build/...
    files = ['apks/*', 'lib/*.so',
             '../../third_party/llvm-build/Release+Asserts/lib/clang/*/lib/' +
             'linux/libclang_rt.asan-arm-android.so']

    archive_name = 'clusterfuzz.zip'
    zipfile = self.m.path['checkout'].join('out', archive_name)
    self._cleanup_list.append(zipfile)

    yield self.git_number()
    git_number = str.strip(self.m.step_history['git_number'].stdout)

    yield self.make_zip_archive(
      'zip_clusterfuzz',
      archive_name,
      files=files,
      preserve_paths=False,
      cwd=self.m.path['checkout']
    )
    yield self.m.python(
        'git_revisions',
        self.m.path['checkout'].join('clank', 'build',
                                     'clusterfuzz_generate_revision.py'),
        ['--file', git_number],
        always_run=True,
    )
    yield self.m.gsutil.upload(
        name='upload_revision_data',
        source=self.m.path['checkout'].join('out', git_number),
        bucket='%s/revisions' % self.c.storage_bucket,
        dest=git_number,
        use_retry_wrapper=True
    )
    yield self.m.gsutil.upload(
        name='upload_clusterfuzz',
        source=zipfile,
        bucket=self.c.storage_bucket,
        dest='%s%s.zip' % (self.c.upload_dest_prefix, git_number),
        use_retry_wrapper=True
    )

  def upload_build(self):
    assert self.c.storage_bucket, 'upload_build needs storage bucket'
    upload_tag = self.m.properties.get('revision')
    yield self._upload_build(
        bucket=self.c.storage_bucket,
        path='%s%s.zip' % (self.c.upload_dest_prefix, upload_tag))

  def upload_build_for_tester(self):
    return self._upload_build(
        bucket=self._internal_names['BUILD_BUCKET'],
        path='%s/build_product_%s.zip' % (
            self.m.properties['buildername'], self.m.properties['revision']))

  def _download_build(self, bucket, path):
    base_path = path.split('/')[-1]
    zipfile = self.m.path['checkout'].join('out', base_path)
    self._cleanup_list.append(zipfile)
    yield self.m.gsutil.download(
        name='download_build_product',
        bucket=bucket,
        source=path,
        dest=zipfile
    )
    yield self.unzip_archive(
        'unzip_build_product',
        zipfile,
        cwd=self.m.path['checkout'].join('out')
    )

  def download_build(self):
    return self._download_build(
        bucket=self._internal_names['BUILD_BUCKET'],
        path='%s/build_product_%s.zip' % (
            self.m.properties['parent_buildername'],
            self.m.properties['revision']))


  def spawn_logcat_monitor(self):
    return self.m.step(
        'spawn_logcat_monitor',
        [self.m.path['build'].join('scripts', 'slave', 'daemonizer.py'),
         '--', self.c.cr_build_android.join('adb_logcat_monitor.py'),
         self.m.chromium.c.build_dir.join('logcat')],
        env=self.get_env(), can_fail_build=False)

  def device_status_check(self):
    yield self.m.step(
        'device_status_check',
        [self.m.path['checkout'].join('build', 'android', 'buildbot',
                              'bb_device_status_check.py')],
        env=self.get_env())

  def detect_and_setup_devices(self):
    yield self.device_status_check()
    yield self.m.step(
        'provision_devices',
        [self.c.cr_build_android.join('provision_devices.py'),
         '-t', self.m.chromium.c.BUILD_CONFIG],
        env=self.get_env(), can_fail_build=False)

    if self.c.INTERNAL:
      yield self.m.step(
          'setup_devices_for_testing',
          [self.c.internal_dir.join('build',  'setup_device_testing.py')],
          env=self.get_env(), can_fail_build=False)
      deploy_cmd = [
          self.c.internal_dir.join('build', 'full_deploy.py'),
          '-v', '--%s' % self.m.chromium.c.BUILD_CONFIG.lower()]
      if self.c.extra_deploy_opts:
        deploy_cmd.extend(self.c.extra_deploy_opts)
      yield self.m.step('deploy_on_devices', deploy_cmd, env=self.get_env())

  def instrumentation_tests(self):
    dev_status_step = self.m.step_history.get('device_status_check')
    setup_success = dev_status_step and dev_status_step.retcode == 0
    if self.c.INTERNAL:
      deploy_step = self.m.step_history.get('deploy_on_devices')
      setup_success = deploy_step and deploy_step.retcode == 0
    if setup_success:
      install_cmd = [
          self.m.path['checkout'].join('build',
                                       'android',
                                       'adb_install_apk.py'),
          '--apk', 'ChromeTest.apk',
          '--apk_package', 'com.google.android.apps.chrome.tests'
      ]
      # TODO(sivachandra): Add --release option to install_cmd when those
      # testers are added.
      yield self.m.step('install ChromeTest.apk', install_cmd,
                        env=self.get_env(),  always_run=True)
      if self.m.step_history.last_step().retcode == 0:
        args = (['--test=%s' % s for s in self.c.tests] +
                ['--checkout-dir', self.m.path['checkout'],
                 '--target', self.m.chromium.c.BUILD_CONFIG])
        yield self.m.generator_script(
            self.c.internal_dir.join('build', 'buildbot', 'tests_generator.py'),
            *args,
            env=self.get_env()
        )

  def monkey_test(self, **kwargs):
    args = [
        'monkey',
        '-v',
        '--package=%s' % self.c.channel,
        '--event-count=50000'
    ]
    yield self.m.python(
        'Monkey Test',
        str(self.m.path['checkout'].join('build', 'android', 'test_runner.py')),
        args,
        env={'BUILDTYPE': self.c.BUILD_CONFIG},
        always_run=True,
        **kwargs)

  def logcat_dump(self):
    if self.m.step_history.get('spawn_logcat_monitor'):
      return self.m.python(
          'logcat_dump',
          self.m.path['build'].join('scripts', 'slave', 'tee.py'),
          [self.m.chromium.output_dir.join('full_log'),
           '--',
           self.m.path['checkout'].join('build', 'android',
                                        'adb_logcat_printer.py'),
           self.m.path['checkout'].join('out', 'logcat')],
          always_run=True)

  def stack_tool_steps(self):
    if self.c.run_stack_tool_steps:
      log_file = self.m.path['checkout'].join('out',
                                              self.m.chromium.c.BUILD_CONFIG,
                                              'full_log')
      yield self.m.step(
          'stack_tool_with_logcat_dump',
          [self.m.path['checkout'].join('third_party', 'android_platform',
                                'development', 'scripts', 'stack'),
           '--more-info', log_file], always_run=True, env=self.get_env())
      yield self.m.step(
          'stack_tool_for_tombstones',
          [self.m.path['checkout'].join('build', 'android', 'tombstones.py'),
           '-a', '-s', '-w'], always_run=True, env=self.get_env())
      if self.c.asan_symbolize:
        yield self.m.step(
            'stack_tool_for_asan',
            [self.m.path['checkout'].join('build',
                                          'android',
                                          'asan_symbolize.py'),
             '-l', log_file], always_run=True, env=self.get_env())

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
         args=[self.m.path['checkout'].join('out',
                                            self.m.chromium.c.BUILD_CONFIG,
                                            'test_logs',
                                            '*.log')],
         always_run=True
    )

  def cleanup_build(self):
    return self.m.step(
        'cleanup_build',
        ['rm', '-rf'] + self._cleanup_list,
        always_run=True)

  def common_tree_setup_steps(self):
    yield self.init_and_sync()
    yield self.envsetup()
    yield self.clean_local_files()
    if self.c.INTERNAL and self.c.run_tree_truth:
      yield self.run_tree_truth()

  def common_tests_setup_steps(self):
    yield self.spawn_logcat_monitor()
    yield self.detect_and_setup_devices()

  def common_tests_final_steps(self):
    yield self.logcat_dump()
    yield self.stack_tool_steps()
    yield self.test_report()
    yield self.cleanup_build()

  def run_bisect_script(self, extra_src='', path_to_config=''):
    yield self.m.step('prepare bisect perf regression',
        [self.m.path['checkout'].join('tools',
                                      'prepare-bisect-perf-regression.py'),
         '-w', self.m.path['slave_build']])
    args = []
    if extra_src:
      args = args + ['--extra_src', extra_src]
    if path_to_config:
      args = args + ['--path_to_config', path_to_config]
    yield self.m.step('run bisect perf regression',
        [self.m.path['checkout'].join('tools',
                                      'run-bisect-perf-regression.py'),
         '-w', self.m.path['slave_build']] + args)

  def run_test_suite(self, suite, args=[]):
    yield self.m.python(
        str(suite),
        self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
        ['gtest', '-s', suite] + args,
        env={'BUILDTYPE': self.c.BUILD_CONFIG},
        always_run=True)
