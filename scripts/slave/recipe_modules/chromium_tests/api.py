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

from . import bot_config_and_test_db as bdb_module
from . import builders
from . import steps
from . import trybots


# Paths which affect recipe config and behavior in a way that survives
# deapplying user's patch.
RECIPE_CONFIG_PATHS = [
    'testing/buildbot',
]


# TODO(phajdan.jr): Remove special case for layout tests.
# This could be done by moving layout tests to main waterfall.
CHROMIUM_BLINK_TESTS_BUILDERS = freeze([
  'mac_chromium_rel_ng',
  'win_chromium_rel_ng',
])

CHROMIUM_BLINK_TESTS_SWARMING_BUILDERS = freeze([
  'linux_chromium_rel_ng',
])


CHROMIUM_BLINK_TESTS_PATHS = freeze([
  'components/test_runner',
  'content/browser/bluetooth',
  'content/browser/service_worker',
  'content/child/service_worker',
  'content/common/bluetooth',
  'content/renderer/bluetooth',
  'content/renderer/service_worker',
  'content/shell/browser/layout_test',
  'content/shell/renderer/layout_test',
  'device/bluetooth',
  'device/usb/public/interfaces',
  'media',
  'third_party/WebKit',
  'third_party/harfbuzz-ng',
  'third_party/iccjpeg',
  'third_party/libjpeg',
  'third_party/libjpeg_turbo',
  'third_party/libpng',
  'third_party/libwebp',
  'third_party/qcms',
  'third_party/skia',
  'third_party/yasm',
  'third_party/zlib',
  'v8',
])


class ChromiumTestsApi(recipe_api.RecipeApi):
  def __init__(self, *args, **kwargs):
    super(ChromiumTestsApi, self).__init__(*args, **kwargs)
    self._builders = {}
    self.add_builders(builders.BUILDERS)
    self._precommit_mode = False

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
    bot_id = {'mastername': mastername, 'buildername': buildername}
    return bdb_module.BotConfig(self.builders, [bot_id])

  def create_generalized_bot_config_object(self, bot_ids):
    return bdb_module.BotConfig(self.builders, bot_ids)

  def create_bot_db_object(self):
    return bdb_module.BotConfigAndTestDB()

  def set_precommit_mode(self):
    """Configures this module to indicate that tests are running before
    the changes are committed. This must be called very early in the
    recipe, certainly before prepare_checkout, and the action can not
    be undone.
    """
    self._precommit_mode = True

  def is_precommit_mode(self):
    """Returns a Boolean indicating whether this module is running in
    precommit mode; i.e., whether tests are running before the changes
    are committed.
    """
    return self._precommit_mode

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

    self.m.gclient.set_config(
        bot_config.get('gclient_config'),
        PATCH_PROJECT=self.m.properties.get('patch_project'),
        BUILDSPEC_VERSION=buildspec_version,
        **bot_config.get('gclient_config_kwargs', {}))

    self.m.test_results.set_config(
        bot_config.get('test_results_config'))

    if bot_config.get('android_config'):
      self.m.chromium_android.configure_from_properties(
          bot_config.get('android_config'),
          **bot_config.get('chromium_config_kwargs', {}))

    for c in bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)

    for c in bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    for c in bot_config.get('android_apply_config', []):
      self.m.chromium_android.apply_config(c)

    # WARNING: src-side runtest.py is only tested with chromium CQ builders.
    # Usage not covered by chromium CQ is not supported and can break
    # without notice.
    if bot_config.get_master_setting('src_side_runtest_py'):
      self.m.chromium.c.runtest_py.src_side = True

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

  def set_up_swarming(self, bot_config):
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
    bot_db = self.create_bot_db_object()
    bot_db._add_master_dict_and_test_spec(mastername, master_dict, {})
    return bot_db

  def prepare_checkout(self, bot_config, root_solution_revision=None):
    update_step = self.m.chromium_checkout.ensure_checkout(
        bot_config, root_solution_revision)

    if (self.m.chromium.c.compile_py.compiler and
        'goma' in self.m.chromium.c.compile_py.compiler):
      self.m.chromium.ensure_goma(canary=bot_config.get('goma_canary', False))

    self.set_up_swarming(bot_config)
    self.runhooks(update_step)

    bot_db = bdb_module.BotConfigAndTestDB()
    bot_config.initialize_bot_db(self, bot_db, update_step)

    if self.m.chromium.c.lto and \
        not self.m.chromium.c.env.LLVM_FORCE_HEAD_REVISION:
      self.m.chromium.download_lto_plugin()

    return update_step, bot_db

  @property
  def _api_for_tests(self):
    """Methods of Test objects receive this as their api object to allow them
    to access the 'chromium_tests' module as well as the other modules
    in chromium_tests' module DEPS"""
    api = copy.copy(self.m)
    api.chromium_tests = self
    return api

  # TODO(phajdan.jr): remove enable_swarming (http://crbug.com/684067).
  def generate_tests_from_test_spec(self, test_spec, builder_dict,
      buildername, mastername, enable_swarming, swarming_dimensions,
      scripts_compile_targets, generators, bot_update_step):
    tests = builder_dict.get('tests', ())
    # TODO(phajdan.jr): Switch everything to scripts generators and simplify.
    for generator in generators:
      tests = (
          tuple(generator(
              self._api_for_tests, self, mastername, buildername, test_spec,
              bot_update_step, enable_swarming=enable_swarming,
              swarming_dimensions=swarming_dimensions,
              scripts_compile_targets=scripts_compile_targets)) +
          tuple(tests))
    return tests

  def read_test_spec(self, test_spec_file):
    test_spec_path = self.m.path['checkout'].join(
        'testing', 'buildbot', test_spec_file)
    test_spec_result = self.m.json.read(
        'read test spec (%s)' % self.m.path.basename(test_spec_path),
        test_spec_path,
        step_test_data=lambda: self.m.json.test_api.output({}))
    test_spec_result.presentation.step_text = 'path: %s' % test_spec_path
    test_spec = test_spec_result.json.output

    return test_spec

  def create_test_runner(self, tests, suffix='', serialize_tests=False):
    """Creates a test runner to run a set of tests.

    Args:
      api: API of the calling recipe.
      tests: List of step.Test objects to be run.
      suffix: Suffix to be passed when running the tests.
      serialize_tests: True if this bot should run all tests serially
        (specifically, tests run on Swarming). Used to reduce the load
        generated by waterfall bots.

    Returns:
      A function that can be passed to setup_chromium_tests or run directly.

    """

    def test_runner():
      failed_tests = []

      with self.m.step.nest('test_pre_run'):
        for t in tests:
          try:
            t.pre_run(self._api_for_tests, suffix)
          except self.m.step.InfraFailure:  # pragma: no cover
            raise
          except self.m.step.StepFailure:  # pragma: no cover
            failed_tests.append(t)

      for t in tests:
        try:
          t.run(self._api_for_tests, suffix)
        except self.m.step.InfraFailure:  # pragma: no cover
          raise
        except self.m.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)
          if t.abort_on_failure:
            raise

      for t in tests:
        try:
          t.post_run(self._api_for_tests, suffix)
        except self.m.step.InfraFailure:  # pragma: no cover
          raise
        except self.m.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)
          if t.abort_on_failure:
            raise

      if failed_tests:
        failed_tests_names = [t.name for t in failed_tests]
        raise self.m.step.StepFailure(
            '%d tests failed: %r' % (len(failed_tests), failed_tests_names))

    def serialized_test_runner():
      failed_tests = []

      for t in tests:
        try:
          t.pre_run(self._api_for_tests, suffix)
        except self.m.step.InfraFailure:  # pragma: no cover
          raise
        except self.m.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)

        try:
          t.run(self._api_for_tests, suffix)
        except self.m.step.InfraFailure:  # pragma: no cover
          raise
        except self.m.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)
          if t.abort_on_failure:
            raise

        try:
          t.post_run(self._api_for_tests, suffix)
        except self.m.step.InfraFailure:  # pragma: no cover
          raise
        except self.m.step.StepFailure:  # pragma: no cover
          failed_tests.append(t)
          if t.abort_on_failure:
            raise

      if failed_tests:
        failed_tests_names = [t.name for t in failed_tests]
        raise self.m.step.StepFailure(
            '%d tests failed: %r' % (len(failed_tests), failed_tests_names))

    return serialized_test_runner if serialize_tests else test_runner

  def get_tests(self, bot_config, bot_db):
    """Returns a tuple: list of tests, and list of tests on the triggered
       testers."""

    assert isinstance(bot_db, bdb_module.BotConfigAndTestDB), \
        "bot_db argument %r was not a BotConfigAndTestDB" % (bot_db)

    return bot_config.get_tests(bot_db)

  def get_compile_targets(self, bot_config, bot_db, tests):
    assert isinstance(bot_db, bdb_module.BotConfigAndTestDB), \
        "bot_db argument %r was not a BotConfigAndTestDB" % (bot_db)

    compile_targets = bot_config.get_compile_targets(self, bot_db, tests)
    return sorted(set(compile_targets))

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

    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.clean_local_files()
      self.m.chromium_android.run_tree_truth()

    if bot_type in ['builder', 'builder_tester']:
      isolated_targets = [
          t.isolate_target(self._api_for_tests)
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
            set_swarm_hashes=False,
            always_use_exparchive=bot_config.get('force_exparchive', False))
        if bot_config.get('perf_isolate_lookup'):
          self.m.perf_dashboard.set_default_config()
          self.m.perf_dashboard.upload_isolated(
              self.m.properties['buildername'],
              update_step.presentation.properties['got_revision'],
              self.m.isolate.isolated_tests)

  def archive_build(self, mastername, buildername, update_step, bot_db):
    bot_config = bot_db.get_bot_config(mastername, buildername)

    if bot_config.get('bot_type') == 'builder':
      if not bot_config.get('cf_archive_build'):
        master_config = bot_db.get_master_settings(mastername)
        build_revision = update_step.presentation.properties['got_revision']

        # For archiving 'chromium.perf', the builder also archives a version
        # without perf test files for manual bisect.
        # (https://bugs.chromium.org/p/chromium/issues/detail?id=604452)
        if (master_config.get('bisect_builders') and
            buildername in master_config.get('bisect_builders')):
          self.m.archive.zip_and_upload_build(
              'package build for bisect',
              self.m.chromium.c.build_config_fs,
              build_url=self._build_bisect_gs_archive_url(master_config),
              build_revision=build_revision,
              cros_board=self.m.chromium.c.TARGET_CROS_BOARD,
              update_properties=update_step.presentation.properties,
              exclude_perf_test_files=True,
              store_by_hash=False,
              platform=self.m.chromium.c.HOST_PLATFORM
          )

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

      # TODO(phajdan.jr): Triggering should be separate from archiving.
      trigger_specs = []
      for loop_mastername, loop_buildername, builder_dict in sorted(
          bot_db.bot_configs_matching_parent_buildername(
              mastername, buildername)):
        trigger_spec = {
            'builder_name': loop_buildername,
            'properties': {
                'parent_mastername': mastername,
            },
        }
        if mastername != loop_mastername:
          trigger_spec['bucket'] = 'master.' + loop_mastername
        for name, value in update_step.presentation.properties.iteritems():
          if name.startswith('got_'):
            trigger_spec['properties']['parent_' + name] = value
        trigger_specs.append(trigger_spec)
      if trigger_specs:
        self.m.trigger(*trigger_specs)

    if bot_config.get('archive_build') and not self.m.tryserver.is_tryserver:
      self.m.chromium.archive_build(
          'archive_build',
          bot_config['gs_bucket'],
          bot_config.get('gs_acl'),
          mode='dev'
      )
    if bot_config.get('cf_archive_build') and not self.m.tryserver.is_tryserver:
       self.m.archive.clusterfuzz_archive(
         build_dir=self.m.chromium.c.build_dir.join(
         self.m.chromium.c.build_config_fs),
         update_properties=update_step.presentation.properties,
         gs_bucket=bot_config.get('cf_gs_bucket'),
         gs_acl=bot_config.get('cf_gs_acl'),
         archive_prefix=bot_config.get('cf_archive_name'),
         archive_subdir_suffix=bot_config.get('cf_archive_subdir_suffix', ''),
         revision_dir=bot_config.get('cf_revision_dir'),
       )

  def run_mb_and_compile(self, compile_targets, isolated_targets, name_suffix,
                         mb_mastername=None, mb_buildername=None):
    use_goma_module=False
    if self.m.chromium.c.project_generator.tool == 'mb':
      mb_mastername = mb_mastername or self.m.properties['mastername']
      mb_buildername = mb_buildername or self.m.properties['buildername']
      use_goma = (self.m.chromium.c.compile_py.compiler and
                  'goma' in self.m.chromium.c.compile_py.compiler)
      self.m.chromium.run_mb(mb_mastername, mb_buildername, use_goma=use_goma,
                             isolated_targets=isolated_targets,
                             name='generate_build_files%s' % name_suffix)
      if use_goma:
        use_goma_module = True

    self.m.chromium.compile(compile_targets, name='compile%s' % name_suffix,
                            use_goma_module=use_goma_module)

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
    build_revision = build_revision or self.m.properties.get(
        'parent_got_revision') or update_step.presentation.properties[
        'got_revision']
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

  def _make_legacy_build_url(self, master_config, mastername):
    # The master where the build was zipped and uploaded from.
    source_master = self.m.properties.get('parent_mastername')
    if not source_master:
      source_master = self.m.properties['mastername']
    return self.m.archive.legacy_download_url(
               master_config.get('build_gs_bucket'),
               extra_url_components=(
                   None if mastername.startswith('chromium.perf')
                   else source_master))

  @contextlib.contextmanager
  def wrap_chromium_tests(self, bot_config, tests=None):
    context = {
        'cwd': self.m.chromium_checkout.working_dir,
        'env': self.m.chromium.get_env(),
    }
    with self.m.step.context(context):
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ('tester', 'builder_tester'):
        isolated_targets = [
            t.isolate_target(self._api_for_tests)
            for t in tests if t.uses_swarming]
        if isolated_targets:
          self.m.isolate.find_isolated_tests(self.m.chromium.output_dir)

      if bot_type == 'tester':
        if (self.m.chromium.c.TARGET_PLATFORM == 'android' and
            bot_config.get('root_devices')):
          self.m.adb.root_devices()

      # Some recipes use this wrapper to setup devices and have their own way
      # to run tests. If platform is Android and tests is None, run device
      # steps.
      require_device_steps = (tests is None or
                              any([t.uses_local_devices for t in tests]))

      if (self.m.chromium.c.TARGET_PLATFORM == 'android' and
          require_device_steps):
        #TODO(prasadv): Remove this hack and implement specific functions
        # at the point of call.
        perf_setup = bot_config.matches_any_bot_id(lambda bot_id:
            bot_id['mastername'].startswith('chromium.perf') or
            bot_id['mastername'].startswith('tryserver.chromium.perf'))
        self.m.chromium_android.common_tests_setup_steps(perf_setup=perf_setup)

      try:
        yield
      finally:
        if self.m.platform.is_win:
          self.m.chromium.process_dumps()

        checkout_dir = None
        if self.m.chromium_checkout.working_dir:
          checkout_dir = self.m.chromium_checkout.working_dir.join('src')
        if self.m.chromium.c.TARGET_PLATFORM == 'android':
          if require_device_steps:
            self.m.chromium_android.common_tests_final_steps(
                logcat_gs_bucket='chromium-android',
                checkout_dir=checkout_dir)
          else:
            self.m.chromium_android.test_report()

  def deapply_patch(self, bot_update_step):
    assert self.m.tryserver.is_tryserver

    if self.m.platform.is_win:
      self.m.chromium.taskkill()

    context = {}
    if self.m.chromium_checkout.working_dir:
      context['cwd'] = self.m.chromium_checkout.working_dir

    with self.m.step.context(context):
      self.m.bot_update.deapply_patch(bot_update_step)
    with self.m.step.context({'cwd': self.m.path['checkout']}):
      self.m.chromium.runhooks(name='runhooks (without patch)')

  def run_tests_on_tryserver(self, bot_config, tests, bot_update_step,
                             affected_files, mb_mastername=None,
                             mb_buildername=None, disable_deapply_patch=False):
    def deapply_patch_fn(failing_tests):
      self.deapply_patch(bot_update_step)
      compile_targets = list(itertools.chain(
          *[t.compile_targets(self._api_for_tests) for t in failing_tests]))
      if compile_targets:
        # Remove duplicate targets.
        compile_targets = sorted(set(compile_targets))
        failing_swarming_tests = [
            t.isolate_target(self._api_for_tests)
            for t in failing_tests if t.uses_swarming]
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
    deapply_patch_reason = 'unknown reason'
    for path in RECIPE_CONFIG_PATHS:
      if any([f.startswith(path) for f in affected_files]):
        deapply_patch = False
        deapply_patch_reason = 'build config changes detected'
        break
    if disable_deapply_patch:
      deapply_patch = False
      deapply_patch_reason = 'disabled in recipes'

    with self.wrap_chromium_tests(bot_config, tests):
      if deapply_patch:
        self.m.test_utils.determine_new_failures(
            self._api_for_tests, tests, deapply_patch_fn)
      else:
        failing_tests = self.m.test_utils.run_tests_with_patch(
            self._api_for_tests, tests)
        if failing_tests:
          self.m.python.failing_step(
              'test results',
              'TESTS FAILED; retries without patch disabled (%s)'
                  % deapply_patch_reason)

  def _build_bisect_gs_archive_url(self, master_config):
    return self.m.archive.legacy_upload_url(
        master_config.get('bisect_build_gs_bucket'),
        extra_url_components=master_config.get('bisect_build_gs_extra'))

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

    paths = {
      'checkout': self.m.path['checkout'],
      'runit.py': self.package_repo_resource('scripts', 'tools', 'runit.py'),
      'runtest.py': self.package_repo_resource(
          'scripts', 'slave', 'runtest.py'),
    }
    args.extend(['--paths', self.m.json.input(paths)])

    properties = {}
    # TODO(phajdan.jr): Remove buildnumber when no longer used.

    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = self.builders.get(mastername, {})
    bot_config = master_dict.get('builders', {}).get(buildername, {})

    for name in ('buildername', 'bot_id', 'buildnumber', 'mastername'):
      properties[name] = self.m.properties[name]
    properties['slavename'] = properties['bot_id']

    # Optional properties
    for name in ('perf-id', 'results-url'):
      if bot_config.get(name):
        properties[name] = bot_config[name]

    properties['target_platform'] = self.m.chromium.c.TARGET_PLATFORM

    args.extend(['--properties', self.m.json.input(properties)])

    return args

  def get_compile_targets_for_scripts(self):
    """This gets the combined compile_targets information from the
    //testing/scripts/get_compile_targets.py script.

    This script returns the compile targets for all of the 'script tests' in
    chromium (including ones that we don't plan to run on this configuration,
    see TODO). The information is returned in the following format:

    {
      "some_script_name.py": ["list", "of", "compile", "targets"],
    }

    Where "some_script_name.py" corresponds to
    "//testing/scripts/some_script_name.py".

    Returns:
      The compile target data in the form described above.

    TODO:
      * Only gather targets for the scripts that we might concievably run.
    """
    result = self.m.python(
        name='get compile targets for scripts',
        script=self.m.path['checkout'].join(
            'testing', 'scripts', 'get_compile_targets.py'),
        args=[
            '--output', self.m.json.output(),
            '--',
        ] + self.get_common_args_for_scripts(),
        step_test_data=lambda: self.m.json.test_api.output({}))
    return result.json.output

  def main_waterfall_steps(self):
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')

    bot_config = self.create_bot_config_object(mastername, buildername)
    self.configure_build(bot_config)
    update_step, bot_db = self.prepare_checkout(bot_config)
    tests, tests_including_triggered = self.get_tests(bot_config, bot_db)
    compile_targets = self.get_compile_targets(
        bot_config, bot_db, tests_including_triggered)
    self.compile_specific_targets(
        bot_config, update_step, bot_db,
        compile_targets, tests_including_triggered)
    self.archive_build(
        mastername, buildername, update_step, bot_db)
    self.download_and_unzip_build(mastername, buildername, update_step, bot_db)

    if not tests:
      return

    self.m.chromium_swarming.configure_swarming(
        'chromium', precommit=False, mastername=mastername)
    test_runner = self.create_test_runner(
        tests, serialize_tests=bot_config.get('serialize_tests'))
    with self.wrap_chromium_tests(bot_config, tests):
      test_runner()

  def trybot_steps(self):
    with self.m.tryserver.set_failure_hash():
      try:
        (bot_config_object, bot_update_step, affected_files, tests,
         disable_deapply_patch) = self._trybot_steps_internal()
      finally:
        self.m.python.succeeding_step('mark: before_tests', '')

      if tests:
        self.run_tests_on_tryserver(
            bot_config_object, tests, bot_update_step,
            affected_files, disable_deapply_patch=disable_deapply_patch)

  def _trybot_steps_internal(self):
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    bot_config = self.trybots.get(mastername, {}).get(
        'builders', {}).get(buildername)
    assert bot_config, 'No bot config for master/builder [%s / %s]' % (
        mastername, buildername)

    bot_config_object = self.create_generalized_bot_config_object(
        bot_config['bot_ids'])
    self.set_precommit_mode()
    self.configure_build(bot_config_object, override_bot_type='builder_tester')

    self.m.chromium_swarming.configure_swarming('chromium', precommit=True)

    self.m.chromium.apply_config('trybot_flavor')

    bot_update_step, bot_db = self.prepare_checkout(bot_config_object)
    tests, tests_including_triggered = self.get_tests(bot_config_object, bot_db)

    def add_tests(additional_tests):
      tests.extend(additional_tests)
      tests_including_triggered.extend(additional_tests)

    affected_files = self.m.chromium_checkout.get_files_affected_by_patch(
        'src/')

    affects_blink_paths = any(
        f.startswith(path) for f in affected_files
        for path in CHROMIUM_BLINK_TESTS_PATHS)

    if affects_blink_paths:
      subproject_tag = 'blink'
    else:
      subproject_tag = 'chromium'

    self.m.tryserver.set_subproject_tag(subproject_tag)

    # TODO(phajdan.jr): Remove special case for layout tests.
    add_blink_tests = (
        affects_blink_paths and
        buildername in
        CHROMIUM_BLINK_TESTS_BUILDERS+CHROMIUM_BLINK_TESTS_SWARMING_BUILDERS)
    add_blink_tests_swarming = (
        affects_blink_paths and
        buildername in CHROMIUM_BLINK_TESTS_SWARMING_BUILDERS)

    # Add blink tests that work well with "analyze" here. The tricky ones
    # that bypass it (like the layout tests) are added later.
    if add_blink_tests:
      add_tests([
          self.steps.GTestTest('blink_heap_unittests'),
          self.steps.GTestTest('blink_platform_unittests'),
          self.steps.GTestTest('webkit_unit_tests'),
          self.steps.GTestTest('wtf_unittests'),
      ])
    if add_blink_tests_swarming:
      merge = {
          'script': self.m.path['checkout'].join(
              'third_party', 'WebKit', 'Tools', 'Scripts',
              'merge-layout-test-results'),
          'args': [
              '--verbose',
              '--results-json-override-with-build-property',
              'build_number',
              'buildnumber',
              '--results-json-override-with-build-property',
              'builder_name',
              'buildername',
              '--results-json-override-with-build-property',
              'chromium_revision',
              'got_revision_cp',
            ],
      }
      add_tests([
          self.steps.SwarmingIsolatedScriptTest(
              name='webkit_layout_tests',
              args=[],
              target_name='webkit_layout_tests_exparchive',
              shards=6,
              dimensions={'os': 'Ubuntu-14.04'},
              override_compile_targets=None,
              priority=None,
              expiration=None,
              hard_timeout=None,
              perf_id=bot_config.get('perf-id'),
              results_url=bot_config.get('results-url'),
              perf_dashboard_id='webkt_layout_tests_exparchive',
              io_timeout=None,
              waterfall_mastername=mastername,
              waterfall_buildername=buildername,
              merge=merge,
              results_handler=self.steps.LayoutTestResultsHandler(),
          ),
      ])

    compile_targets = self.get_compile_targets(
        bot_config_object,
        bot_db,
        tests_including_triggered)

    test_targets = sorted(set(
        self._all_compile_targets(tests + tests_including_triggered)))
    additional_compile_targets = sorted(
        set(compile_targets) - set(test_targets))
    test_targets, compile_targets = self.m.filter.analyze(
        affected_files, test_targets, additional_compile_targets,
        'trybot_analyze_config.json')

    if bot_config.get('analyze_mode') == 'compile':
      tests = []
      tests_including_triggered = []

    # Blink tests have to bypass "analyze", see below.
    if compile_targets or add_blink_tests:
      tests = self._tests_in_compile_targets(test_targets, tests)
      tests_including_triggered = self._tests_in_compile_targets(
          test_targets, tests_including_triggered)

      # TODO(tansell): Remove these special cases.
      # At the moment there remains a few blink tests which are not using
      # "analyze". These tests don't correctly specify their dependencies and
      # thus need to be manually added on blink changes.
      # See https://crbug.com/703894
      if add_blink_tests:
        blink_tests = [
            self.steps.ScriptTest(
                'webkit_lint', 'webkit_lint.py', collections.defaultdict(list)),
            self.steps.ScriptTest(
                'webkit_python_tests', 'webkit_python_tests.py',
                collections.defaultdict(list)),
        ]
        # TODO(tansell): Remove this once all builders are running layout tests
        # via analyze.
        if not add_blink_tests_swarming:
          blink_tests.append(self.steps.BlinkTest())

        add_tests(blink_tests)
        for test in blink_tests:
          compile_targets.extend(test.compile_targets(self._api_for_tests))
        compile_targets = sorted(set(compile_targets))

      self.compile_specific_targets(
          bot_config_object,
          bot_update_step,
          bot_db,
          compile_targets,
          tests_including_triggered,
          override_bot_type='builder_tester')
    else:
      # Even though the patch doesn't require a compile on this platform,
      # we'd still like to run tests not depending on
      # compiled targets (that's obviously not covered by the
      # 'analyze' step) if any source files change.
      if any(self._is_source_file(f) for f in affected_files):
        tests = [t for t in tests if not t.compile_targets(self._api_for_tests)]
      else:
        tests = []

    disable_deapply_patch = not bot_config.get('deapply_patch', True)
    return (bot_config_object, bot_update_step, affected_files, tests,
            disable_deapply_patch)

  def _all_compile_targets(self, tests):
    """Returns the compile_targets for all the Tests in |tests|."""
    return sorted(set(x
                      for test in tests
                      for x in test.compile_targets(self._api_for_tests)))

  def _is_source_file(self, filepath):
    """Returns true iff the file is a source file."""
    _, ext = self.m.path.splitext(filepath)
    return ext in ['.c', '.cc', '.cpp', '.h', '.java', '.mm']

  def _tests_in_compile_targets(self, compile_targets, tests):
    """Returns the tests in |tests| that have at least one of their compile
    targets in |compile_targets|."""
    result = []
    for test in tests:
      test_compile_targets = test.compile_targets(self._api_for_tests)
      # Always return tests that don't require compile. Otherwise we'd never
      # run them.
      if ((set(compile_targets) & set(test_compile_targets)) or
          not test_compile_targets):
        result.append(test)
    return result
