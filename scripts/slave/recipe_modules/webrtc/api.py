# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

from recipe_engine import recipe_api

WEBRTC_GS_BUCKET = 'chromium-webrtc'

from . import builders as webrtc_builders
from . import steps

THIS_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(THIS_DIR)))

from chromium_tests.steps import SwarmingTest


CHROMIUM_REPO = 'https://chromium.googlesource.com/chromium/src'
# WebRTC's dependencies on Chromium's subtree mirrors like
# https://chromium.googlesource.com/chromium/src/build.git
CHROMIUM_DEPS = ['base', 'build', 'ios', 'testing', 'third_party', 'tools']


class Bot(object):
  def __init__(self, builders, recipe_configs, bucket, builder):
    self._builders = builders
    self._recipe_configs = recipe_configs
    self.bucket = bucket
    self.builder = builder

  def __repr__(self):  # pragma: no cover
    return '<Bot %s/%s>' % (self.bucket, self.builder)

  @property
  def config(self):
    return self._builders[self.bucket]['builders'][self.builder]

  @property
  def bot_type(self):
    return self.config.get('bot_type', 'builder_tester')

  def triggered_bots(self):
    for builder in self.config.get('triggers', []):
      bucketname, buildername = builder.split('/')
      yield (bucketname, buildername)

  @property
  def recipe_config(self):
    return self._recipe_configs[self.config['recipe_config']]

  @property
  def test_suite(self):
    return self.recipe_config.get('test_suite')

  @property
  def should_build(self):
    return self.bot_type in ('builder', 'builder_tester')

  @property
  def should_test(self):
    return self.bot_type in ('tester', 'builder_tester')

  @property
  def should_upload_build(self):
    return 'buildbot_triggers' in self.config

  @property
  def should_download_build(self):
    return self.config.get('parent_buildername')

  @property
  def should_test_android_studio_project_generation(self):
    return self.config.get('test_android_studio_project_generation', False)



class WebRTCApi(recipe_api.RecipeApi):
  WEBRTC_GS_BUCKET = WEBRTC_GS_BUCKET

  def __init__(self, **kwargs):
    super(WebRTCApi, self).__init__(**kwargs)
    self._env = {}
    self._isolated_targets = None

    # Keep track of working directory (which contains the checkout).
    # None means "default value".
    self._working_dir = None

    self._builders = None
    self._recipe_configs = None
    self.bot = None

    self.revision = ''
    self.revision_cp = ''
    self.revision_number = ''

  BUILDERS = webrtc_builders.BUILDERS
  RECIPE_CONFIGS = webrtc_builders.RECIPE_CONFIGS


  def apply_bot_config(self, builders, recipe_configs):
    self._builders = builders
    self._recipe_configs = recipe_configs

    self.bot = self.get_bot(self.bucketname, self.buildername)

    self.set_config('webrtc', TEST_SUITE=self.bot.test_suite,
                    PERF_ID=self.bot.config.get('perf_id'))

    chromium_kwargs = self.bot.config.get('chromium_config_kwargs', {})
    if self.bot.recipe_config.get('chromium_android_config'):
      self.m.chromium_android.set_config(
          self.bot.recipe_config['chromium_android_config'], **chromium_kwargs)

    self.m.chromium.set_config(self.bot.recipe_config['chromium_config'],
                               **chromium_kwargs)
    gclient_config = self.bot.recipe_config['gclient_config']
    self.m.gclient.set_config(gclient_config)

    # Support applying configs both at the bot and the recipe config level.
    for c in self.bot.config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot.config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in self.bot.recipe_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    if self.m.tryserver.is_tryserver:
      self.m.chromium.apply_config('trybot_flavor')

    if self.bot.config.get('perf_id'):
      assert not self.m.tryserver.is_tryserver
      assert self.m.chromium.c.BUILD_CONFIG == 'Release', (
        'Perf tests should only be run with Release builds.')

  @property
  def bucketname(self):
    if self.m.runtime.is_luci:
      return self.m.buildbucket.bucket_v1
    else:
      return self.m.properties.get('mastername')

  @property
  def buildername(self):
    return self.m.buildbucket.builder_name

  def get_bot(self, bucketname, buildername):
    return Bot(self._builders, self._recipe_configs, bucketname, buildername)

  @property
  def master_config(self):
    return self._builders[self.bucketname].get('settings', {})

  @property
  def mastername(self):
    return self.master_config.get('mastername', self.bucketname)

  def related_bots(self):
    yield self.bot
    for triggered_bot in self.bot.triggered_bots():
      yield self.get_bot(*triggered_bot)

  @property
  def should_download_audio_quality_tools(self):
    if not self.c.enable_swarming:
      return 'perf' in self.bot.test_suite and self.bot.should_test

    for bot in self.related_bots():
      if 'perf' in bot.test_suite:
        return self.bot.should_build
    return False

  @property
  def should_download_video_quality_tools(self):
    if not self.c.enable_swarming:
      return 'android_perf' in self.bot.test_suite and self.bot.should_test

    for bot in self.related_bots():
      if 'android_perf' in bot.test_suite:
        return self.bot.should_build
    return False

  def configure_isolate(self, phase=None):
    if self.c.enable_swarming:
      isolated_targets = set()
      for bot in self.related_bots():
        if bot.should_test:
          for test in steps.generate_tests(
              self.m, phase, self.revision, self.revision_number, bot):
            if isinstance(test, SwarmingTest):
              isolated_targets.add(test._name)

      self._isolated_targets = sorted(isolated_targets)

  def configure_swarming(self):
    self.c.enable_swarming = self.bot.config.get('enable_swarming')
    if self.c.enable_swarming:
      self.m.chromium_swarming.configure_swarming(
          'webrtc',
          precommit=self.m.tryserver.is_tryserver,
          mastername=self.mastername,
          use_go_client=True)
      self.m.swarming.set_default_dimension(
          'os',
          self.m.swarming.prefered_os_dimension(
              self.m.platform.name).split('-', 1)[0])
      for key, value in self.bot.config.get(
          'swarming_dimensions', {}).iteritems():
        self.m.swarming.set_default_dimension(key, value)
      if self.bot.config.get('swarming_timeout'):
        self.m.swarming.default_hard_timeout = self.bot.config[
            'swarming_timeout']
        self.m.swarming.default_io_timeout = self.bot.config['swarming_timeout']

  def _apply_patch(self, repository_url, patch_ref, include_subdirs=()):
    """Applies a patch by downloading the text diff from Gitiles."""
    with self.m.context(cwd=self.m.path['checkout']):
      patch_diff = self.m.gitiles.download_file(
          repository_url, '', patch_ref + '^!',
          step_name='download patch',
          step_test_data=self.test_api.example_patch)

      includes = ['--include=%s/*' % subdir for subdir in include_subdirs]
      try:
        self.m.git('apply', *includes,
                   stdin=self.m.raw_io.input_text(patch_diff),
                   name='apply patch', infra_step=False)
      except recipe_api.StepFailure:  # pragma: no cover
        self.m.step.active_result.presentation.step_text = 'Patch failure'
        self.m.tryserver.set_patch_failure_tryjob_result()
        raise

  def checkout(self, **kwargs):
    if (self.bot and self.bot.bot_type == 'tester' and
        not self.m.properties.get('parent_got_revision')):
      raise self.m.step.InfraFailure(
         'Testers must not be started without providing revision information.')

    self._working_dir = self.m.chromium_checkout.get_checkout_dir({})

    is_chromium = self.m.tryserver.gerrit_change_repo_url == CHROMIUM_REPO

    if is_chromium:
      for subdir in CHROMIUM_DEPS:
        self.m.gclient.c.revisions['src/%s' % subdir] = 'HEAD'

      kwargs.setdefault('patch', False)

    with self.m.context(cwd=self.m.context.cwd or self._working_dir):
      update_step = self.m.bot_update.ensure_checkout(**kwargs)
    assert update_step.json.output['did_run']

    # Whatever step is run right before this line needs to emit got_revision.
    revs = update_step.presentation.properties
    self.revision = revs['got_revision']
    self.revision_cp = revs['got_revision_cp']
    self.revision_number = str(self.m.commit_position.parse_revision(
        self.revision_cp))

    if is_chromium:
      self._apply_patch(self.m.tryserver.gerrit_change_repo_url,
                        self.m.tryserver.gerrit_change_fetch_ref,
                        include_subdirs=CHROMIUM_DEPS)

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

    self.m.chromium.mb_gen(
      self.mastername, self.buildername, phase=phase, use_goma=True,
      mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
      isolated_targets=self._isolated_targets)

  def compile(self, phase=None):
    self.run_mb(phase)

    targets = self._isolated_targets
    if targets:
      targets = ['default'] + targets

    # TODO(oprypin): remove this after migration to swarming is done.
    if self.bot.test_suite == 'android_perf':
      targets = sorted(steps.ANDROID_PERF_TESTS)

    self.m.chromium.compile(targets=targets, use_goma_module=True)

    if self.c.enable_swarming:
      self.m.isolate.isolate_tests(self.m.chromium.output_dir,
                                   targets=self._isolated_targets)

  def get_binary_sizes(self, files=None, base_dir=None):
    if files is None:
      files = self.bot.config.get('binary_size_files')
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
      tests = steps.generate_tests(
          self.m, phase, self.revision, self.revision_number, self.bot)
      with self.m.step.defer_results():
        if tests:
          run_android_device_steps = (not self.c.enable_swarming and
              self.m.chromium.c.TARGET_PLATFORM == 'android')

          if run_android_device_steps:
            self.m.chromium_android.common_tests_setup_steps()

          for test in tests:
            test.pre_run(self.m, suffix='')

          # Build + upload archives while waiting for swarming tasks to finish.
          if self.bot.config.get('build_android_archive'):
            self.build_android_archive()
          if self.bot.config.get('archive_apprtc'):
            self.package_apprtcmobile()

          for test in tests:
            test.run(self.m, suffix='')

          if run_android_device_steps:
            self.m.chromium_android.common_tests_final_steps(
                logcat_gs_bucket=self.master_config.get('build_gs_bucket'),
                force_latest_version=True)

  def maybe_trigger(self):
    properties = {
      'revision': self.revision,
      'parent_got_revision': self.revision,
      'parent_got_revision_cp': self.revision_cp,
    }

    buildbot_triggers = self.bot.config.get('buildbot_triggers')
    if buildbot_triggers:
      self.m.trigger(*[{
        'builder_name': builder_name,
        'properties': properties,
      } for builder_name in buildbot_triggers])

    triggered_bots = list(self.bot.triggered_bots())
    if triggered_bots:
      if self.c.enable_swarming:
        properties['swarm_hashes'] = self.m.isolate.isolated_tests

      self.m.scheduler.emit_trigger(
          self.m.scheduler.BuildbucketTrigger(properties=properties),
          project='webrtc',
          jobs=[buildername for _, buildername in triggered_bots])

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

    if not self.m.tryserver.is_tryserver and not self.m.runtime.is_experimental:
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
    if not self.m.runtime.is_experimental:
      self.m.gsutil.upload(zip_path, WEBRTC_GS_BUCKET, apk_upload_url,
                           args=['-a', 'public-read'], unauthenticated_url=True)

  def extract_build(self):
    if self.c.enable_swarming:
      self.m.isolate.check_swarm_hashes(self._isolated_targets)
      return

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
