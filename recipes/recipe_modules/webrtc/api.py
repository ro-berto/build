# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import re

import six
from six.moves import urllib

from recipe_engine import recipe_api

WEBRTC_GS_BUCKET = 'chromium-webrtc'

from . import builders as webrtc_builders
from . import steps

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import test_utils
from RECIPE_MODULES.build.chromium_tests import steps as c_steps


CHROMIUM_REPO = 'https://chromium.googlesource.com/chromium/src'
# WebRTC's dependencies on Chromium's subtree mirrors like
# https://chromium.googlesource.com/chromium/src/build.git
CHROMIUM_DEPS = ('base', 'build', 'ios', 'testing', 'third_party', 'tools')

DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'
BINARY_SIZE_TARGETS = (
    'AppRTCMobile',
    'libjingle_peerconnection_so',
    'webrtc',
)


def _sanitize_file_name(name):
  safe_with_spaces = ''.join(c if c.isalnum() else ' ' for c in name)
  return '_'.join(safe_with_spaces.split())


def _replace_string_in_dict(dict_input, old, new):
  dict_output = {}
  for key, values in dict_input.items():
    dict_output[key] = [value.replace(old, new) for value in values]
  return dict_output


class Bot(object):
  def __init__(self, builders, recipe_configs, bucket, builder):
    self._builders = builders
    self._recipe_configs = recipe_configs
    self.bucket = bucket
    self.builder = builder

  @property
  def config(self):
    return self._builders[self.bucket]['builders'][self.builder]

  @property
  def bot_type(self):
    return self.config.get('bot_type', 'builder_tester')

  @property
  def recipe_config(self):
    return self._recipe_configs[self.config['recipe_config']]

  @property
  def test_suite(self):
    return self.recipe_config.get('test_suite')

  @property
  def phases(self):
    return self.config.get('phases', [None])

  def is_running_perf_tests(self):
    return bool(self.config.get('perf_id'))

  def triggered_bots(self):
    for builder in self.config.get('triggers', []):
      bucketname, buildername = builder.split('/')
      yield Bot(self._builders, self._recipe_configs, bucketname, buildername)


class WebRTCApi(recipe_api.RecipeApi):
  BUILDERS = webrtc_builders.BUILDERS
  RECIPE_CONFIGS = webrtc_builders.RECIPE_CONFIGS

  def __init__(self, **kwargs):
    super(WebRTCApi, self).__init__(**kwargs)
    self._isolated_targets = []
    self._non_isolated_targets = []

    # Keep track of working directory (which contains the checkout).
    # None means "default value".
    self._working_dir = None

    self._builders = None
    self._recipe_configs = None
    self._ios_config = None
    self.bot = None

    self.revision = None
    self.revision_cp = None

  def apply_bot_config(self, builders, recipe_configs):
    self._builders = builders
    self._recipe_configs = recipe_configs

    self.bot = Bot(builders, recipe_configs, self.bucketname, self.buildername)

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

    if self.m.properties.get('xcode_build_version'):
      xcode_version = self.m.properties['xcode_build_version']
      args = ['--xcode-build-version', xcode_version]
      named_caches = {'xcode_ios_' + xcode_version: 'Xcode.app'}
      if self.bot.config.get('platform') and self.bot.config.get('version'):
        platform = self.bot.config['platform']
        version = self.bot.config['version']
        args += ['--platform', platform, '--version', version]
        named_caches['runtime_ios_' +
                     _sanitize_file_name(version)] = 'Runtime-ios-' + version
      self._ios_config = {
          'service_account': self.bot.config.get('service_account'),
          'named_caches': named_caches,
          'args': args,
      }

    if self.bot.is_running_perf_tests():
      assert not self.m.tryserver.is_tryserver
      assert self.m.chromium.c.BUILD_CONFIG == 'Release', (
          'Perf tests should only be run with Release builds.')
    if self.bot.bot_type == 'tester':
      assert self.m.properties.get('parent_got_revision'), (
          'Testers should only be run with "parent_got_revision" property.')

  @property
  def revision_number(self):
    branch, number = self.m.commit_position.parse(self.revision_cp)
    assert branch.endswith('/main')
    return number

  @property
  def bucketname(self):
    return self.m.buildbucket.bucket_v1

  @property
  def buildername(self):
    return self.m.buildbucket.builder_name

  @property
  def builder_id(self):
    return chromium.BuilderId.create_for_group(self.builder_group,
                                               self.buildername)

  @property
  def build_url(self):
    return 'https://ci.chromium.org/p/%s/builders/%s/%s/%s' % (
        urllib.parse.quote(self.m.buildbucket.build.builder.project),
        urllib.parse.quote(self.bucketname), urllib.parse.quote(
            self.buildername),
        urllib.parse.quote(str(self.m.buildbucket.build.number)))

  @property
  def builder_group(self):
    group_config = self._builders[self.bucketname].get('settings', {})
    return group_config.get('builder_group', self.bucketname)

  def related_bots(self):
    return [self.bot] + list(self.bot.triggered_bots())

  def should_download_audio_quality_tools(self):
    # Perf test low_bandwidth_audio_perf_test doesn't run on iOS.
    return any(bot.is_running_perf_tests() and 'ios' not in bot.test_suite
               for bot in self.related_bots())

  def should_download_video_quality_tools(self):
    return any(bot.is_running_perf_tests() and 'android' in bot.test_suite
               for bot in self.related_bots())

  def is_triggering_perf_tests(self):
    return any(bot.is_running_perf_tests() for bot in self.bot.triggered_bots())

  def run_mb_analyze(self, phase, affected_files, test_targets):
    step_result = self.m.chromium.mb_analyze(
        self.builder_id,
        analyze_input={
            'files': affected_files,
            'test_targets': sorted(set(test_targets)),
            'additional_compile_targets': ['all'],
        },
        mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
        phase=phase)

    if 'error' in step_result.json.output:
      failure_msg = 'Error: ' + step_result.json.output['error']
      step_result.presentation.step_text = failure_msg
      step_result.presentation.status = self.m.step.FAILURE
      raise self.m.step.StepFailure(failure_msg)

    if 'invalid_targets' in step_result.json.output:
      failure_msg = 'Error, following targets were not found: ' + ', '.join(
          step_result.json.output['invalid_targets'])
      raise self.m.step.StepFailure(failure_msg)

    if 'Found dependency' not in step_result.json.output['status']:
      step_result.presentation.step_text = 'No compile necessary'
      return [], []

    return (step_result.json.output['test_targets'],
            step_result.json.output['compile_targets'])

  def get_compile_targets(self, phase):
    isolated_targets = []
    non_isolated_targets = []
    for bot in self.related_bots():
      if bot.bot_type in ('tester', 'builder_tester'):
        tests = steps.generate_tests(phase, bot, self.m.tryserver.is_tryserver,
                                     self.m.chromium_tests, self._ios_config)
        isolated_targets += [
            t.name for t in tests if isinstance(t, c_steps.SwarmingTest)
        ]
        non_isolated_targets += [
            t.name for t in tests if isinstance(t, c_steps.AndroidJunitTest)
        ]
    self._isolated_targets = sorted(set(isolated_targets))
    self._non_isolated_targets = sorted(set(non_isolated_targets))

    patch_root = self.m.gclient.get_gerrit_patch_root()
    affected_files = self.m.chromium_checkout.get_files_affected_by_patch(
        relative_to=patch_root, cwd=self.m.path['checkout'])

    # If the main DEPS file has been changed by the current CL, skip the
    # analyze step and build/test everything. This is needed in order to
    # have safe Chromium Rolls since from the GN point of view, a DEPS
    # change doesn't affect anything.
    # The CI bots can rebuild everything; they're less time sensitive than
    # trybots.
    if 'DEPS' in affected_files or not self.m.tryserver.is_tryserver:
      # Perf testers are a special case; they only need the catapult protos.
      if self.bot.bot_type == 'tester' and self.bot.is_running_perf_tests():
        return ['webrtc_dashboard_upload']
      return ['all']

    tests_target, compile_targets = self.run_mb_analyze(
        phase, affected_files, isolated_targets + non_isolated_targets)

    self._isolated_targets = [
        t for t in self._isolated_targets if t in tests_target
    ]
    self._non_isolated_targets = [
        t for t in self._non_isolated_targets if t in tests_target
    ]
    if compile_targets:
      # See crbug.com/557505 - we need to not prune meta
      # targets that are part of 'test_targets', because otherwise
      # we might not actually build all of the binaries needed for
      # a given test, even if they aren't affected by the patch.
      compile_targets += self._isolated_targets + self._non_isolated_targets

    # Some trybots are used to calculate the binary size impact of the current
    # CL. These targets should always be built.
    for binary_size_target in BINARY_SIZE_TARGETS:
      for binary_size_file in self.bot.config.get('binary_size_files', []):
        if binary_size_target in binary_size_file:
          compile_targets += [binary_size_target]

    return sorted(set(compile_targets))

  def configure_swarming(self):
    self.m.chromium_swarming.configure_swarming(
        'webrtc',
        precommit=self.m.tryserver.is_tryserver,
        builder_group=self.builder_group,
        path_to_merge_scripts=self.m.path.join(self._working_dir, 'src',
                                               'testing', 'merge_scripts'))
    self.m.chromium_swarming.set_default_dimension(
        'os',
        self.m.chromium_swarming.prefered_os_dimension(
            self.m.platform.name).split('-', 1)[0])
    for key, value in six.iteritems(
        self.bot.config.get('swarming_dimensions', {})):
      self.m.chromium_swarming.set_default_dimension(key, value)
    if self.bot.config.get('swarming_timeout'):
      self.m.chromium_swarming.default_hard_timeout = self.bot.config[
          'swarming_timeout']
      self.m.chromium_swarming.default_io_timeout = self.bot.config[
          'swarming_timeout']
    # Perf tests are marked as not idempotent, which means they're re-run
    # if they did not change this build. This will give the dashboard some
    # more variance data to work with.
    if self.bot.is_running_perf_tests():
      self.m.chromium_swarming.default_idempotent = False

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
    self._working_dir = self.m.chromium_checkout.checkout_dir

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
    self.revision_cp = revs.get('got_revision_cp')

    if is_chromium:
      self._apply_patch(self.m.tryserver.gerrit_change_repo_url,
                        self.m.tryserver.gerrit_change_fetch_ref,
                        include_subdirs=CHROMIUM_DEPS)

  def download_audio_quality_tools(self):
    args = [self.m.path['checkout'].join('tools_webrtc', 'audio_quality')]
    script = self.m.path['checkout'].join('tools_webrtc', 'download_tools.py')
    cmd = ['vpython3', '-u', script] + args

    with self.m.depot_tools.on_path():
      self.m.step('download audio quality tools', cmd)

  def download_video_quality_tools(self):
    with self.m.depot_tools.on_path():
      # Video quality tools
      args_tools = [
          self.m.path['checkout'].join('tools_webrtc',
                                       'video_quality_toolchain', 'linux')
      ]
      script_tools = self.m.path['checkout'].join('tools_webrtc',
                                                  'download_tools.py')
      cmd_tools = ['vpython3', '-u', script_tools] + args_tools
      self.m.step('download video quality tools', cmd_tools)

      # AppRTC
      args_apprtc = [
          '--bucket=chromium-webrtc-resources', '--directory',
          self.m.path['checkout'].join('rtc_tools', 'testing')
      ]
      script_apprtc = self.m.depot_tools.download_from_google_storage_path
      cmd_apprtc = ['vpython3', '-u', script_apprtc] + args_apprtc
      self.m.step('download apprtc', cmd_apprtc)

      # Golang
      args_golang = [
          '--bucket=chromium-webrtc-resources', '--directory',
          self.m.path['checkout'].join('rtc_tools', 'testing', 'golang',
                                       'linux')
      ]
      script_golang = self.m.depot_tools.download_from_google_storage_path
      cmd_golang = ['vpython3', '-u', script_golang] + args_golang
      self.m.step('download golang', cmd_golang)

  def run_mb(self, phase=None):
    if phase:
      # Set the out folder to be the same as the phase name, so caches of
      # consecutive builds don't interfere with each other.
      self.m.chromium.c.build_config_fs = _sanitize_file_name(phase)
    else:
      # Set the out folder to be the same as the builder name, so the whole
      # 'src' folder can be shared between builder types.
      self.m.chromium.c.build_config_fs = _sanitize_file_name(self.buildername)

    self.m.chromium.mb_gen(
        self.builder_id,
        phase=phase,
        use_goma=True,
        mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
        isolated_targets=self._isolated_targets)

  def isolate(self):
    if self.bot.bot_type == 'tester':
      # The tests running on a 'tester' bot are isolated by the 'builder'.
      self.m.isolate.check_swarm_hashes(self._isolated_targets)
    elif self.is_triggering_perf_tests() and not self.m.tryserver.is_tryserver:
      # Set the swarm_hashes name so that it is found by pinpoint.
      commit_position = self.revision_cp.replace('@', '(at)')
      swarm_hashes_property_name = '_'.join(
          ('swarm_hashes', commit_position, 'without_patch'))

      self.m.isolate.isolate_tests(
          self.m.chromium.output_dir,
          targets=self._isolated_targets,
          swarm_hashes_property_name=swarm_hashes_property_name)

      # Upload the input files to the pinpoint server.
      self.m.perf_dashboard.upload_isolate(
          self.m.buildbucket.builder_name,
          self.m.perf_dashboard.get_change_info([{
              'repository': 'webrtc',
              'git_hash': self.revision
          }]), self.m.cas.instance, self.m.isolate.isolated_tests)
    else:
      self.m.isolate.isolate_tests(
          self.m.chromium.output_dir, targets=self._isolated_targets)

  def find_swarming_command_lines(self):
    args = [
        '--build-dir', self.m.chromium.output_dir, '--output-json',
        self.m.json.output()
    ]
    script = self.m.chromium_tests.resource('find_command_lines.py')
    cmd = ['vpython3', '-u', script] + args
    step_result = self.m.step(
        'find command lines',
        cmd,
        step_test_data=lambda: self.m.json.test_api.output({}))
    assert isinstance(step_result.json.output, dict)
    return step_result.json.output

  def set_swarming_command_lines(self, tests):
    if self.bot.bot_type == 'tester':
      # Tester builders only triggers swarming tests built on 'builder' bots
      # so the swarming command line needs to be retrieved from build
      # parameters.
      raw_command_lines = self.m.properties.get('swarming_command_lines')
      swarming_command_lines = _replace_string_in_dict(
          raw_command_lines, 'WILL_BE_ISOLATED_OUTDIR', 'ISOLATED_OUTDIR')
      # Tester builders run their tests in the parent builder out directory.
      output_dir = str(self.m.chromium.output_dir).replace(
          _sanitize_file_name(self.buildername),
          _sanitize_file_name(self.bot.config.get('parent_buildername')))
    else:
      swarming_command_lines = self.find_swarming_command_lines()
      output_dir = self.m.chromium.output_dir

    relative_cwd = self.m.path.relpath(output_dir, self.m.path['checkout'])
    for test in tests:
      if test.runs_on_swarming:
        command_line = swarming_command_lines.get(test.name, [])
        if command_line:
          test.raw_cmd = command_line
          test.relative_cwd = relative_cwd

  def get_binary_sizes(self, files=None, base_dir=None):
    if files is None:
      files = self.bot.config.get('binary_size_files')
    if not files:
      return

    args = [
        '--base-dir', base_dir or self.m.chromium.output_dir, '--output',
        self.m.json.output(), '--'
    ] + list(files)
    cmd = ['vpython3', '-u', self.resource('binary_sizes.py')] + args

    result = self.m.step(
        'get binary sizes',
        cmd,
        infra_step=True,
        step_test_data=self.test_api.example_binary_sizes)
    result.presentation.properties['binary_sizes'] = result.json.output

  def run_perf_tests(self, tests):
    suffix = ''
    group = test_utils.api.SwarmingGroup(tests, self.m.resultdb)
    group.pre_run(self.m, suffix)

    failures = []
    for test in tests:
      group.fetch_rdb_results(test, suffix, self.m.flakiness)
      step_result = test.run(suffix)
      self.upload_to_perf_dashboard(test.name, step_result)

      if not test.has_valid_results(suffix) or test.deterministic_failures(
          suffix):
        failures.append(test.name)

    if failures:
      raise self.m.step.StepFailure('Test target(s) failed: %s' %
                                    ', '.join(failures))

  def runtests(self, phase):
    with self.m.context(cwd=self._working_dir):
      all_tests = steps.generate_tests(phase, self.bot,
                                       self.m.tryserver.is_tryserver,
                                       self.m.chromium_tests, self._ios_config)

      tests = [
          t for t in all_tests
          if t.name in self._isolated_targets + self._non_isolated_targets
      ]
      if not tests:
        return

      self.set_swarming_command_lines(tests)
      if self.bot.config.get('build_android_archive'):
        self.build_android_archive()
      if self.bot.config.get('archive_apprtc'):
        self.package_apprtcmobile()

      if self.bot.is_running_perf_tests():
        return self.run_perf_tests(tests)

      test_runner = self.m.chromium_tests.create_test_runner(tests)
      test_failure_summary = test_runner()
      if test_failure_summary:
        raise self.m.step.StepFailure(test_failure_summary.summary_markdown)

  def trigger_bots(self):
    # If the builder is triggered by pinpoint, don't trigger any bots.
    for tag in self.m.buildbucket.build.tags:
      if tag.key == 'pinpoint_job_id':
        return

    triggered_bots = list(self.bot.triggered_bots())
    if triggered_bots:
      raw_command_lines = self.find_swarming_command_lines()
      # Replace ISOLATED_OUTDIR by WILL_BE_ISOLATED_OUTDIR to prevent
      # the variable to be expanded by the builder instead of the tester.
      swarming_command_lines = _replace_string_in_dict(
          raw_command_lines, 'ISOLATED_OUTDIR', 'WILL_BE_ISOLATED_OUTDIR')
      properties = {
          'revision': self.revision,
          'parent_got_revision': self.revision,
          'parent_got_revision_cp': self.revision_cp,
          'swarming_command_lines': swarming_command_lines,
          'swarm_hashes': self.m.isolate.isolated_tests,
      }
      self.m.scheduler.emit_trigger(
          self.m.scheduler.BuildbucketTrigger(properties=properties),
          project='webrtc',
          jobs=[bot.builder for bot in triggered_bots])

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

      cmd = ['vpython3', '-u', build_script] + args

      with self.m.context(cwd=self.m.path['checkout']):
        with self.m.depot_tools.on_path():
          step_result = self.m.step('build android archive', cmd)
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
      task_output_dir = {'0/perftest-output.pb': 'dummy_data'}
    else:
      task_output_dir = step_result.raw_io.output_dir  # pragma no cover

    results_to_upload = []
    for filepath in sorted(task_output_dir):
      # Both .json and .pb files are accepted even though the file always
      # stores a proto. This is in order to be compatible with Chromium.
      # If there are retries, you might see perftest-output_1.pb and so on.
      if re.search(r'perftest-output.*(\.json|\.pb)$', filepath):
        results_to_upload.append(task_output_dir[filepath])

    if not results_to_upload and test_succeeded: # pragma: no cover
      raise self.m.step.InfraFailure(
          'Missing perf output from the test; expected perftest-output(_x).pb '
          'or perftest-output(_x).json in the isolated-out from the test.')

    perf_bot_group = 'WebRTCPerf'
    if self.m.runtime.is_experimental:
      perf_bot_group = 'Experimental' + perf_bot_group

    for perf_results in results_to_upload:
      args = [
          '--build-page-url', self.build_url, '--test-suite', name, '--bot',
          self.c.PERF_ID, '--output-json-file',
          self.m.json.output(), '--input-results-file',
          self.m.raw_io.input(perf_results), '--dashboard-url',
          DASHBOARD_UPLOAD_URL, '--commit-position', self.revision_number,
          '--webrtc-git-hash', self.revision, '--perf-dashboard-machine-group',
          perf_bot_group, '--outdir', self.m.chromium.output_dir,
          '--wait-for-upload'
      ]

      upload_script = self.m.path['checkout'].join(
          'tools_webrtc', 'perf', 'webrtc_dashboard_upload.py')
      cmd = ['vpython3', '-u', upload_script] + args
      self.m.step(
          '%s Dashboard upload' % name,
          cmd,
          step_test_data=lambda: self.m.json.test_api.output({}),
          infra_step=True)
