# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import contextlib
import copy
import itertools
import json

from recipe_engine.types import freeze
from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

from . import bot_config_and_test_db as bdb_module
from . import builders
from . import steps
from . import trybots


# Paths which affect recipe config and behavior in a way that survives
# deapplying user's patch.
RECIPE_CONFIG_PATHS = [
    'testing/buildbot',
]


PER_TARGET_SWARMING_DIMS = collections.defaultdict(dict)
PER_TARGET_SWARMING_DIMS.update({
    'android': {
      'android_devices': '6',
      'cpu': None,
      'gpu': None,
      'os': 'Android',
    }
})


MASTER_SWARMING_PRIORITIES = collections.defaultdict(lambda: 25)
MASTER_SWARMING_PRIORITIES.update({
    'chromium.fyi': 35,  # This should be lower than the CQ.
    'chromium.memory.fyi': 27,
})


class ChromiumTestsApi(recipe_api.RecipeApi):
  def __init__(self, *args, **kwargs):
    super(ChromiumTestsApi, self).__init__(*args, **kwargs)
    self._builders = {}
    self.add_builders(builders.BUILDERS)

  @property
  def builders(self):
    return self._builders

  @property
  def steps(self):
    return steps

  @property
  def trybots(self):
    return trybots.TRYBOTS

  def add_builders(self, builders):
    """Adds builders to our builder map"""
    self._builders.update(builders)

  def create_bot_config_object(self, mastername, buildername):
    return bdb_module.BotConfig(
        self.builders,
        [{'mastername': mastername, 'buildername': buildername}])

  def configure_build(self, bot_config, override_bot_type=None):
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

    self.m.gclient.set_config(
        bot_config.get('gclient_config'),
        PATCH_PROJECT=self.m.properties.get('patch_project'),
        BUILDSPEC_VERSION=buildspec_version,
        **bot_config.get('gclient_config_kwargs', {}))

    if bot_config.get('android_config'):
      self.m.chromium_android.configure_from_properties(
          bot_config.get('android_config'),
          **bot_config.get('chromium_config_kwargs', {}))

    if bot_config.get('amp_config'):
      self.m.amp.set_config(bot_config.get('amp_config'))

    for c in bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)

    for c in bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    # WARNING: src-side runtest.py is only tested with chromium CQ builders.
    # Usage not covered by chromium CQ is not supported and can break
    # without notice.
    if bot_config.get_master_setting('src_side_runtest_py'):
      self.m.chromium.c.runtest_py.src_side = True

    if bot_config.get('goma_canary'):
      self.m.goma.update_goma_canary()

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

  def ensure_checkout(self, bot_config, root_solution_revision=None):
    if self.m.platform.is_win:
      self.m.chromium.taskkill()

    # Bot Update re-uses the gclient configs.
    update_step = self.m.bot_update.ensure_checkout(
        patch_root=bot_config.get('patch_root'),
        root_solution_revision=root_solution_revision,
        clobber=bot_config.get('clobber', False))
    assert update_step.json.output['did_run']
    # HACK(dnj): Remove after 'crbug.com/398105' has landed
    self.m.chromium.set_build_properties(update_step.json.output['properties'])

    return update_step

  def set_up_swarming(self, bot_config):
    if not bot_config.get('enable_swarming'):
      return
    self.m.isolate.set_isolate_environment(self.m.chromium.c)
    self.m.swarming.check_client_version()
    for key, value in bot_config.get('swarming_dimensions', {}).iteritems():
      self.m.swarming.set_default_dimension(key, value)

  def runhooks(self, update_step):
    if self.m.tryserver.is_tryserver:
      try:
        self.m.chromium.runhooks(name='runhooks (with patch)')
      except self.m.step.StepFailure:
        # As part of deapplying patch we call runhooks without the patch.
        self.deapply_patch(update_step)
        raise
    else:
      self.m.chromium.runhooks()

  # TODO(phajdan.jr): remove create_bot_db_from_master_dict. It adds another
  # entry point to _add_master_dict_and_test_spec which can really complicate
  # things.
  def create_bot_db_from_master_dict(self, mastername, master_dict):
    bot_db = bdb_module.BotConfigAndTestDB()
    bot_db._add_master_dict_and_test_spec(mastername, master_dict, {})
    return bot_db

  def prepare_checkout(self, bot_config, root_solution_revision=None):
    update_step = self.ensure_checkout(bot_config, root_solution_revision)

    # TODO(robertocn): Remove this hack by the end of Q1/2016.
    if (bot_config.matches_any_bot_id(
            lambda bot_id: bot_id['mastername'] == 'tryserver.chromium.perf' and
                           bot_id['buildername'].endswith('builder'))
        and bot_config.get('bot_type') == 'builder'):
      if bot_config.should_force_legacy_compiling(self):
        self.m.chromium.c.project_generator.tool = 'gyp'

    self.set_up_swarming(bot_config)
    self.runhooks(update_step)

    bot_db = bdb_module.BotConfigAndTestDB()
    bot_config.initialize_bot_db(self, bot_db)

    if self.m.chromium.c.lto and \
        not self.m.chromium.c.env.LLVM_FORCE_HEAD_REVISION:
      self.m.chromium.download_lto_plugin()

    return update_step, bot_db

  def generate_tests_from_test_spec(self, api, test_spec, builder_dict,
      buildername, mastername, enable_swarming, scripts_compile_targets,
      generators):
    tests = builder_dict.get('tests', ())
    # TODO(phajdan.jr): Switch everything to scripts generators and simplify.
    for generator in generators:
      tests = (
          tuple(generator(api, mastername, buildername, test_spec,
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
      self, bot_config, bot_db,
      override_bot_type=None, override_tests=None):
    """Returns a tuple: list of compile targets and list of tests.

    The list of tests includes ones on the triggered testers."""

    assert isinstance(bot_db, bdb_module.BotConfigAndTestDB), \
        "bot_db argument %r was not a BotConfigAndTestDB" % (bot_db)

    compile_targets, tests = bot_config.get_compile_targets_and_tests(
        self, bot_db, override_bot_type, override_tests)

    # Only add crash_service when we have explicit compile targets.
    compile_targets = set(compile_targets)
    if (self.m.platform.is_win and
        compile_targets and
        'all' not in compile_targets):
      compile_targets.add('crash_service')

    return sorted(compile_targets), tests

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
        command(lambda name: '%s (without patch)' % name)
        raise
    else:
      command(lambda name: name)


  def compile(self, bot_config, update_step, bot_db,
              mb_mastername=None, mb_buildername=None):
    """Runs compile and related steps for given builder."""
    assert isinstance(bot_db, bdb_module.BotConfigAndTestDB), \
        "bot_db argument %r was not a BotConfigAndTestDB" % (bot_db)
    compile_targets, tests = self.get_compile_targets_and_tests(
        bot_config, bot_db)
    self.compile_specific_targets(
        bot_config, update_step, bot_db,
        compile_targets, tests,
        mb_mastername=mb_mastername, mb_buildername=mb_buildername)

  def compile_specific_targets(
      self, bot_config, update_step, bot_db,
      compile_targets, tests_including_triggered,
      mb_mastername=None, mb_buildername=None, override_bot_type=None):
    """Runs compile and related steps for given builder.

    Allows finer-grained control about exact compile targets used.

    We don't use the given `mastername` and `buildername` to run MB, because
    they may be the values of the continuous builder the trybot may be
    configured to match; instead we need to use the actual mastername and
    buildername we're running on (Default to the "mastername" and
    "buildername" in the build properties -- self.m.properties, but could be
    overridden by `mb_mastername` and `mb_buildername`), because it may be
    configured with different MB settings.

    However, recipes used by Findit for culprit finding may still set
    (mb_mastername, mb_buildername) = (mastername, buildername) to exactly match
    a given continuous builder."""

    assert isinstance(bot_db, bdb_module.BotConfigAndTestDB), \
        "bot_db argument %r was not a BotConfigAndTestDB" % (bot_db)
    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    self.m.chromium.cleanup_temp()
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.clean_local_files()
      self.m.chromium_android.run_tree_truth()

    if bot_type in ['builder', 'builder_tester']:
      isolated_targets = [
          t.isolate_target(self.m)
          for t in tests_including_triggered if t.uses_swarming
      ]

      if isolated_targets:
        self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)

      if self.m.chromium.c.project_generator.tool == 'mb':
        if bot_config.get('chromium_config') == 'chromium_win_clang':
          self.m.chromium.update_clang()

      try:
        self.transient_check(update_step, lambda transform_name:
            self.run_mb_and_compile(compile_targets, isolated_targets,
                                    name_suffix=transform_name(''),
                                    mb_mastername=mb_mastername,
                                    mb_buildername=mb_buildername))
      except self.m.step.StepFailure:
        self.m.tryserver.set_compile_failure_tryjob_result()
        raise

      if isolated_targets:
        self.m.isolate.remove_build_metadata()
        # 'compile' just prepares all information needed for the isolation,
        # and the isolation is a separate step.
        self.m.isolate.isolate_tests(
            self.m.chromium.output_dir,
            targets=list(set(isolated_targets)),
            verbose=True,
            set_swarm_hashes=False)

  def archive_build(self, mastername, buildername, update_step, bot_db):
    bot_config = bot_db.get_bot_config(mastername, buildername)

    if bot_config.get('bot_type') == 'builder':
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
            fixed_staging_dir=bot_config.get('fixed_staging_dir', False),
        )
      else:
        master_config = bot_db.get_master_settings(mastername)
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

      for loop_buildername, builder_dict in sorted(
          bot_db.bot_configs_matching_parent_buildername(
              mastername, buildername)):
        trigger_spec = {
            'builder_name': loop_buildername,
            'properties': {},
        }
        for name, value in update_step.presentation.properties.iteritems():
          if name.startswith('got_'):
            trigger_spec['properties']['parent_' + name] = value
        self.m.trigger(trigger_spec)

    if bot_config.get('archive_build') and not self.m.tryserver.is_tryserver:
      self.m.chromium.archive_build(
          'archive_build',
          bot_config['gs_bucket'],
          bot_config.get('gs_acl'),
          mode='dev'
      )

  def run_mb_and_compile(self, compile_targets, isolated_targets, name_suffix,
                         mb_mastername=None, mb_buildername=None):
    if self.m.chromium.c.project_generator.tool == 'mb':
      mb_mastername = mb_mastername or self.m.properties['mastername']
      mb_buildername = mb_buildername or self.m.properties['buildername']
      self.m.chromium.run_mb(mb_mastername, mb_buildername,
                             isolated_targets=isolated_targets,
                             name='generate_build_files%s' % name_suffix)

    self.m.chromium.compile(compile_targets, name='compile%s' % name_suffix)

  def download_and_unzip_build(self, mastername, buildername, update_step,
                               bot_db, build_archive_url=None,
                               build_revision=None, override_bot_type=None):
    assert isinstance(bot_db, bdb_module.BotConfigAndTestDB), \
        "bot_db argument %r was not a BotConfigAndTestDB" % (bot_db)
    # We only want to do this for tester bots (i.e. those which do not compile
    # locally).
    bot_type = override_bot_type or bot_db.get_bot_config(
        mastername, buildername).get('bot_type')
    if bot_type != 'tester':
      return

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

    legacy_build_url = None
    got_revision = update_step.presentation.properties['got_revision']
    build_revision = build_revision or self.m.properties.get(
        'parent_got_revision') or got_revision
    build_archive_url = build_archive_url or self.m.properties.get(
        'parent_build_archive_url')
    if build_archive_url is None:
      master_config = bot_db.get_master_settings(mastername)
      legacy_build_url = self._make_legacy_build_url(master_config, mastername)

    self.m.archive.download_and_unzip_build(
      step_name='extract build',
      target=self.m.chromium.c.build_config_fs,
      build_url=legacy_build_url,
      build_revision=build_revision,
      build_archive_url=build_archive_url)

  def tests_for_builder(self, mastername, buildername, update_step, bot_db,
                        override_bot_type=None):
    assert isinstance(bot_db, bdb_module.BotConfigAndTestDB), \
        "bot_db argument %r was not a BotConfigAndTestDB" % (bot_db)
    bot_config = bot_db.get_bot_config(mastername, buildername)
    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')
    # TODO(shinyak): bot_config.get('tests', []) sometimes return tuple.
    tests = [copy.deepcopy(t) for t in bot_config.get('tests', [])]

    if bot_config.get('goma_canary') or bot_config.get('goma_staging'):
      tests.insert(0, steps.DiagnoseGomaTest())

    return tests

  def _make_legacy_build_url(self, master_config, mastername):
    return self.m.archive.legacy_download_url(
               master_config.get('build_gs_bucket'),
               extra_url_components=(
                   None if mastername.startswith('chromium.perf')
                   else self.m.properties['mastername']))

  @contextlib.contextmanager
  def wrap_chromium_tests(self, bot_config, tests=None):
    bot_type = bot_config.get('bot_type', 'builder_tester')

    if bot_type in ('tester', 'builder_tester'):
      isolated_targets = [
          t.isolate_target(self.m) for t in tests if t.uses_swarming]
      if isolated_targets:
        self.m.isolate.find_isolated_tests(self.m.chromium.output_dir)

    if bot_type == 'tester':
      if (self.m.chromium.c.TARGET_PLATFORM == 'android' and
          bot_config.get('root_devices')):
        self.m.adb.root_devices()

    # Some recipes use this wrapper to setup devices and have their own way
    # to run tests. If platform is Android and tests is None, run device steps.
    require_device_steps = (tests is None or
                            any([t.uses_local_devices for t in tests]))

    if self.m.chromium.c.TARGET_PLATFORM == 'android' and require_device_steps:
      #TODO(prasadv): Remove this hack and implement specific functions
      # at the point of call.
      perf_setup = bot_config.matches_any_bot_id(lambda bot_id:
          bot_id['mastername'].startswith('chromium.perf') or
          bot_id['mastername'].startswith('tryserver.chromium.perf'))
      self.m.chromium_android.common_tests_setup_steps(perf_setup=perf_setup)

    if self.m.platform.is_win:
      self.m.chromium.crash_handler()

    try:
      yield
    finally:
      if self.m.platform.is_win:
        self.m.chromium.process_dumps()

      if self.m.chromium.c.TARGET_PLATFORM == 'android':
        if require_device_steps:
          self.m.chromium_android.common_tests_final_steps(
              logcat_gs_bucket='chromium-android')
        else:
          self.m.chromium_android.test_report()

  def deapply_patch(self, bot_update_step):
    assert self.m.tryserver.is_tryserver

    if self.m.platform.is_win:
      self.m.chromium.taskkill()
    bot_update_json = bot_update_step.json.output
    # We only override first solution here to make sure that we correctly revert
    # changes to DEPS file, which is particularly important for auto-rolls. It
    # is also imporant that we do not assume that corresponding revision is
    # stored in the 'got_revision' as some gclient configs change the default
    # mapping for their own purposes.
    first_solution_name = self.m.gclient.c.solutions[0].name
    rev_property = self.m.gclient.c.got_revision_mapping[first_solution_name]
    self.m.gclient.c.revisions[first_solution_name] = str(
        bot_update_json['properties'][rev_property])
    self.m.bot_update.ensure_checkout(
        force=True, patch=False, update_presentation=False)
    self.m.chromium.runhooks(name='runhooks (without patch)')

  def run_tests_on_tryserver(self, bot_config, api, tests, bot_update_step,
                             affected_files, mb_mastername=None,
                             mb_buildername=None):
    def deapply_patch_fn(failing_tests):
      self.deapply_patch(bot_update_step)
      compile_targets = list(itertools.chain(
          *[t.compile_targets(api) for t in failing_tests]))
      if compile_targets:
        # Remove duplicate targets.
        compile_targets = sorted(set(compile_targets))
        failing_swarming_tests = [
            t.isolate_target(api) for t in failing_tests if t.uses_swarming]
        if failing_swarming_tests:
          self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)
        self.run_mb_and_compile(compile_targets, failing_swarming_tests,
                                ' (without patch)',
                                mb_mastername=mb_mastername,
                                mb_buildername=mb_buildername)
        if failing_swarming_tests:
          self.m.isolate.isolate_tests(self.m.chromium.output_dir,
                                       verbose=True)

    deapply_patch = True
    for path in RECIPE_CONFIG_PATHS:
      if any([f.startswith(path) for f in affected_files]):
        deapply_patch = False
        break

    with self.wrap_chromium_tests(bot_config, tests):
      if deapply_patch:
        self.m.test_utils.determine_new_failures(api, tests, deapply_patch_fn)
      else:
        failing_tests = self.m.test_utils.run_tests_with_patch(api, tests)
        if failing_tests:
          self.m.python.failing_step('test results', 'TESTS FAILED')

  def analyze(self, affected_files, test_targets, additional_compile_targets,
              config_file_name, mb_mastername=None, mb_buildername=None,
              additional_names=None):
    """Runs "analyze" step to determine targets affected by the patch.

    Returns a tuple of:
      - list of targets that are needed to run tests (see filter recipe module)
      - list of targets that need to be compiled (see filter recipe module)"""

    if additional_names is None:
      additional_names = ['chromium']

    use_mb = (self.m.chromium.c.project_generator.tool == 'mb')
    build_output_dir = '//out/%s' % self.m.chromium.c.build_config_fs
    self.m.filter.does_patch_require_compile(
        affected_files,
        test_targets=test_targets,
        additional_compile_targets=additional_compile_targets,
        additional_names=additional_names,
        config_file_name=config_file_name,
        use_mb=use_mb,
        mb_mastername=mb_mastername,
        mb_buildername=mb_buildername,
        build_output_dir=build_output_dir,
        cros_board=self.m.chromium.c.TARGET_CROS_BOARD)

    compile_targets = self.m.filter.compile_targets[:]

    # Add crash_service to compile_targets. This is done after filtering compile
    # targets out because crash_service should always be there on windows.
    # TODO(akuegel): Need to solve this in a better way. crbug.com/478053
    if (self.m.platform.is_win and compile_targets and
        'crash_service' not in compile_targets):
      compile_targets.extend(['crash_service'])

    # Emit more detailed output useful for debugging.
    analyze_details = {
        'test_targets': test_targets,
        'additional_compile_targets': additional_compile_targets,
        'self.m.filter.compile_targets': self.m.filter.compile_targets,
        'self.m.filter.test_targets': self.m.filter.test_targets,
        'compile_targets': compile_targets,
    }
    with contextlib.closing(recipe_util.StringListIO()) as listio:
      json.dump(analyze_details, listio, indent=2, sort_keys=True)
    step_result = self.m.step.active_result
    step_result.presentation.logs['analyze_details'] = listio.lines

    return self.m.filter.test_targets, compile_targets

  def configure_swarming(self, project_name, precommit, mastername=None):
    """Configures default swarming dimensions and tags.

    Uses the 'chromium' global config to determine target platform defaults,
    make sure something like chromium_tests.configure_build() has been called
    beforehand.

    Args:
      project_name: Lowercase name of the project, e.g. "blink", "chromium".
      precommit: Boolean flag to indicate whether the tests are running before
          the changes are commited.
    """

    # Set platform-specific default dims.
    target_platform = self.m.chromium.c.TARGET_PLATFORM
    swarming_dims = PER_TARGET_SWARMING_DIMS[target_platform]
    for k, v in swarming_dims.iteritems():
      self.m.swarming.set_default_dimension(k, v)

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
      self.m.swarming.default_priority = MASTER_SWARMING_PRIORITIES[mastername]
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

  def get_common_args_for_scripts(self):
    args = []

    args.extend(['--build-config-fs', self.m.chromium.c.build_config_fs])

    if self.m.chromium.c.runtest_py.src_side:
      args.append('--use-src-side-runtest-py')

    paths = {}
    for path in ('build', 'checkout'):
      paths[path] = self.m.path[path]
    args.extend(['--paths', self.m.json.input(paths)])

    properties = {}
    # TODO(phajdan.jr): Remove buildnumber when no longer used.

    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = self.builders.get(mastername, {})
    bot_config = master_dict.get('builders', {}).get(buildername, {})

    for name in ('buildername', 'slavename', 'buildnumber', 'mastername'):
      properties[name] = self.m.properties[name]

    # Optional properties
    for name in ('perf-id', 'results-url'):
      if bot_config.get(name):
        properties[name] = bot_config[name]

    properties['target_platform'] = self.m.chromium.c.TARGET_PLATFORM

    args.extend(['--properties', self.m.json.input(properties)])

    return args

  def get_compile_targets_for_scripts(self):
    return self.m.python(
        name='get compile targets for scripts',
        script=self.m.path['checkout'].join(
            'testing', 'scripts', 'get_compile_targets.py'),
        args=[
            '--output', self.m.json.output(),
            '--',
        ] + self.get_common_args_for_scripts(),
        step_test_data=lambda: self.m.json.test_api.output({}))
