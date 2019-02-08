# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import os
import re
import sys
import urllib

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

PERF_CONFIG = {'a_default_rev': 'r_webrtc_git'}
DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'


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
  def should_test_android_studio_project_generation(self):
    return self.config.get('test_android_studio_project_generation', False)

  @property
  def should_upload_perf_results(self):
    return bool(self.config.get('perf_id'))


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

  def apply_ios_config(self):
    """Generate a JSON config from bot config, apply it to ios recipe module."""

    # The ios recipe module has only one way of configuring it - by passing a
    # location of a JSON config file. The config covers everything from
    # selecting GN args to running the tests. But we just want the part that
    # runs tests, to be able to reuse the existing compilation code across all
    # platforms. The module has many required parameters with global validation,
    # so some dummy values are needed.
    # It is possible to see the actual JSON files that it generates in
    # ios.expected/*.json step "read build config". They are the direct
    # replacement of the src-side config.

    ios_config = {}

    ios_config['configuration'] = self.m.chromium.c.BUILD_CONFIG
    # Set the bare minimum GN args; these aren't used for building.
    ios_config['gn_args'] = [
      'is_debug=%s' % ('true' if self.m.chromium.c.BUILD_CONFIG != 'Release'
                       else 'false'),
      # HACK: ios recipe module looks for hardcoded values of CPU to determine
      # real device vs simulator but doesn't directly use these values.
      'target_cpu="%s"' % ('arm' if self.m.chromium.c.TARGET_ARCH == 'arm'
                           else 'x64'),
      'use_goma=true',
    ]
    xcode_version = self.m.properties['$depot_tools/osx_sdk']['sdk_version']
    ios_config['xcode build version'] = xcode_version

    ios_config.update(self.bot.config['ios_config'])

    ios_config['tests'] = []
    if self.bot.should_test:
      tests = steps.generate_tests(
          self.m, None, self.revision, self.revision_number, self.bot)
      for test in tests:
        assert isinstance(test, steps.IosTest)
        test_dict = {
          'pool': 'Chrome',
          'priority': 30,
        }
        # Apply generic parameters.
        test_dict.update(self.bot.config.get('ios_testing', {}))
        # Apply test-specific parameters.
        test_dict.update(test.config)
        ios_config['tests'].append(test_dict)

    buildername = sanitize_file_name(self.buildername)
    with self.m.tempfile.temp_dir('ios') as tmp_path:
      self.m.file.ensure_directory(
          'create temp directory',
          tmp_path.join(self.bucketname))
      self.m.file.write_text(
          'generate %s.json' % buildername,
          tmp_path.join(self.bucketname, '%s.json' % buildername),
          self.m.json.dumps(ios_config, indent=2, separators=(',', ': ')))

      # Make it read the actual config even in testing mode.
      if self._test_data.enabled:
        self.m.ios._test_data['build_config'] = ios_config
      self.m.ios.read_build_config(build_config_base_dir=tmp_path,
                                   master_name=self.bucketname,
                                   buildername=buildername)

  @property
  def bucketname(self):
    return self.m.buildbucket.bucket_v1

  @property
  def buildername(self):
    return self.m.buildbucket.builder_name

  @property
  def build_url(self):
    return 'https://ci.chromium.org/p/%s/builders/%s/%s/%s' % (
        urllib.quote(self.m.buildbucket.build.builder.project),
        urllib.quote(self.bucketname),
        urllib.quote(self.buildername),
        urllib.quote(str(self.m.buildbucket.build.number)))

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
    for bot in self.related_bots():
      if 'perf' in bot.test_suite:
        return self.bot.should_build
    return False

  @property
  def should_download_video_quality_tools(self):
    for bot in self.related_bots():
      if 'android_perf' in bot.test_suite:
        return self.bot.should_build
    return False

  def configure_isolate(self, phase=None):
    if self.bot.config.get('isolate_server'):
      self.m.isolate.isolate_server = self.bot.config['isolate_server']

    isolated_targets = set()
    for bot in self.related_bots():
      if bot.should_test:
        for test in steps.generate_tests(
            self.m, phase, self.revision, self.revision_number, bot):
          if isinstance(test, (SwarmingTest, steps.IosTest)):
            isolated_targets.add(test._name)

    self._isolated_targets = sorted(isolated_targets)

    if self.bot.config.get('parent_buildername'):
      self.m.isolate.check_swarm_hashes(self._isolated_targets)

  def configure_swarming(self):
    if self.bot.config.get('swarming_server'):
      self.m.swarming.swarming_server = self.bot.config['swarming_server']

    self.m.chromium_swarming.configure_swarming(
        'webrtc',
        precommit=self.m.tryserver.is_tryserver,
        mastername=self.mastername)
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
    if self.bot.should_test:
      self.m.swarming.check_client_version()

  @contextlib.contextmanager
  def ensure_sdk(self):
    with self.m.osx_sdk(self.bot.config['ensure_sdk']):
      yield

  def run_mb(self, phase=None):
    if phase:
      # Set the out folder to be the same as the phase name, so caches of
      # consecutive builds don't interfere with each other.
      self.m.chromium.c.build_config_fs = sanitize_file_name(phase)
    else:
      # Set the out folder to be the same as the builder name, so the whole
      # 'src' folder can be shared between builder types.
      self.m.chromium.c.build_config_fs = sanitize_file_name(self.buildername)

    if self._isolated_targets:
      self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)

    self.m.chromium.mb_gen(
      self.mastername, self.buildername, phase=phase, use_goma=True,
      mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
      isolated_targets=self._isolated_targets)

  def run_mb_ios(self):
    # Match the out path that ios recipe module uses.
    self.m.chromium.c.build_config_fs = os.path.basename(
        self.m.ios.most_recent_app_dir)
    # TODO(oprypin): Allow configuring the path in ios recipe module and remove
    # this override.

    with self.m.context(env={'FORCE_MAC_TOOLCHAIN': ''}):
      self.m.chromium.mb_gen(
        self.mastername, self.buildername, use_goma=True,
        mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
        # mb isolate is not supported (and not needed) on iOS. The ios recipe
        # module does isolation itself, it basically just includes the .app file
        isolated_targets=None)

  def compile(self, phase=None):
    targets = self._isolated_targets
    if targets:
      targets = ['default'] + targets

    self.m.chromium.compile(targets=targets, use_goma_module=True)

  def isolate(self):
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
          for test in tests:
            test.pre_run(self.m, suffix='')

          # Build + upload archives while waiting for swarming tasks to finish.
          if self.bot.config.get('build_android_archive'):
            self.build_android_archive()
          if self.bot.config.get('archive_apprtc'):
            self.package_apprtcmobile()

          for test in tests:
            test.run(self.m, suffix='')

  def maybe_trigger(self):
    properties = {
      'revision': self.revision,
      'parent_got_revision': self.revision,
      'parent_got_revision_cp': self.revision_cp,
    }

    triggered_bots = list(self.bot.triggered_bots())
    if triggered_bots:
      properties['swarm_hashes'] = self.m.isolate.isolated_tests

      self.m.scheduler.emit_trigger(
          self.m.scheduler.BuildbucketTrigger(properties=properties),
          project='webrtc',
          jobs=[buildername for _, buildername in triggered_bots])

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

  def upload_to_perf_dashboard(self, name, step_result):
    test_succeeded = (step_result.presentation.status == self.m.step.SUCCESS)

    if self._test_data.enabled and test_succeeded:
      step_result.raw_io.output_dir = {
        '0/perftest-output.json': self.test_api.example_chartjson(),
        'logcats': 'foo',
      }
    task_output_dir = step_result.raw_io.output_dir

    results_to_upload = []
    for filepath in sorted(task_output_dir):
      # File names are 'perftest-output.json', 'perftest-output_1.json', ...
      # And 'perf_result.json' for iOS.
      if re.search(r'(perftest-output.*|perf_result)\.json$', filepath):
        perf_results = self.m.json.loads(task_output_dir[filepath])
        if perf_results:
          results_to_upload.append(perf_results)

    if not results_to_upload and test_succeeded: # pragma: no cover
      raise self.m.step.InfraFailure(
          'Cannot find JSON performance data for a test that succeeded.')

    perf_bot_group = 'WebRTCPerf'
    if self.m.runtime.is_experimental:
      perf_bot_group = 'Experimental' + perf_bot_group

    for perf_results in results_to_upload:
      args = [
          '--build-url', self.build_url,
          '--name', name,
          '--perf-id', self.c.PERF_ID,
          '--output-json-file', self.m.json.output(),
          '--results-file', self.m.json.input(perf_results),
          '--results-url', DASHBOARD_UPLOAD_URL,
          '--commit-position', self.revision_number,
          '--got-webrtc-revision', self.revision,
          '--perf-dashboard-machine-group', perf_bot_group,
      ]

      self.m.build.python(
          '%s Dashboard Upload' % name,
          self.resource('upload_perf_dashboard_results.py'),
          args,
          step_test_data=lambda: self.m.json.test_api.output({}),
          infra_step=True)


def sanitize_file_name(name):
  safe_with_spaces = ''.join(c if c.isalnum() else ' ' for c in name)
  return '_'.join(safe_with_spaces.split())
