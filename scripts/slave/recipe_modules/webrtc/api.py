# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze
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

  NORMAL_TESTS = freeze({
    'audio_decoder_unittests': {},
    'common_audio_unittests': {},
    'common_video_unittests': {},
    'modules_tests': {
      'shards': 2,
    },
    'modules_unittests': {
      'shards': 6,
    },
    'peerconnection_unittests': {
      'shards': 4,
    },
    'rtc_media_unittests': {},
    'rtc_pc_unittests': {},
    'rtc_stats_unittests': {},
    'rtc_unittests': {
      'shards': 6,
    },
    'system_wrappers_unittests': {},
    'test_support_unittests': {},
    'tools_unittests': {},
    'video_engine_tests': {
      'shards': 4,
    },
    'voice_engine_unittests': {},
    'webrtc_nonparallel_tests': {
      'parallel': False,
    },
    'xmllite_xmpp_unittests': {},
  })

  ANDROID_DEVICE_TESTS = freeze({
    'audio_decoder_unittests': {},
    'common_audio_unittests': {},
    'common_video_unittests': {},
    'modules_tests': {
      'shards': 2,
    },
    'modules_unittests': {
      'shards': 3,
    },
    'peerconnection_unittests': {
      'shards': 3,
    },
    'rtc_stats_unittests': {},
    'rtc_unittests': {
      'shards': 2,
    },
    'system_wrappers_unittests': {},
    'test_support_unittests': {},
    'tools_unittests': {},
    'video_engine_tests': {},
    'voice_engine_unittests': {},
    'webrtc_nonparallel_tests': {},
  })

  ANDROID_INSTRUMENTATION_TESTS = freeze({
    'AppRTCMobileTest': {},
    'libjingle_peerconnection_android_unittest': {},
  })

  ANDROID_JUNIT_TESTS = freeze({
    'android_junit_tests': {},
  })

  DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'

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
  def should_download_build(self):
    return self.bot_config.get('parent_buildername')

  def apply_bot_config(self, builders, recipe_configs, perf_config=None):
    self.mastername = self.m.properties.get('mastername')
    self.buildername = self.m.properties.get('buildername')
    master_dict = builders.get(self.mastername, {})
    self.master_config = master_dict.get('settings', {})
    perf_config = self.master_config.get('PERF_CONFIG')

    self.bot_config = master_dict.get('builders', {}).get(self.buildername)
    assert self.bot_config, ('Unrecognized builder name "%r" for master "%r".' %
                             (self.buildername, self.mastername))

    self.bot_type = self.bot_config.get('bot_type', 'builder_tester')
    recipe_config_name = self.bot_config['recipe_config']
    self.recipe_config = recipe_configs.get(recipe_config_name)
    assert self.recipe_config, (
        'Cannot find recipe_config "%s" for builder "%r".' %
        (recipe_config_name, self.buildername))

    self.set_config('webrtc', PERF_CONFIG=perf_config,
                    TEST_SUITE=self.recipe_config.get('test_suite'),
                    **self.bot_config.get('webrtc_config_kwargs', {}))

    chromium_kwargs = self.bot_config.get('chromium_config_kwargs', {})
    if self.recipe_config.get('chromium_android_config'):
      self.m.chromium_android.set_config(
          self.recipe_config['chromium_android_config'], **chromium_kwargs)

    self.m.chromium.set_config(self.recipe_config['chromium_config'],
                               **chromium_kwargs)
    self.m.gclient.set_config(self.recipe_config['gclient_config'])

    # Support applying configs both at the bot and the recipe config level.
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in self.recipe_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    if self.m.tryserver.is_tryserver:
      self.m.chromium.apply_config('trybot_flavor')

  def configure_swarming(self):
    self.c.use_isolate = self.bot_config.get('use_isolate')
    self.c.enable_swarming = self.bot_config.get('enable_swarming')
    if self.c.use_isolate:
      self.m.isolate.set_isolate_environment(self.m.chromium.c)
      self._isolated_targets = []
      if self.c.TEST_SUITE == 'webrtc':
        self._isolated_targets += self.NORMAL_TESTS.keys()
      if self.c.TEST_SUITE == 'android_linux':
        self._isolated_targets += self.ANDROID_JUNIT_TESTS.keys()
      if self.c.TEST_SUITE in ('android_device', 'android_linux'):
        self._isolated_targets += (self.ANDROID_DEVICE_TESTS.keys() +
                                   self.ANDROID_INSTRUMENTATION_TESTS.keys())
      self._isolated_targets = sorted(self._isolated_targets)
      if not self._isolated_targets: # pragma: no cover
        raise self.m.step.StepFailure('Isolation and swarming are only '
                                      'supported for webrtc, android_linux and '
                                      'android_device test suites.')

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

  def checkout(self, **kwargs):
    self._working_dir = self.m.chromium_checkout.get_checkout_dir({})
    if self._working_dir:
      kwargs.setdefault('cwd', self._working_dir)

    update_step = self.m.bot_update.ensure_checkout(**kwargs)
    assert update_step.json.output['did_run']

    # Whatever step is run right before this line needs to emit got_revision.
    revs = update_step.presentation.properties
    self.revision = revs['got_revision']
    self.revision_cp = revs['got_revision_cp']
    self.revision_number = str(self.m.commit_position.parse_revision(
        self.revision_cp))

  def check_swarming_version(self):
    if self.c.enable_swarming:
      self.m.swarming.check_client_version()

  def compile(self):
    self.m.chromium.run_mb(
      self.mastername, self.buildername, use_goma=True,
      mb_config_path=self.m.path['checkout'].join('webrtc', 'build',
                                                  'mb_config.pyl'),
      gyp_script=self.m.path['checkout'].join('webrtc', 'build',
                                              'gyp_webrtc.py'),
      isolated_targets=self._isolated_targets)
    # GYP bots no longer compiles, we only want to ensure GYP executes.
    if 'gyp' not in self.buildername.lower():
      self.m.chromium.compile()

    if self.c.use_isolate:
      self.m.isolate.remove_build_metadata()
      self.m.isolate.isolate_tests(self.m.chromium.output_dir,
                                   targets=self._isolated_targets)


  def runtests(self):
    """Add a suite of test steps.

    Args:
      test_suite: The name of the test suite.
    """
    context = {}
    if self._working_dir:
      context['cwd'] = self._working_dir

    with self.m.step.context(context):
      tests = steps.generate_tests(self, self.c.TEST_SUITE, self.revision,
                                   self.c.enable_swarming)
      with self.m.step.defer_results():
        if tests:
          run_android_device_steps = (not self.c.enable_swarming and
              self.m.chromium.c.TARGET_PLATFORM == 'android' and
              self.c.TEST_SUITE != 'android_linux')

          if run_android_device_steps:
            self.m.chromium_android.common_tests_setup_steps()

          for test in tests:
            test.run(self, suffix='')

          if run_android_device_steps:
            self.m.chromium_android.shutdown_device_monitor()
            self.m.chromium_android.logcat_dump(
                gs_bucket=self.master_config.get('build_gs_bucket'))
            self.m.chromium_android.stack_tool_steps(force_latest_version=True)
            self.m.chromium_android.test_report()

      with self.m.step.defer_results():
        for test in tests:
          if test.enable_swarming:
            self.m.swarming.collect_task(test.swarming_task)


  def add_test(self, test, name=None, args=None, revision=None, env=None,
               python_mode=False, perf_test=False, perf_dashboard_id=None,
               parallel=True):
    """Helper function to invoke chromium.runtest().

    Notice that the name parameter should be the same as the test executable in
    order to get the stdio links in the perf dashboard to become correct.
    """
    name = name or test
    args = args or []
    env = env or {}
    if perf_test and self.c.PERF_ID:
      perf_dashboard_id = perf_dashboard_id or test
      assert self.revision_number, (
          'A revision number must be specified for perf tests as they upload '
          'data to the perf dashboard.')
      self.m.chromium.runtest(
          test=test, args=args, name=name,
          results_url=self.DASHBOARD_UPLOAD_URL, annotate='graphing',
          xvfb=True, perf_dashboard_id=perf_dashboard_id,
          test_type=perf_dashboard_id, env=env, python_mode=python_mode,
          revision=self.revision_number, perf_id=self.c.PERF_ID,
          perf_config=self.c.PERF_CONFIG)
    else:
      annotate = 'gtest'
      test_type = test
      flakiness_dash = (not self.m.tryserver.is_tryserver and
                        not self.m.chromium.c.runtests.memory_tool)

      # Dr Memory and Memcheck memory tools uses special scripts that doesn't
      # play well with the gtest-parallel script.
      if parallel and not self.m.chromium.c.runtests.memory_tool:
        test_executable = self.m.chromium.c.build_dir.join(
          self.m.chromium.c.build_config_fs, test)
        args = [test_executable, '--'] + args
        test = self.m.path['checkout'].join('third_party', 'gtest-parallel',
                                            'gtest-parallel')
        python_mode = True
        annotate = None  # The parallel script doesn't output gtest format.
        flakiness_dash = False

      self.m.chromium.runtest(
          test=test, args=args, name=name, annotate=annotate, xvfb=True,
          flakiness_dash=flakiness_dash, python_mode=python_mode,
          revision=revision, test_type=test_type, env=env)

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

    # Zip and upload out/{Debug,Release}/apks/AppRTCMobile.apk
    if self.bot_config.get('archive_apprtc', False):
      apk_root = self.m.chromium.c.build_dir.join(
          self.m.chromium.c.build_config_fs, 'apks')
      zip_path = self.m.path['slave_build'].join('AppRTCMobile_apk.zip')

      pkg = self.m.zip.make_package(apk_root, zip_path)
      pkg.add_file(apk_root.join('AppRTCMobile.apk'))
      pkg.zip('AppRTCMobile zip archive')

      apk_upload_url = 'client.webrtc/%s/AppRTCMobile_apk_%s.zip' % (
          self.buildername, self.revision_number)
      self.m.gsutil.upload(zip_path, 'chromium-webrtc', apk_upload_url,
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
      self.m.chromium_android.clean_local_files()
    else:
      self.m.chromium.cleanup_temp()
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
