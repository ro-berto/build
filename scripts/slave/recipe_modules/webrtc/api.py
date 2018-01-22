# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from . import builders
from . import steps


class WebRTCApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(WebRTCApi, self).__init__(**kwargs)
    self._env = {}
    self._isolated_targets = None

    # Keep track of working directory (which contains the checkout).
    # None means "default value".
    self._working_dir = None

  BUILDERS = builders.BUILDERS
  RECIPE_CONFIGS = builders.RECIPE_CONFIGS

  NORMAL_TESTS = steps.NORMAL_TESTS
  ANDROID_DEVICE_TESTS = steps.ANDROID_DEVICE_TESTS
  ANDROID_INSTRUMENTATION_TESTS = steps.ANDROID_INSTRUMENTATION_TESTS
  ANDROID_JUNIT_TESTS = steps.ANDROID_JUNIT_TESTS
  PERF_TESTS = steps.PERF_TESTS
  ANDROID_PERF_TESTS = steps.ANDROID_PERF_TESTS

  WEBRTC_GS_BUCKET = 'chromium-webrtc'

  @property
  def should_build(self):
    return self.bot_type in ('builder', 'builder_tester')

  @property
  def should_test(self):
    return self.bot_type in ('tester', 'builder_tester')

  @property
  def should_upload_build(self):
    return self.bot_config.get('triggers')

  @property
  def should_test_android_studio_project_generation(self):
    return self.bot_config.get('test_android_studio_project_generation')

  @property
  def should_download_build(self):
    return self.bot_config.get('parent_buildername')

  @property
  def should_download_audio_quality_tools(self):
    return hasattr(self.c, 'TEST_SUITE') and self.c.TEST_SUITE in (
        'android_perf', 'android_perf_swarming', 'desktop_perf_swarming',
        'webrtc')

  @property
  def should_download_video_quality_tools(self):
    return hasattr(self.c, 'TEST_SUITE') and self.c.TEST_SUITE in (
        'android_perf', 'android_perf_swarming')

  def apply_bot_config(self, builders, recipe_configs):
    self.mastername = self.m.properties.get('mastername')
    self.buildername = self.m.properties.get('buildername')
    master_dict = builders.get(self.mastername, {})
    self.master_config = master_dict.get('settings', {})

    self.bot_config = master_dict.get('builders', {}).get(self.buildername)
    assert self.bot_config, ('Unrecognized builder name "%r" for master "%r".' %
                             (self.buildername, self.mastername))

    self.bot_type = self.bot_config.get('bot_type', 'builder_tester')
    recipe_config_name = self.bot_config['recipe_config']
    self.recipe_config = recipe_configs.get(recipe_config_name)
    assert self.recipe_config, (
        'Cannot find recipe_config "%s" for builder "%r".' %
        (recipe_config_name, self.buildername))

    self.set_config('webrtc', TEST_SUITE=self.recipe_config.get('test_suite'),
                    **self.bot_config.get('webrtc_config_kwargs', {}))

    chromium_kwargs = self.bot_config.get('chromium_config_kwargs', {})
    if self.recipe_config.get('chromium_android_config'):
      self.m.chromium_android.set_config(
          self.recipe_config['chromium_android_config'], **chromium_kwargs)

    self.m.chromium.set_config(self.recipe_config['chromium_config'],
                               **chromium_kwargs)
    gclient_config = self.recipe_config['gclient_config']
    self.m.gclient.set_config(gclient_config)

    # Support applying configs both at the bot and the recipe config level.
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in self.recipe_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    if self.m.tryserver.is_tryserver:
      self.m.chromium.apply_config('trybot_flavor')

    if self.c.PERF_ID:
      assert not self.m.tryserver.is_tryserver
      assert self.m.chromium.c.BUILD_CONFIG == 'Release', (
        'Perf tests should only be run with Release builds.')

  def configure_swarming(self):
    self.c.use_isolate = self.bot_config.get('use_isolate')
    if self.c.use_isolate:
      if self.c.TEST_SUITE == 'webrtc':
        self._isolated_targets = (self.NORMAL_TESTS.keys())
      elif self.c.TEST_SUITE == 'android':
        self._isolated_targets = (self.ANDROID_DEVICE_TESTS.keys() +
                                  self.ANDROID_INSTRUMENTATION_TESTS.keys() +
                                  self.ANDROID_JUNIT_TESTS.keys())
        if self.m.tryserver.is_tryserver:
          self._isolated_targets += ('webrtc_perf_tests',)
      elif self.c.TEST_SUITE == 'desktop_perf_swarming':
        self._isolated_targets = self.PERF_TESTS
      elif self.c.TEST_SUITE == 'android_perf_swarming':
        self._isolated_targets = self.ANDROID_PERF_TESTS
      self._isolated_targets = sorted(self._isolated_targets)
      if not self._isolated_targets: # pragma: no cover
        raise self.m.step.StepFailure('Isolation and swarming are only '
                                      'supported for webrtc and '
                                      'android test suites.')

    self.c.enable_swarming = self.bot_config.get('enable_swarming')
    if self.c.enable_swarming:
      self.m.chromium_swarming.configure_swarming(
          'webrtc',
          precommit=self.m.tryserver.is_tryserver,
          mastername=self.mastername)
      self.m.swarming.set_default_dimension(
          'os',
          self.m.swarming.prefered_os_dimension(
              self.m.platform.name).split('-', 1)[0])
      for key, value in self.bot_config.get(
          'swarming_dimensions', {}).iteritems():
        self.m.swarming.set_default_dimension(key, value)
      if self.bot_config.get('swarming_timeout'):
        self.m.swarming.default_hard_timeout = self.bot_config['swarming_timeout']
        self.m.swarming.default_io_timeout = self.bot_config['swarming_timeout']

  def checkout(self, **kwargs):
    self._working_dir = self.m.chromium_checkout.get_checkout_dir({})

    # Cleanup symlinks if there are any created.
    self.m.python('clean symlinks',
                  script=self.resource('cleanup_symlinks.py'),
                  args=[self._working_dir],
                  infra_step=True)

    with self.m.context(cwd=self.m.context.cwd or self._working_dir):
      update_step = self.m.bot_update.ensure_checkout(**kwargs)
    assert update_step.json.output['did_run']

    # Whatever step is run right before this line needs to emit got_revision.
    revs = update_step.presentation.properties
    self.revision = revs['got_revision']
    self.revision_cp = revs['got_revision_cp']
    self.revision_number = str(self.m.commit_position.parse_revision(
        self.revision_cp))

  def download_audio_quality_tools(self):
    with self.m.depot_tools.on_path():
      self.m.python('download audio quality tools',
                    self.m.path['checkout'].join('tools_webrtc',
                                                 'download_tools.py'),
                    args=[self.m.path['checkout'].join('tools_webrtc',
                                                       'audio_quality')])

  def download_video_quality_tools(self):
    with self.m.depot_tools.on_path():
      self.m.python('download video quality tools',
                    self.m.path['checkout'].join('tools_webrtc',
                                                 'download_tools.py'),
                    args=[self.m.path['checkout'].join(
                        'tools_webrtc', 'video_quality_toolchain', 'linux')])

  def check_swarming_version(self):
    if self.c.enable_swarming:
      self.m.swarming.check_client_version()

  def run_mb(self):
    self.m.chromium.run_mb(
      self.mastername, self.buildername, use_goma=True,
      mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
      isolated_targets=self._isolated_targets)

  def compile(self):
    self.run_mb()
    self.m.chromium.compile(use_goma_module=True)

    if self.c.use_isolate:
      self.m.isolate.remove_build_metadata()
      self.m.isolate.isolate_tests(self.m.chromium.output_dir,
                                   targets=self._isolated_targets)

  def runtests(self):
    """Add a suite of test steps.

    Args:
      test_suite=The name of the test suite.
    """
    with self.m.context(cwd=self._working_dir):
      tests = steps.generate_tests(self, self.c.TEST_SUITE, self.revision)
      with self.m.step.defer_results():
        if tests:
          run_android_device_steps = (not self.c.enable_swarming and
              self.m.chromium.c.TARGET_PLATFORM == 'android')

          if run_android_device_steps:
            self.m.chromium_android.common_tests_setup_steps()

          for test in tests:
            test.pre_run(self.m, suffix='')

          for test in tests:
            test.run(self, suffix='')

          # Build + upload archives while waiting for swarming tasks to finish.
          if self.bot_config.get('build_android_archive'):
            self.build_android_archive()
          if self.bot_config.get('archive_apprtc'):
            self.package_apprtcmobile()

          for test in tests:
            test.post_run(self.m, suffix='')

          if run_android_device_steps:
            self.m.chromium_android.common_tests_final_steps(
                logcat_gs_bucket=self.master_config.get('build_gs_bucket'),
                force_latest_version=True)


  def run_baremetal_test(self, test, name=None, gtest_args=None,
                         args=None, parallel=True):
    steps.BaremetalTest(test, name, gtest_args=gtest_args,
                        args=args, parallel=parallel).run(self, suffix='')

  def maybe_trigger(self):
    triggers = self.bot_config.get('triggers')
    if triggers:
      properties = {
        'revision': self.revision,
        'parent_got_revision': self.revision,
        'parent_got_revision_cp': self.revision_cp,
      }
      self.m.trigger(*[{
        'builder_name': builder_name,
        'properties': properties,
      } for builder_name in triggers])

  def package_build(self):
    upload_url = self.m.archive.legacy_upload_url(
        self.master_config.get('build_gs_bucket'),
        extra_url_components=self.mastername)
    self.m.archive.zip_and_upload_build(
        'package build',
        self.m.chromium.c.build_config_fs,
        upload_url,
        build_revision=self.revision)

  def build_android_archive(self):
    # Build the Android .aar archive and upload it to Google storage (except for
    # trybots). This should only be run on a single bot or the archive will be
    # overwritten (and it's a multi-arch build so one is enough).
    goma_dir = self.m.goma.ensure_goma()
    self.m.goma.start()
    ninja_log_exit_status = 1
    try:
      build_script = self.m.path['checkout'].join('tools_webrtc', 'android',
                                                  'build_aar.py')
      args = ['--use-goma',
              '--verbose',
              '--extra-gn-args', 'goma_dir=\"%s\"' % goma_dir]
      if self.m.tryserver.is_tryserver:
        # To benefit from incremental builds for speed.
        args.append('--build-dir=out/android-archive')

      with self.m.context(cwd=self.m.path['checkout']):
        with self.m.depot_tools.on_path():
          step_result = self.m.python(
              'build android archive',
              build_script,
              args=args,
          )
      ninja_log_exit_status = step_result.retcode
    except self.m.step.StepFailure as e:
      ninja_log_exit_status = e.retcode
      raise e
    finally:
      self.m.goma.stop(ninja_log_compiler='goma',
                       ninja_log_exit_status=ninja_log_exit_status)

    if not self.m.tryserver.is_tryserver:
      self.m.gsutil.upload(
          self.m.path['checkout'].join('libwebrtc.aar'),
          'chromium-webrtc',
          'android_archive/webrtc_android_%s.aar' % self.revision_number,
          args=['-a', 'public-read'],
          unauthenticated_url=True)


  def package_apprtcmobile(self):
    # Zip and upload out/{Debug,Release}/apks/AppRTCMobile.apk
    apk_root = self.m.chromium.c.build_dir.join(
        self.m.chromium.c.build_config_fs, 'apks')
    zip_path = self.m.path['start_dir'].join('AppRTCMobile_apk.zip')

    pkg = self.m.zip.make_package(apk_root, zip_path)
    pkg.add_file(apk_root.join('AppRTCMobile.apk'))
    pkg.zip('AppRTCMobile zip archive')

    apk_upload_url = 'client.webrtc/%s/AppRTCMobile_apk_%s.zip' % (
        self.buildername, self.revision_number)
    self.m.gsutil.upload(zip_path, self.WEBRTC_GS_BUCKET, apk_upload_url,
                         args=['-a', 'public-read'], unauthenticated_url=True)

  def extract_build(self):
    if not self.m.properties.get('parent_got_revision'):
      raise self.m.step.StepFailure(
         'Testers cannot be forced without providing revision information. '
         'Please select a previous build and click [Rebuild] or force a build '
         'for a Builder instead (will trigger new runs for the testers).')

    # Ensure old build directory isn't being used by removing it.
    self.m.file.rmtree(
        'build directory',
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

    download_url = self.m.archive.legacy_download_url(
       self.master_config.get('build_gs_bucket'),
       extra_url_components=self.mastername)
    self.m.archive.download_and_unzip_build(
        'extract build',
        self.m.chromium.c.build_config_fs,
        download_url,
        build_revision=self.revision)

  def cleanup(self):
    self.clean_test_output()
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.clean_local_files(clean_pyc_files=False)
    if self.c.use_isolate:
      self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)

  def clean_test_output(self):
    """Remove all test output in out/, since we have tests leaking files."""
    out_dir = self.m.path['checkout'].join('out')
    self.m.python('clean test output files',
                  script=self.resource('cleanup_files.py'),
                  args=[out_dir],
                  infra_step=True)

  def virtual_webcam_check(self):
    self.m.python('webcam_check', self.resource('ensure_webcam_is_running.py'))
