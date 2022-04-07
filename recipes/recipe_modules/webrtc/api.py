# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import six
from six.moves import urllib

from recipe_engine import recipe_api

from . import builders as webrtc_builders
from . import steps

from RECIPE_MODULES.build import chromium

_WEBRTC_GS_BUCKET = 'chromium-webrtc'
_DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'
_PERF_MACHINE_GROUP = 'WebRTCPerf'
_BINARY_SIZE_TARGETS = (
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


def _get_isolated_targets(tests):
  return [t.canonical_name for t in tests or [] if t.runs_on_swarming]


def _get_tests_from_targets_config(targets_config, phase):
  if phase is None:
    return targets_config.all_tests
  if phase == 'rtti_no_sctp':
    return targets_config.all_tests
  return []


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
  BUILDERS_DB = webrtc_builders.BUILDERS_DB
  RECIPE_CONFIGS = webrtc_builders.RECIPE_CONFIGS

  def __init__(self, **kwargs):
    super(WebRTCApi, self).__init__(**kwargs)

    self._builders = None
    self._recipe_configs = None
    self._ios_config = None
    self.bot = None

  def apply_bot_config(self, builders, recipe_configs, builder_config=None):
    self._builders = builders
    self._recipe_configs = recipe_configs

    self.bot = Bot(builders, recipe_configs, self.bucketname, self.buildername)

    self.set_config('webrtc', TEST_SUITE=self.bot.test_suite,
                    PERF_ID=self.bot.config.get('perf_id'))

    if builder_config:
      self.m.chromium_tests.configure_build(builder_config)
    else:
      chromium_kwargs = self.bot.config.get('chromium_config_kwargs', {})
      if self.bot.recipe_config.get('chromium_android_config'):
        self.m.chromium_android.set_config(
            self.bot.recipe_config['chromium_android_config'],
            **chromium_kwargs)

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
  def revision(self):
    return self.m.chromium.build_properties.get('got_revision')

  @property
  def revision_cp(self):
    return self.m.chromium.build_properties.get('got_revision_cp')

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

  def get_tests_and_compile_targets(self, phase, builder_config, update_step):
    """ Returns the tests to run and the targets to compile."""
    tests = []
    for bot in self.related_bots():
      if bot.bot_type in ('tester', 'builder_tester'):
        tests += steps.generate_tests(phase, bot, self.m.tryserver.is_tryserver,
                                      self.m.chromium_tests, self._ios_config)

    if builder_config:
      targets_config = self.m.chromium_tests.create_targets_config(
          builder_config, update_step.presentation.properties)
      # TODO(crbug.com/webrtc/13899): This is temporary code to make sure we're
      # running the same tests while migrating to a .pyl configuration.
      old_tests = set([t.canonical_name for t in tests])
      tests = _get_tests_from_targets_config(targets_config, phase)
      new_tests = set([t.canonical_name for t in tests])
      if (not self._test_data.enabled and
          old_tests != new_tests):  # pragma: no cover
        self.m.step(str(old_tests), cmd=None)
        self.m.step(str(new_tests), cmd=None)
        assert False

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
        return tests, ['webrtc_dashboard_upload']
      return tests, ['all']

    tests_targets, compile_targets = self.m.filter.analyze(
        affected_files,
        test_targets=[t.canonical_name for t in tests],
        additional_compile_targets=['all'],
        mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
        phase=phase)

    # Some trybots are used to calculate the binary size impact of the current
    # CL. These targets should always be built.
    for binary_size_file in self.bot.config.get('binary_size_files', []):
      compile_targets += [
          t for t in _BINARY_SIZE_TARGETS if t in binary_size_file
      ]
    tests = [t for t in tests if t.canonical_name in tests_targets]
    return tests, sorted(set(compile_targets))

  def configure_swarming(self):
    self.m.chromium_swarming.configure_swarming(
        'webrtc',
        precommit=self.m.tryserver.is_tryserver,
        builder_group=self.builder_group,
        path_to_merge_scripts=self.m.path.join(
            self.m.chromium_checkout.checkout_dir, 'src', 'testing',
            'merge_scripts'))
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

  def run_mb(self, phase=None, tests=None):
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
        isolated_targets=_get_isolated_targets(tests))

  def isolate(self, tests):
    if self.bot.bot_type == 'tester':
      # The tests running on a 'tester' bot are isolated by the 'builder'.
      self.m.isolate.check_swarm_hashes(_get_isolated_targets(tests))
    elif self.is_triggering_perf_tests() and not self.m.tryserver.is_tryserver:
      # Set the swarm_hashes name so that it is found by pinpoint.
      commit_position = self.revision_cp.replace('@', '(at)')
      swarm_hashes_property_name = '_'.join(
          ('swarm_hashes', commit_position, 'without_patch'))

      self.m.isolate.isolate_tests(
          self.m.chromium.output_dir,
          targets=_get_isolated_targets(tests),
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
          self.m.chromium.output_dir, targets=_get_isolated_targets(tests))

  def set_upload_build_properties(self):
    experiment_prefix = 'Experimental' if self.m.runtime.is_experimental else ''
    self.m.chromium.set_build_properties({
        'build_page_url': self.build_url,
        'bot': self.c.PERF_ID,
        'dashboard_url': _DASHBOARD_UPLOAD_URL,
        'commit_position': self.revision_number,
        'webrtc_git_hash': self.revision,
        'perf_dashboard_machine_group': experiment_prefix + _PERF_MACHINE_GROUP,
        'outdir': self.m.chromium.output_dir,
    })

  def set_test_command_lines(self, tests):
    if self.bot.bot_type in ('builder', 'builder_tester'):
      return self.m.chromium_tests.set_test_command_lines(tests, suffix='')

    # Tester builders only triggers swarming tests built on 'builder' bots
    # so the swarming command line needs to be retrieved from build
    # parameters.
    swarming_command_lines = _replace_string_in_dict(
        self.m.properties.get('swarming_command_lines'),
        'WILL_BE_ISOLATED_OUTDIR',
        'ISOLATED_OUTDIR',
    )
    # Tester builders run their tests in the parent builder out directory.
    output_dir = str(self.m.chromium.output_dir).replace(
        _sanitize_file_name(self.buildername),
        _sanitize_file_name(self.bot.config.get('parent_buildername')))

    relative_cwd = self.m.path.relpath(output_dir, self.m.path['checkout'])
    for test in tests:
      if test.runs_on_swarming:
        command_line = swarming_command_lines.get(test.name, [])
        if command_line:
          test.raw_cmd = command_line
          test.relative_cwd = relative_cwd

  def get_binary_sizes(self, files, base_dir=None):
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
      args = [
          '--use-goma', '--verbose', '--extra-gn-args',
          'goma_dir=\"%s\"' % goma_dir
      ]
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
      self.m.goma.stop(
          ninja_log_compiler='goma', build_exit_status=build_exit_status)

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
      self.m.gsutil.upload(
          zip_path,
          _WEBRTC_GS_BUCKET,
          apk_upload_url,
          args=['-a', 'public-read'],
          unauthenticated_url=True)

  def run_tests(self, tests):
    if not tests or self.bot.bot_type == 'builder':
      return

    if self.bot.is_running_perf_tests():
      self.set_upload_build_properties()

    self.set_test_command_lines(tests)
    test_runner = self.m.chromium_tests.create_test_runner(
        tests, enable_infra_failure=True)
    return test_runner()

  def trigger_child_builds(self):
    # If the builder is triggered by pinpoint, don't trigger any bots.
    for tag in self.m.buildbucket.build.tags:
      if tag.key == 'pinpoint_job_id':
        return

    triggered_bots = list(self.bot.triggered_bots())
    if triggered_bots:
      # Replace ISOLATED_OUTDIR by WILL_BE_ISOLATED_OUTDIR to prevent
      # the variable to be expanded by the builder instead of the tester.
      swarming_command_lines = _replace_string_in_dict(
          self.m.chromium_tests.find_swarming_command_lines(suffix=''),
          'ISOLATED_OUTDIR',
          'WILL_BE_ISOLATED_OUTDIR',
      )
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
