# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from slave import recipe_api


# Different types of builds this recipe module can do.
RECIPE_CONFIGS = {
  'chromeos_official': {
    'chromium_config': 'chromium_official',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'chromium': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
  },
  'chromium_blink_merged': {
    'chromium_config': 'chromium',
    'gclient_config': 'blink_merged',
  },
  'chromium_android': {
    'chromium_config': 'android',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
  },
  'chromium_android_clang': {
    'chromium_config': 'android_clang',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
  },
  'chromium_clang': {
    'chromium_config': 'chromium_clang',
    'gclient_config': 'chromium',
  },
  'chromium_linux_asan': {
    'chromium_config': 'chromium_linux_asan',
    'gclient_config': 'chromium',
  },
  'chromium_mac_asan': {
    'chromium_config': 'chromium_mac_asan',
    'gclient_config': 'chromium',
  },
  'chromium_chromiumos_asan': {
    'chromium_config': 'chromium_chromiumos_asan',
    'gclient_config': 'chromium',
  },
  'chromium_chromeos': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chrome_chromeos': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos', 'chrome_internal'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'chromium_chromeos_ozone': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos', 'ozone'],
    'gclient_config': 'chromium',
  },
  'chromium_chromeos_clang': {
    'chromium_config': 'chromium_clang',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chromium_ios_device': {
    'chromium_config': 'chromium_ios_device',
    'gclient_config': 'ios',
  },
  'chromium_ios_ninja': {
    'chromium_config': 'chromium_ios_ninja',
    'gclient_config': 'ios',
  },
  'chromium_ios_simulator': {
    'chromium_config': 'chromium_ios_simulator',
    'gclient_config': 'ios',
  },
  'chromium_msan': {
    'chromium_config': 'chromium_msan',
    'gclient_config': 'chromium',
  },
  'chromium_no_goma': {
    'chromium_config': 'chromium_no_goma',
    'gclient_config': 'chromium',
  },
  'chromium_oilpan': {
    'chromium_config': 'chromium_official',
    'chromium_apply_config': ['oilpan'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'chromium_v8': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'gclient_apply_config': [
      'v8_bleeding_edge_git',
      'chromium_lkcr',
      'show_v8_revision',
    ],
  },
  'chromium_skia': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium_skia',
  },
  'chromium_win_clang': {
    'chromium_config': 'chromium_win_clang',
    'gclient_config': 'chromium',
  },

  'official': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'perf': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'perf',
  }
}


class ChromiumTestsApi(recipe_api.RecipeApi):
  def sync_and_configure_build(self, mastername, buildername,
                               override_bot_type=None,
                               chromium_apply_config=None):
    # Make an independent copy so that we don't overwrite global state
    # with updates made dynamically based on the test specs.
    master_dict = copy.deepcopy(self.m.chromium.builders.get(mastername, {}))

    bot_config = master_dict.get('builders', {}).get(buildername)
    master_config = master_dict.get('settings', {})
    recipe_config_name = bot_config['recipe_config']
    assert recipe_config_name, (
        'Unrecognized builder name %r for master %r.' % (
            buildername, mastername))
    recipe_config = RECIPE_CONFIGS[recipe_config_name]

    self.m.chromium.set_config(
        recipe_config['chromium_config'],
        **bot_config.get('chromium_config_kwargs', {}))
    # Set GYP_DEFINES explicitly because chromium config constructor does
    # not support that.
    self.m.chromium.c.gyp_env.GYP_DEFINES.update(
        bot_config.get('GYP_DEFINES', {}))
    if bot_config.get('use_isolate'):
      self.m.isolate.set_isolate_environment(self.m.chromium.c)
    for c in recipe_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    if chromium_apply_config:
      for c in chromium_apply_config:
        self.m.chromium.apply_config(c)
    self.m.gclient.set_config(
        recipe_config['gclient_config'],
        **bot_config.get('gclient_config_kwargs', {}))
    for c in recipe_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    if 'android_config' in bot_config:
      self.m.chromium_android.set_config(
          bot_config['android_config'],
          **bot_config.get('chromium_config_kwargs', {}))

    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    if bot_config.get('set_component_rev'):
      # If this is a component build and the main revision is e.g. blink,
      # webrtc, or v8, the custom deps revision of this component must be
      # dynamically set to either:
      # (1) the revision of the builder if this is a tester,
      # (2) 'revision' from the waterfall, or
      # (3) 'HEAD' for forced builds with unspecified 'revision'.
      # TODO(machenbach): Use parent_got_cr_revision on testers with component
      # builds to match also the chromium revision from the builder.
      component_rev = self.m.properties.get('revision') or 'HEAD'
      if bot_type == 'tester':
        component_rev = self.m.properties.get(
            'parent_got_revision', component_rev)
      dep = bot_config.get('set_component_rev')
      self.m.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev

    if self.m.platform.is_win:
      self.m.chromium.taskkill()

    # Bot Update re-uses the gclient configs.
    update_step = self.m.bot_update.ensure_checkout(
        patch_root=bot_config.get('patch_root'))
    assert update_step.json.output['did_run']
    # HACK(dnj): Remove after 'crbug.com/398105' has landed
    self.m.chromium.set_build_properties(update_step.json.output['properties'])

    enable_swarming = bot_config.get('enable_swarming')
    if enable_swarming:
      self.m.isolate.set_isolate_environment(self.m.chromium.c)
      self.m.swarming.check_client_version()
      for key, value in bot_config.get('swarming_dimensions', {}).iteritems():
        self.m.swarming.set_default_dimension(key, value)

    if not bot_config.get('disable_runhooks'):
      if self.m.tryserver.is_tryserver:
        try:
          self.m.chromium.runhooks(name='runhooks (with patch)')
        except self.m.step.StepFailure:
          # As part of deapplying patch we call runhooks without the patch.
          self.deapply_patch(update_step)
          raise
      else:
        self.m.chromium.runhooks()

    test_spec_file = bot_config.get('testing', {}).get('test_spec_file',
                                                       '%s.json' % mastername)
    test_spec_path = self.m.path['checkout'].join('testing', 'buildbot',
                                               test_spec_file)
    # TODO(phajdan.jr): Bots should have no generators instead.
    if bot_config.get('disable_tests'):
      test_spec = {}
      scripts_compile_targets = {}
    else:
      test_spec_result = self.m.json.read(
          'read test spec',
          test_spec_path,
          step_test_data=lambda: self.m.json.test_api.output({}))
      test_spec_result.presentation.step_text = 'path: %s' % test_spec_path
      test_spec = test_spec_result.json.output

      scripts_compile_targets = \
          self.m.chromium.get_compile_targets_for_scripts().json.output

    for loop_buildername, builder_dict in master_dict.get(
        'builders', {}).iteritems():
      builder_dict.setdefault('tests', [])
      # TODO(phajdan.jr): Switch everything to scripts generators and simplify.
      for generator in builder_dict.get('test_generators', []):
        builder_dict['tests'] = (
            list(generator(self.m, mastername, loop_buildername, test_spec,
                           enable_swarming=enable_swarming,
                           scripts_compile_targets=scripts_compile_targets)) +
            builder_dict['tests'])

    return update_step, master_dict, test_spec

  def create_test_runner(self, api, tests, suffix=''):
    """Creates a test runner to run a set of tests.

    Args:
      api: API of the calling recipe.
      tests: List of step.Test objects to be run.
      suffix: Suffix to be passed when running the tests.

    Returns:
      A function that can be passed to setup_chromium_tests or run directly.
    """

    def test_runner():
      failed_tests = []

      for t in tests:
        try:
          t.pre_run(api, suffix)
        except api.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)

      for t in tests:
        try:
          t.run(api, suffix)
        except api.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)
          if t.abort_on_failure:
            raise

      for t in tests:
        try:
          t.post_run(api, suffix)
        except api.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)
          if t.abort_on_failure:
            raise

      if failed_tests:
        failed_tests_names = [t.name for t in failed_tests]
        raise self.m.step.StepFailure(
            '%d tests failed: %r' % (len(failed_tests), failed_tests_names))

    return test_runner

  def get_compile_targets_and_tests(
      self, mastername, buildername, master_dict, override_bot_type=None,
      override_tests=None):
    """Returns a tuple: list of compile targets and list of tests.

    The list of tests includes ones on the triggered testers."""

    bot_config = master_dict.get('builders', {}).get(buildername)
    master_config = master_dict.get('settings', {})
    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    tests = bot_config.get('tests', [])
    if override_tests is not None:
      tests = override_tests

    if bot_type not in ['builder', 'builder_tester']:
      return [], []

    compile_targets = set(bot_config.get('compile_targets', []))
    tests_including_triggered = tests[:]
    for loop_buildername, builder_dict in master_dict.get(
        'builders', {}).iteritems():
      if builder_dict.get('parent_buildername') == buildername:
        tests_including_triggered.extend(builder_dict.get('tests', []))

    if bot_config.get('add_tests_as_compile_targets', True):
      for t in tests_including_triggered:
        compile_targets.update(t.compile_targets(self.m))

    return sorted(compile_targets), tests_including_triggered

  def get_build_revision(self, properties, type):
    if type == 'commit_position':
      return self.m.commit_position.parse_revision(
          properties['got_revision_cp'])
    return properties['got_revision']

  def compile(self, mastername, buildername, update_step, master_dict,
              test_spec):
    """Runs compile and related steps for given builder."""
    compile_targets, tests_including_triggered = \
        self.get_compile_targets_and_tests(
            mastername,
            buildername,
            master_dict)
    self.compile_specific_targets(
        mastername, buildername, update_step, master_dict, test_spec,
        compile_targets, tests_including_triggered)

  def compile_specific_targets(
      self, mastername, buildername, update_step, master_dict, test_spec,
      compile_targets, tests_including_triggered, override_bot_type=None,
      disable_isolate=False):
    """Runs compile and related steps for given builder.

    Allows finer-grained control about exact compile targets used."""

    bot_config = master_dict.get('builders', {}).get(buildername)
    master_config = master_dict.get('settings', {})
    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    self.m.chromium.cleanup_temp()
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.clean_local_files()
      self.m.chromium_android.run_tree_truth()

    if bot_type in ['builder', 'builder_tester']:
      isolated_targets = []
      if not disable_isolate:
        isolated_targets = [
          t.isolate_target for t in tests_including_triggered if t.uses_swarming
        ]

      if isolated_targets:
        self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)

      if self.m.tryserver.is_tryserver:
        try:
          self.m.chromium.compile(compile_targets, name='compile (with patch)')
        except self.m.step.StepFailure:
          self.deapply_patch(update_step)
          try:
            self.m.chromium.compile(compile_targets, name='compile (without patch)')

            # TODO(phajdan.jr): Set failed tryjob result after recognizing infra
            # compile failures. We've seen cases of compile with patch failing
            # with build steps getting killed, compile without patch succeeding,
            # and compile with patch succeeding on another attempt with same
            # patch.
          except self.m.step.StepFailure:
            self.m.tryserver.set_transient_failure_tryjob_result()
            raise
          raise
      else:
        self.m.chromium.compile(compile_targets)

      if self.m.chromium.c.TARGET_PLATFORM == 'android':
        self.m.chromium_android.check_webview_licenses()
        if self.m.chromium.c.BUILD_CONFIG == 'Debug':
          self.m.chromium_android.findbugs()

      if isolated_targets:
        self.m.isolate.remove_build_metadata()
        # 'compile' just prepares all information needed for the isolation,
        # and the isolation is a separate step.
        self.m.isolate.isolate_tests(
            self.m.chromium.output_dir,
            targets=list(set(isolated_targets)),
            verbose=True)

    if bot_type == 'builder':
      if (mastername == 'chromium.linux' and
          self.m.chromium.c.TARGET_PLATFORM != 'android'):
        # TODO(samuong): This is restricted to Linux for now until I have more
        # confidence that it is not totally broken.
        self.m.archive.archive_dependencies(
            'archive dependencies',
            self.m.chromium.c.build_config_fs,
            mastername,
            buildername,
            self.m.properties.get('buildnumber'))

      if bot_config.get('cf_archive_build'):
        self.m.archive.clusterfuzz_archive(
            'ClusterFuzz Archive ',
            self.m.chromium.c.build_config_fs,
            gs_bucket=bot_config.get('cf_gs_bucket'),
            cf_archive_name=bot_config.get('cf_archive_name'),
            revision_dir=bot_config.get('cf_revision_dir'),
        )
      else:
        build_revision = self.get_build_revision(
            update_step.presentation.properties,
            bot_config.get('archive_key', 'got_revision'))

        self.m.archive.zip_and_upload_build(
            'package build',
            self.m.chromium.c.build_config_fs,
            build_url=self._build_gs_archive_url(mastername, master_config),
            build_revision=build_revision,
            cros_board=self.m.chromium.c.TARGET_CROS_BOARD,
            # TODO(machenbach): Make asan a configuration switch.
            package_dsym_files=(
                self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan') and
                self.m.chromium.c.HOST_PLATFORM == 'mac'),
        )

  def tests_for_builder(self, mastername, buildername, update_step, master_dict,
                        override_bot_type=None):
    got_revision = update_step.presentation.properties['got_revision']

    bot_config = master_dict.get('builders', {}).get(buildername)
    master_config = master_dict.get('settings', {})

    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    if bot_type == 'tester':
      # Protect against hard to debug mismatches between directory names
      # used to run tests from and extract build to. We've had several cases
      # where a stale build directory was used on a tester, and the extracted
      # build was not used at all, leading to confusion why source code changes
      # are not taking effect.
      #
      # The best way to ensure the old build directory is not used is to
      # remove it.
      self.m.path.rmtree(
        'build directory',
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))
      self.m.archive.download_and_unzip_build(
        'extract build',
        self.m.chromium.c.build_config_fs,
        self.m.archive.legacy_download_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=(None if mastername.startswith('chromium.perf')
           else self.m.properties['mastername'])),
        build_revision=self.m.properties.get(
          'parent_got_revision', got_revision),
        build_archive_url=self.m.properties.get('parent_build_archive_url'),
        )

      if (self.m.chromium.c.TARGET_PLATFORM == 'android' and
          bot_config.get('root_devices')):
        self.m.adb.root_devices()

    tests = bot_config.get('tests', [])

    # TODO(phajdan.jr): bots should just leave tests empty instead of this.
    if bot_config.get('do_not_run_tests'):
      tests = []

    return tests

  def setup_chromium_tests(self, test_runner, mastername=None):
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.common_tests_setup_steps()

    if self.m.platform.is_win:
      self.m.chromium.crash_handler()

    try:
      return test_runner()
    finally:
      if self.m.platform.is_win:
        self.m.chromium.process_dumps()

      if self.m.chromium.c.TARGET_PLATFORM == 'android':
        # TODO(phajdan.jr): Configure logcat GS bucket in cleaner way.
        logcat_gs_bucket = None
        if mastername == 'chromium.linux':
          logcat_gs_bucket = 'chromium-android'
        self.m.chromium_android.common_tests_final_steps(
            logcat_gs_bucket=logcat_gs_bucket)

  def deapply_patch(self, bot_update_step):
    assert self.m.tryserver.is_tryserver

    if self.m.platform.is_win:
      self.m.chromium.taskkill()
    bot_update_json = bot_update_step.json.output
    self.m.gclient.c.revisions['src'] = str(
        bot_update_json['properties']['got_revision'])
    self.m.bot_update.ensure_checkout(
        force=True, patch=False, update_presentation=False)
    try:
      self.m.chromium.runhooks(name='runhooks (without patch)')
    except self.m.step.StepFailure:
      self.m.tryserver.set_transient_failure_tryjob_result()
      raise

  def analyze(self, exes, compile_targets, config_file_name):
    """Runs "analyze" step to determine targets affected by the patch.

    Returns a tuple of:
      - boolean, indicating whether patch requires compile
      - list of matching exes (see filter recipe module)
      - list of targets that need to be compiled (see filter recipe module)"""

    self.m.filter.does_patch_require_compile(
        exes=exes,
        compile_targets=compile_targets,
        additional_name='chromium',
        config_file_name=config_file_name)

    if not self.m.filter.result:
      # Patch does not require compile.
      return False, [], []

    if 'all' in compile_targets:
      compile_targets = self.m.filter.compile_targets
    else:
      compile_targets = list(set(compile_targets) &
                             set(self.m.filter.compile_targets))
    # Always add |matching_exes|. They will be covered by |compile_targets|,
    # but adding |matching_exes| makes determing if conditional tests are
    # necessary easier. For example, if we didn't do this we could end up
    # with chrome_run as a compile_target and not chrome (since chrome_run
    # depends upon chrome). This results in not picking up
    # NaclIntegrationTest as it depends upon chrome not chrome_run.
    compile_targets = list(set(self.m.filter.matching_exes +
                               self.m.filter.compile_targets))

    return True, self.m.filter.matching_exes, compile_targets

  def configure_swarming(self, project_name, precommit):
    """Configures default swarming dimensions and tags.

    Args:
      project_name: Lowercase name of the project, e.g. "blink", "chromium".
      precommit: Boolean flag to indicate whether the tests are running before
          the changes are commited.
    """
    self.m.swarming.set_default_dimension('pool', 'Chrome')
    self.m.swarming.add_default_tag('project:%s' % project_name)
    self.m.swarming.default_idempotent = True

    if precommit:
      self.m.swarming.add_default_tag('purpose:pre-commit')
      requester = self.m.properties.get('requester')
      if requester == 'commit-bot@chromium.org':
        self.m.swarming.default_priority = 30
        self.m.swarming.add_default_tag('purpose:CQ')
        blamelist = self.m.properties.get('blamelist')
        if len(blamelist) == 1:
          requester = blamelist[0]
      else:
        self.m.swarming.default_priority = 50
        self.m.swarming.add_default_tag('purpose:ManualTS')
      self.m.swarming.default_user = requester
    else:
      self.m.swarming.add_default_tag('purpose:post-commit')
      self.m.swarming.add_default_tag('purpose:CI')
      self.m.swarming.default_priority = 25

  # Used to build the Google Storage archive url.
  #
  # We need to special-case the logic for composing the archive url for a couple
  # of masters. That has been moved outside of the compile method.
  #
  # Special-cased masters:
  #   'chromium.perf' or 'chromium.perf.fyi':
  #     exclude the name of the master from the url.
  #   'tryserver.chromium.perf':
  #     return nothing so that the archive url specified in factory_properties
  #     (as set on the master's configuration) is used instead.
  def _build_gs_archive_url(self, mastername, master_config):
    if mastername.startswith('chromium.perf'):
      return self.m.archive.legacy_upload_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=None)
    elif mastername == 'tryserver.chromium.perf':
      return  None
    else:
      return self.m.archive.legacy_upload_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=self.m.properties['mastername'])
