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

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import steps as c_steps


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

  def platform_name(self):
    return self.config.get('testing').get('platform')

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
    is_perf_tester = self.should_upload_perf_results and self.should_test
    return (self.bot_type in ('builder', 'builder_tester')) or is_perf_tester

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
    self._isolated_targets = []
    self._non_isolated_targets = []
    self._compile_targets = []

    # Keep track of working directory (which contains the checkout).
    # None means "default value".
    self._working_dir = None

    self._builders = None
    self._recipe_configs = None
    self.bot = None

    self.revision = None
    self.revision_cp = None

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

    # Note: 'xcode build version' property in the json is only informative.
    # It's the depot_tools/osx_sdk recipe module that decides which xcode
    # actually gets installed, and it does so based off $depot_tools/osx_sdk.
    # $depot_tools/osx_sdk is set by our cr-buildbucket.cfg (i.e. config.star).
    xcode_version = self.m.properties['$depot_tools/osx_sdk']['sdk_version']
    ios_config['xcode build version'] = xcode_version

    if 'ios_config' in self.bot.config:
      ios_config.update(self.bot.config['ios_config'])

    ios_config['tests'] = []
    if self.bot.should_test:
      out_dir = self.m.path['checkout'].join('out',
                                             self.m.chromium.c.build_config_fs)
      tests = steps.generate_tests(None, self.bot, self.m.platform.name,
                                   out_dir, self.m.path['checkout'],
                                   self.m.tryserver.is_tryserver)
      for test in tests:
        assert isinstance(test, steps.IosTest)
        test_dict = {
            'pool': 'chromium.tests',
            'priority': 30,
        }
        # Apply generic parameters.
        test_dict.update(self.bot.config.get('ios_testing', {}))
        # Apply test-specific parameters.
        test_dict.update(test.config)
        ios_config['tests'].append(test_dict)

    buildername = sanitize_file_name(self.buildername)
    tmp_path = self.m.path.mkdtemp('ios')
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
    self.m.ios.read_build_config(
        build_config_base_dir=tmp_path,
        builder_group=self.bucketname,
        buildername=buildername)

  @property
  def revision_number(self):
    branch, number = self.m.commit_position.parse(self.revision_cp)
    assert branch.endswith('/master')
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
        urllib.quote(self.m.buildbucket.build.builder.project),
        urllib.quote(self.bucketname),
        urllib.quote(self.buildername),
        urllib.quote(str(self.m.buildbucket.build.number)))

  def get_bot(self, bucketname, buildername):
    return Bot(self._builders, self._recipe_configs, bucketname, buildername)

  @property
  def group_config(self):
    return self._builders[self.bucketname].get('settings', {})

  @property
  def builder_group(self):
    return self.group_config.get('builder_group', self.bucketname)

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

  @property
  def is_triggering_perf_tests(self):
    for triggered_bot in self.bot.triggered_bots():
      if self.get_bot(*triggered_bot).test_suite.endswith('perf_swarming'):
        return self.bot.should_build
    return False

  def is_compile_needed(self, phase=None, is_ios=False):
    test_targets = set()
    non_isolated_test_targets = set()
    for bot in self.related_bots():
      if bot.should_test:
        out_dir = self.m.path['checkout'].join(
            'out', self.m.chromium.c.build_config_fs)
        for test in steps.generate_tests(
            phase=phase,
            bot=bot,
            platform_name=self.m.platform.name,
            build_out_dir=out_dir,
            checkout_path=self.m.path['checkout'],
            is_tryserver=self.m.tryserver.is_tryserver):
          if isinstance(
              test,
              (c_steps.SwarmingTest, steps.WebRtcIsolatedGtest, steps.IosTest)):
            test_targets.add(test.name)
          if isinstance(test, (steps.AndroidJunitTest, steps.PythonTest)):
            non_isolated_test_targets.add(test.name)

    if is_ios:
      # TODO(bugs.webrtc.org/11262): On iOS, the list of isolated targets
      # to run is created in a different way (see webrtc.apply_ios_config()
      # in this file) so we need to keep a copy of test_targets to add
      # back to the list of targets to compile even if "gn analyze" considers
      # them not needed.
      ios_mandatory_test_targets = sorted(test_targets)

    # The default behavior is to always build the :default target and
    # the tests that need to be run.
    # TODO(bugs.webrtc.org/11411): When "all" builds correctly change
    # :default to "all".
    self._isolated_targets = sorted(test_targets)
    self._non_isolated_targets = sorted(non_isolated_test_targets)
    self._compile_targets = [
        'default'
    ] + self._isolated_targets + self._non_isolated_targets

    patch_root = self.m.gclient.get_gerrit_patch_root()
    affected_files = self.m.chromium_checkout.get_files_affected_by_patch(
        relative_to=patch_root, cwd=self.m.path['checkout'])

    # If the main DEPS file has been changed by the current CL, skip the
    # analyze step and build/test everything. This is needed in order to
    # have safe Chromium Rolls since from the GN point of view, a DEPS
    # change doesn't affect anything.
    is_deps_changed = 'DEPS' in affected_files

    # Run gn analyze only on trybots. The CI bots can rebuild everything;
    # they're less time sensitive than trybots.
    if self.m.tryserver.is_tryserver and not is_deps_changed:
      analyze_input = {
          'files': affected_files,
          'test_targets': list(test_targets) + list(non_isolated_test_targets),
          'additional_compile_targets': ['all'],
      }
      if not is_ios:
        step_result = self.m.chromium.mb_analyze(
            self.builder_id,
            analyze_input,
            mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
            phase=phase)
      else:
        # Match the out path that ios recipe module uses.
        self.m.chromium.c.build_config_fs = os.path.basename(
            self.m.ios.most_recent_app_dir)
        with self.m.context(env={'FORCE_MAC_TOOLCHAIN': ''}):
          step_result = self.m.chromium.mb_analyze(
              self.builder_id,
              analyze_input,
              mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'))

      if 'error' in step_result.json.output:
        step_result.presentation.step_text = (
            'Error: ' + step_result.json.output['error'])
        step_result.presentation.status = self.m.step.FAILURE
        raise self.m.step.StepFailure('Error: ' +
                                      step_result.json.output['error'])

      if 'invalid_targets' in step_result.json.output:
        raise self.m.step.StepFailure(
            'Error, following targets were not '
            'found: ' + ', '.join(step_result.json.output['invalid_targets']))

      deps_status = ('Found dependency', 'Found dependency (all)')
      if step_result.json.output['status'] in deps_status:
        self._compile_targets = step_result.json.output['compile_targets']
        self._isolated_targets = [
            t for t in step_result.json.output['test_targets']
            if t in test_targets
        ]
        self._non_isolated_targets = [
            t for t in step_result.json.output['test_targets']
            if t in non_isolated_test_targets
        ]
        # See crbug.com/557505 - we need to not prune meta
        # targets that are part of 'test_targets', because otherwise
        # we might not actually build all of the binaries needed for
        # a given test, even if they aren't affected by the patch.
        self._compile_targets = sorted(
            set(self._compile_targets + self._isolated_targets +
                self._non_isolated_targets))
      else:
        step_result.presentation.step_text = 'No compile necessary'
        self._compile_targets = []
        self._isolated_targets = []
        self._non_isolated_targets = []

    # TODO(bugs.webrtc.org/11262): Some trybots are used to calculate
    # the binary size impact of the current CL. These targets should
    # always be built but we should find a better way to hook this up
    # with the rest of the infrastructure to avoid to update the config
    # in two places.
    if self.buildername in ('android_compile_arm_rel',
                            'android_compile_arm64_rel'):
      self._compile_targets = sorted(
          set(self._compile_targets +
              ['libjingle_peerconnection_so', 'AppRTCMobile']))
    elif self.buildername == 'linux_compile_rel':
      self._compile_targets = sorted(set(self._compile_targets + ['webrtc']))

    if is_ios:
      # TODO(bugs.webrtc.org/11262): On iOS, the list of isolated targets
      # to run is created in a different way (see webrtc.apply_ios_config()
      # in this file) so we have to re-add these targets back even if
      # "gn analyze" considers them not affected by this CL.
      self._compile_targets = sorted(
          set(self._compile_targets + ios_mandatory_test_targets))

    return len(self._compile_targets) > 0

  def configure_isolate(self, phase=None):
    if self.bot.config.get('isolate_server'):
      self.m.isolate.isolate_server = self.bot.config['isolate_server']

    if self.bot.config.get('parent_buildername'):
      self.m.isolate.check_swarm_hashes(self._isolated_targets)

  def configure_swarming(self):
    if self.bot.config.get('swarming_server'):
      self.m.chromium_swarming.swarming_server = self.bot.config[
          'swarming_server']

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
    for key, value in self.bot.config.get(
        'swarming_dimensions', {}).iteritems():
      self.m.chromium_swarming.set_default_dimension(key, value)
    if self.bot.config.get('swarming_timeout'):
      self.m.chromium_swarming.default_hard_timeout = self.bot.config[
          'swarming_timeout']
      self.m.chromium_swarming.default_io_timeout = self.bot.config[
          'swarming_timeout']

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
    self.revision_cp = revs.get('got_revision_cp')

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
      self.m.chromium_swarming.check_client_version()

  @contextlib.contextmanager
  def ensure_sdk(self):
    with self.m.osx_sdk(self.bot.config['ensure_sdk']):
      yield

  def get_mac_toolchain_cmd(self):
    cipd_root = self.m.path['start_dir']
    ensure_file = self.m.cipd.EnsureFile().add_package(
        c_steps.MAC_TOOLCHAIN_PACKAGE, c_steps.MAC_TOOLCHAIN_VERSION)
    self.m.cipd.ensure(cipd_root, ensure_file)
    return cipd_root.join('mac_toolchain')

  def ensure_xcode(self, xcode_build_version):
    # TODO(sergeyberezin): for LUCI migration, this must be a requested named
    # cache. Make sure it exists, to avoid installing Xcode on every build.
    xcode_app_path = self.m.path['cache'].join('xcode_ios_%s.app' %
                                               xcode_build_version)
    with self.m.step.nest('ensure xcode') as step_result:
      step_result.presentation.step_text = (
          'Ensuring Xcode version %s in %s' %
          (xcode_build_version, xcode_app_path))

      mac_toolchain_cmd = self.get_mac_toolchain_cmd()
      install_xcode_cmd = [
          mac_toolchain_cmd,
          'install',
          '-kind',
          'ios',
          '-xcode-version',
          xcode_build_version,
          '-output-dir',
          xcode_app_path,
      ]
      self.m.step('install xcode', install_xcode_cmd, infra_step=True)
      self.m.step(
          'select xcode', ['sudo', 'xcode-select', '-switch', xcode_app_path],
          infra_step=True)

  def run_mb(self, phase=None):
    if phase:
      # Set the out folder to be the same as the phase name, so caches of
      # consecutive builds don't interfere with each other.
      self.m.chromium.c.build_config_fs = sanitize_file_name(phase)
    else:
      # Set the out folder to be the same as the builder name, so the whole
      # 'src' folder can be shared between builder types.
      self.m.chromium.c.build_config_fs = sanitize_file_name(self.buildername)

    self.m.chromium.mb_gen(
        self.builder_id,
        phase=phase,
        use_goma=True,
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
          self.builder_id,
          use_goma=True,
          mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
          # mb isolate is not supported (and not needed) on iOS. The ios recipe
          # module does isolation itself, it basically just includes the .app
          # file
          isolated_targets=None)

  def compile(self, phase=None, override_targets=None):
    del phase
    if override_targets is None:
      targets = self._compile_targets
    else:
      targets = override_targets

    return self.m.chromium.compile(targets=targets, use_goma_module=True)

  def isolate(self):
    if self.is_triggering_perf_tests and not self.m.tryserver.is_tryserver:
      # Set the swarm_hashes name so that it is found by pinpoint.
      commit_position = self.revision_cp.replace('@', '(at)')
      swarm_hashes_property_name = '_'.join(
          ('swarm_hashes', commit_position, 'without_patch'))
      self.m.isolate.isolate_tests(
          self.m.chromium.output_dir,
          targets=self._isolated_targets,
          swarm_hashes_property_name=swarm_hashes_property_name)

      # Upload the isolate file to the pinpoint server.
      self.m.perf_dashboard.upload_isolate(
          self.m.buildbucket.builder_name,
          self.m.perf_dashboard.get_change_info([{
              'repository': 'webrtc',
              'git_hash': self.revision
          }]), self.m.isolate.isolate_server, self.m.isolate.isolated_tests)
    else:
      self.m.isolate.isolate_tests(
          self.m.chromium.output_dir, targets=self._isolated_targets)

  def find_swarming_command_lines(self):
    step_result = self.m.python(
        'find command lines',
        self.m.chromium_tests.resource('find_command_lines.py'), [
            '--build-dir', self.m.chromium.output_dir, '--output-json',
            self.m.json.output()
        ],
        step_test_data=lambda: self.m.json.test_api.output({}))
    assert isinstance(step_result.json.output, dict)
    return step_result.json.output

  def set_swarming_command_lines(self, tests):
    if self.bot.bot_type == 'tester':
      # Tester builders only triggers swarming tests built on 'builder' bots
      # so the swarming command line needs to be retrieved from build
      # parameters.
      raw_command_lines = self.m.properties.get('swarming_command_lines')
      swarming_command_lines = replace_string_in_dict(
          raw_command_lines, 'WILL_BE_ISOLATED_OUTDIR', 'ISOLATED_OUTDIR')
      # Tester builders run their tests in the parent builder out directory.
      output_dir = str(self.m.chromium.output_dir).replace(
          sanitize_file_name(self.buildername),
          sanitize_file_name(self.bot.config.get('parent_buildername')))
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
      out_dir = self.m.path['checkout'].join('out',
                                             self.m.chromium.c.build_config_fs)
      all_tests = steps.generate_tests(phase, self.bot, self.m.platform.name,
                                       out_dir, self.m.path['checkout'],
                                       self.m.tryserver.is_tryserver)
      tests = []
      for t in all_tests:
        if t.name in self._isolated_targets:
          tests.append(t)
        if t.name in self._non_isolated_targets:
          tests.append(t)

      if tests:
        self.set_swarming_command_lines(tests)

        for test in tests:
          test.pre_run(self.m)

        # Build + upload archives while waiting for swarming tasks to finish.
        if self.bot.config.get('build_android_archive'):
          self.build_android_archive()
        if self.bot.config.get('archive_apprtc'):
          self.package_apprtcmobile()

        failures = []
        for test in tests:
          try:
            test.run(self.m)
          except self.m.step.StepFailure:
            failures.append(test.name)

        if failures:
          raise self.m.step.StepFailure('Test target(s) failed: %s' %
                                        ', '.join(failures))


  def maybe_trigger(self):
    # If the builder is triggered by pinpoint, don't run the tests.
    for tag in self.m.buildbucket.build.tags:
      if tag.key == 'pinpoint_job_id':
        return

    triggered_bots = list(self.bot.triggered_bots())
    if triggered_bots:
      properties = {
          'revision': self.revision,
          'parent_got_revision': self.revision,
          'parent_got_revision_cp': self.revision_cp,
      }
      raw_command_lines = self.find_swarming_command_lines()
      # Replace ISOLATED_OUTDIR by WILL_BE_ISOLATED_OUTDIR to prevent
      # the variable to be expanded by the builder instead of the tester.
      properties['swarming_command_lines'] = replace_string_in_dict(
          raw_command_lines, 'ISOLATED_OUTDIR', 'WILL_BE_ISOLATED_OUTDIR')
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
      task_output_dir = {
        'logcats': 'foo',
      }
      task_output_dir['0/perftest-output.pb'] = (self.test_api.example_proto())
    else:
      task_output_dir = step_result.raw_io.output_dir  # pragma no cover

    results_to_upload = []
    for filepath in sorted(task_output_dir):
      # If there are retries, you might see perftest-output_1.pb and so on.
      if re.search(r'perftest-output.*\.pb$', filepath):
        results_to_upload.append(task_output_dir[filepath])

    if not results_to_upload and test_succeeded: # pragma: no cover
      raise self.m.step.InfraFailure(
          'Missing perf output from the test; expected perftest-output(_x).pb '
          'in the isolated-out from the test.')

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
      self.m.python(
          '%s Dashboard Upload' % name,
          upload_script,
          args,
          step_test_data=lambda: self.m.json.test_api.output({}),
          infra_step=True)


def sanitize_file_name(name):
  safe_with_spaces = ''.join(c if c.isalnum() else ' ' for c in name)
  return '_'.join(safe_with_spaces.split())


def replace_string_in_dict(dict_input, old, new):
  dict_output = {}
  for key, values in dict_input.items():
    dict_output[key] = [value.replace(old, new) for value in values]
  return dict_output
