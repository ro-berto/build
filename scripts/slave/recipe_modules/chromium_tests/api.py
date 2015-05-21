# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import copy
import json

from infra.libs.infra_types import freeze, thaw
from slave import recipe_api
from slave import recipe_util


class ChromiumTestsApi(recipe_api.RecipeApi):
  def configure_build(self, mastername, buildername, override_bot_type=None,
                      chromium_apply_config=None):
    master_dict = self.m.chromium.builders.get(mastername, {})
    bot_config = master_dict.get('builders', {}).get(buildername)

    # Get the buildspec version. It can be supplied as a build property or as
    # a recipe config value.
    buildspec_version = (self.m.properties.get('buildspec_version') or
                         bot_config.get('buildspec_version'))

    self.m.chromium.set_config(
        bot_config.get('chromium_config'),
        **bot_config.get('chromium_config_kwargs', {}))
    # Set GYP_DEFINES explicitly because chromium config constructor does
    # not support that.
    self.m.chromium.c.gyp_env.GYP_DEFINES.update(
        bot_config.get('GYP_DEFINES', {}))
    if bot_config.get('use_isolate'):
      self.m.isolate.set_isolate_environment(self.m.chromium.c)
    for c in bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    if chromium_apply_config:
      for c in chromium_apply_config:
        self.m.chromium.apply_config(c)

    self.m.gclient.set_config(
        bot_config.get('gclient_config'),
        PATCH_PROJECT=self.m.properties.get('patch_project'),
        BUILDSPEC_VERSION=buildspec_version,
        **bot_config.get('gclient_config_kwargs', {}))
    for c in bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    if bot_config.get('goma_canary'):
      self.m.goma.update_goma_canary()

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

  def prepare_checkout(self, mastername, buildername):
    # Make an independent copy so that we don't overwrite global state
    # with updates made dynamically based on the test specs.
    master_dict = thaw(self.m.chromium.builders.get(mastername, {}))
    bot_config = master_dict.get('builders', {}).get(buildername)

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

    # TODO(phajdan.jr): Bots should have no generators instead.
    if bot_config.get('disable_tests'):
      test_spec = {}
      scripts_compile_targets = {}
    else:
      test_spec = self.read_test_spec(self.m, test_spec_file)
      test_spec_path = self.m.path['checkout'].join('testing', 'buildbot',
                                                 test_spec_file)

      scripts_compile_targets = \
          self.m.chromium.get_compile_targets_for_scripts().json.output

    for loop_buildername, builder_dict in master_dict.get(
        'builders', {}).iteritems():
      builder_dict['tests'] = self.generate_tests_from_test_spec(
          self.m, test_spec, builder_dict,
          loop_buildername, mastername, enable_swarming,
          scripts_compile_targets, builder_dict.get('test_generators', []))

    if self.m.chromium.c.lto:
      self.m.chromium.download_lto_plugin()

    return update_step, freeze(master_dict), test_spec

  def generate_tests_from_test_spec(self, api, test_spec, builder_dict,
      buildername, mastername, enable_swarming, scripts_compile_targets,
      generators):
    tests = builder_dict.get('tests', [])
    # TODO(phajdan.jr): Switch everything to scripts generators and simplify.
    for generator in generators:
      tests = (
          list(generator(api, mastername, buildername, test_spec,
                         enable_swarming=enable_swarming,
                         scripts_compile_targets=scripts_compile_targets)) +
          tests)
    return tests

  def read_test_spec(self, api, test_spec_file):
    test_spec_path = api.path['checkout'].join('testing', 'buildbot',
                                               test_spec_file)
    test_spec_result = api.json.read(
        'read test spec',
        test_spec_path,
        step_test_data=lambda: api.json.test_api.output({}))
    test_spec_result.presentation.step_text = 'path: %s' % test_spec_path
    test_spec = test_spec_result.json.output

    return test_spec

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
        except api.step.InfraFailure:  # pragma: no cover
          raise
        except api.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)

      for t in tests:
        try:
          t.run(api, suffix)
        except api.step.InfraFailure:  # pragma: no cover
          raise
        except api.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)
          if t.abort_on_failure:
            raise

      for t in tests:
        try:
          t.post_run(api, suffix)
        except api.step.InfraFailure:  # pragma: no cover
          raise
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
    tests_including_triggered = list(tests)
    for loop_buildername, builder_dict in master_dict.get(
        'builders', {}).iteritems():
      if builder_dict.get('parent_buildername') == buildername:
        tests_including_triggered.extend(builder_dict.get('tests', []))

    if bot_config.get('add_tests_as_compile_targets', True):
      for t in tests_including_triggered:
        compile_targets.update(t.compile_targets(self.m))

    # Only add crash_service when we have explicit compile targets.
    if self.m.platform.is_win and compile_targets:
      compile_targets.add('crash_service')

    return sorted(compile_targets), tests_including_triggered

  def transient_check(self, update_step, command):
    """Runs command, checking for transience if this is a try job.

    * command is a function which takes an argument of type (str -> str),
      which is a test name transformation (it adds "with patch" or "without
      patch") and runs the command.
    * update_step is the bot_update step used for deapplying the patch.
    """
    if self.m.tryserver.is_tryserver:
      try:
        command(lambda name: '%s (with patch)' % name)
      except self.m.step.StepFailure:
        self.deapply_patch(update_step)
        try:
          command(lambda name: '%s (without patch)' % name)
        except self.m.step.StepFailure:
          self.m.tryserver.set_transient_failure_tryjob_result()
          raise
        raise
    else:
      command(lambda name: name)


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
      compile_targets, tests_including_triggered, override_bot_type=None):
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
      isolated_targets = [
        t.isolate_target for t in tests_including_triggered if t.uses_swarming
      ]

      if isolated_targets:
        self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)

      self.transient_check(update_step, lambda transform_name:
        self.m.chromium.compile(compile_targets,
                                name=transform_name('compile')))

      if isolated_targets:
        self.m.isolate.remove_build_metadata()
        # 'compile' just prepares all information needed for the isolation,
        # and the isolation is a separate step.
        self.m.isolate.isolate_tests(
            self.m.chromium.output_dir,
            targets=list(set(isolated_targets)),
            verbose=True,
            set_swarm_hashes=False)

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
            build_dir=self.m.chromium.c.build_dir.join(
                self.m.chromium.c.build_config_fs),
            update_properties=update_step.presentation.properties,
            gs_bucket=bot_config.get('cf_gs_bucket'),
            gs_acl=bot_config.get('cf_gs_acl'),
            archive_prefix=bot_config.get('cf_archive_name'),
            revision_dir=bot_config.get('cf_revision_dir'),
        )
      else:
        build_revision = update_step.presentation.properties['got_revision']
        self.m.archive.zip_and_upload_build(
            'package build',
            self.m.chromium.c.build_config_fs,
            build_url=self._build_gs_archive_url(
                mastername, master_config, buildername),
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
      self.m.file.rmtree(
        'build directory',
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

      # Do not attempt to compose an archive URL if one is given.
      specified_url = self.m.properties.get('parent_build_archive_url')
      if specified_url:
        legacy_build_url = None
      else:
        legacy_build_url = self._make_legacy_build_url(master_config,
                                                       mastername)

      self.m.archive.download_and_unzip_build(
        step_name='extract build',
        target=self.m.chromium.c.build_config_fs,
        build_url=legacy_build_url,
        build_revision=self.m.properties.get('parent_got_revision',
                                             got_revision),
        build_archive_url=specified_url)

      if (self.m.chromium.c.TARGET_PLATFORM == 'android' and
          bot_config.get('root_devices')):
        self.m.adb.root_devices()

    # TODO(shinyak): bot_config.get('tests', []) sometimes return tuple.
    tests = list(bot_config.get('tests', []))

    if bot_config.get('goma_canary'):
      tests.insert(0, self.m.chromium.steps.DiagnoseGomaTest())

    if bot_type in ('tester', 'builder_tester'):
      isolated_targets = [t.isolate_target for t in tests if t.uses_swarming]
      if isolated_targets:
        self.m.isolate.find_isolated_tests(self.m.chromium.output_dir)

    return tests

  def _make_legacy_build_url(self, master_config, mastername):
    return self.m.archive.legacy_download_url(
               master_config.get('build_gs_bucket'),
               extra_url_components=(
                   None if mastername.startswith('chromium.perf')
                   else self.m.properties['mastername']))

  @contextlib.contextmanager
  def wrap_chromium_tests(self, mastername):
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.common_tests_setup_steps(
          perf_setup=mastername.startswith('chromium.perf'))

    if self.m.platform.is_win:
      self.m.chromium.crash_handler()

    try:
      yield
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

  def run_tests_and_deapply_as_needed(self, mastername, api, tests,
                                      bot_update_step):
    def deapply_patch_fn(failing_tests):
      self.deapply_patch(bot_update_step)
      compile_targets = list(self.m.itertools.chain(
          *[t.compile_targets(api) for t in failing_tests]))
      if compile_targets:
        # Remove duplicate targets.
        compile_targets = sorted(set(compile_targets))
        has_failing_swarming_tests = [
            t for t in failing_tests if t.uses_swarming]
        if has_failing_swarming_tests:
          self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)
        try:
          self.m.chromium.compile(
              compile_targets, name='compile (without patch)')
        except self.m.step.StepFailure:
          self.m.tryserver.set_transient_failure_tryjob_result()
          raise
        if has_failing_swarming_tests:
          self.m.isolate.isolate_tests(self.m.chromium.output_dir,
                                       verbose=True)

    with self.wrap_chromium_tests(mastername):
      return self.m.test_utils.determine_new_failures(api, tests,
                                                      deapply_patch_fn)

  def analyze(self, affected_files, exes, compile_targets, config_file_name,
              additional_names=None, use_mb=False, build_output_dir=None):
    """Runs "analyze" step to determine targets affected by the patch.

    Returns a tuple of:
      - boolean, indicating whether patch requires compile
      - list of matching exes (see filter recipe module)
      - list of targets that need to be compiled (see filter recipe module)"""

    original_exes = exes[:]
    original_compile_targets = compile_targets[:]

    if additional_names is None:
      additional_names = ['chromium']

    self.m.filter.does_patch_require_compile(
        affected_files,
        exes=exes,
        compile_targets=compile_targets,
        additional_names=additional_names,
        config_file_name=config_file_name,
        use_mb=use_mb,
        build_output_dir=build_output_dir)

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
    compile_targets = list(set(self.m.filter.matching_exes + compile_targets))

    # Add crash_service to compile_targets. This is done after filtering compile
    # targets out because crash_service should always be there on windows.
    # TODO(akuegel): Need to solve this in a better way. crbug.com/478053
    if (self.m.platform.is_win and compile_targets and
        'crash_service' not in compile_targets and not use_mb):
      compile_targets.extend(['crash_service'])

    # Emit more detailed output useful for debugging.
    analyze_details = {
        'original_exes': original_exes,
        'original_compile_targets': original_compile_targets,
        'compile_targets': compile_targets,
        'self.m.filter.compile_targets': self.m.filter.compile_targets,
        'self.m.filter.matching_exes': self.m.filter.matching_exes,
    }
    with contextlib.closing(recipe_util.StringListIO()) as listio:
      json.dump(analyze_details, listio, indent=2, sort_keys=True)
    step_result = self.m.step.active_result
    step_result.presentation.logs['analyze_details'] = listio.lines

    # Note: due to our custom logic above it's possible we end up with empty
    # results. In this case we should not compile, because doing so would
    # use default compile targets (i.e. compile too much).
    requires_compile = bool(self.m.filter.matching_exes or compile_targets)
    return requires_compile, self.m.filter.matching_exes, compile_targets

  def configure_swarming(self, project_name, precommit, mastername=None):
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

      patch_project = self.m.properties.get('patch_project')
      if patch_project:
        self.m.swarming.add_default_tag('patch_project:%s' % patch_project)
    else:
      if mastername == 'chromium.fyi':
        # This should be lower than the CQ.
        self.m.swarming.default_priority = 35
      elif mastername == 'chromium.memory.fyi':
        self.m.swarming.default_priority = 27
      else:
        self.m.swarming.default_priority = 25
      self.m.swarming.add_default_tag('purpose:post-commit')
      self.m.swarming.add_default_tag('purpose:CI')

  def _build_gs_archive_url(self, mastername, master_config, buildername):
    """Returns the archive URL to pass to self.m.archive.zip_and_upload_build.

    Most builders on most masters use a standard format for the build archive
    URL, but some builders on some masters may specify custom places to upload
    builds to. These special cases include:
      'chromium.perf' or 'chromium.perf.fyi':
        Exclude the name of the master from the url.
      'tryserver.chromium.perf', or
          linux_full_bisect_builder on 'tryserver.chromium.linux':
        Return None so that the archive url specified in factory_properties
        (as set on the master's configuration) is used instead.
    """
    if mastername.startswith('chromium.perf'):
      return self.m.archive.legacy_upload_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=None)
    elif (mastername == 'tryserver.chromium.perf' or
          (mastername == 'tryserver.chromium.linux' and
           buildername == 'linux_full_bisect_builder')):
      return None
    else:
      return self.m.archive.legacy_upload_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=self.m.properties['mastername'])
