# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

from recipe_engine import recipe_api

from . import builders
from . import steps

THIS_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(THIS_DIR)))

from chromium_tests.steps import SwarmingTest



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
    return self.should_test and getattr(self.c, 'TEST_SUITE', None) in (
        'android_perf', 'android_perf_swarming', 'desktop_perf_swarming')

  @property
  def should_download_video_quality_tools(self):
    return self.should_test and getattr(self.c, 'TEST_SUITE', None) in (
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

  def configure_isolate(self, phase=None):
    if self.c.enable_swarming:
      tests = steps.generate_tests(self, self.c.TEST_SUITE, phase,
                                   self.revision)
      self._isolated_targets = [test._name for test in tests
                                if isinstance(test, SwarmingTest)]
      self._isolated_targets.sort()

  def configure_swarming(self):
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
      self.m.python('download apprtc',
                    self.m.depot_tools.download_from_google_storage_path,
                    args=['--bucket=chromium-webrtc-resources',
                          '--directory',
                          self.m.path['checkout'].join('rtc_tools', 'testing')])
      self.m.python('download golang',
                    self.m.depot_tools.download_from_google_storage_path,
                    args=['--bucket=chromium-webrtc-resources',
                          '--directory',
                          self.m.path['checkout'].join(
                              'rtc_tools', 'testing', 'golang', 'linux')])


  def check_swarming_version(self):
    if self.c.enable_swarming:
      self.m.swarming.check_client_version()

  @classmethod
  def _sanitize_dir_name(cls, name):
    safe_with_spaces = ''.join(c if c.isalnum() else ' ' for c in name)
    return '_'.join(safe_with_spaces.split())

  def run_mb(self, phase=None):
    if phase:
      # Set the out folder to be the same as the phase name, so caches of
      # consecutive builds don't interfere with each other.
      self.m.chromium.c.build_config_fs = self._sanitize_dir_name(phase)
    elif self.m.runtime.is_luci:
      # Set the out folder to be the same as the builder name, so the whole
      # 'src' folder can be shared between builder types.
      self.m.chromium.c.build_config_fs = (
          self._sanitize_dir_name(self.buildername))

    self.m.chromium.run_mb(
      self.mastername, self.buildername, phase=phase, use_goma=True,
      mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
      isolated_targets=self._isolated_targets)

  def compile(self, phase=None):
    self.run_mb(phase)
    self.m.chromium.compile(use_goma_module=True)

    if self.c.enable_swarming:
      self.m.isolate.remove_build_metadata()
      self.m.isolate.isolate_tests(self.m.chromium.output_dir,
                                   targets=self._isolated_targets)

  def get_binary_sizes(self, files=None, base_dir=None):
    if files is None:
      files = self.bot_config.get('binary_size_files')
    if not files:
      return

    result = self.m.python(
      'get binary sizes',
      self.resource('binary_sizes.py'),
      ['--base-dir', base_dir or self.m.chromium.output_dir,
       '--output', self.m.json.output(),
       '--'] + list(files),
      infra_step=True,
      step_test_data=self.test_api.example_binary_sizes)
    result.presentation.properties['binary_sizes'] = result.json.output

  def runtests(self, phase=None):
    """Add a suite of test steps.

    Args:
      test_suite=The name of the test suite.
    """
    with self.m.context(cwd=self._working_dir):
      tests = steps.generate_tests(self, self.c.TEST_SUITE, phase,
                                   self.revision)
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
    build_exit_status = 1
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
      build_exit_status = step_result.retcode
    except self.m.step.StepFailure as e:
      build_exit_status = e.retcode
      raise e
    finally:
      self.m.goma.stop(ninja_log_compiler='goma',
                       build_exit_status=build_exit_status)

    experimental = '_experimental' if self.m.runtime.is_experimental else ''
    aar_upload_path = 'android_archive/webrtc_android_%s%s.aar' % (
        self.revision_number, experimental)
    if not self.m.tryserver.is_tryserver:
      self.m.gsutil.upload(
          self.m.path['checkout'].join('libwebrtc.aar'),
          'chromium-webrtc',
          aar_upload_path,
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

    experimental = '_experimental' if self.m.runtime.is_experimental else ''
    apk_upload_path = 'client.webrtc/%s/AppRTCMobile_apk_%s%s.zip' % (
        self.buildername, self.revision_number, experimental)
    self.m.gsutil.upload(zip_path, self.WEBRTC_GS_BUCKET, apk_upload_path,
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
    if self.c.enable_swarming:
      self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)

  def clean_test_output(self):
    """Remove all test output in out/, since we have tests leaking files."""
    out_dir = self.m.path['checkout'].join('out')
    self.m.python('clean test output files',
                  script=self.resource('cleanup_files.py'),
                  args=[out_dir],
                  infra_step=True)
