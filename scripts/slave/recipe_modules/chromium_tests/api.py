# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import contextlib
import copy
import functools
import itertools
import json
import re
import traceback

from recipe_engine.types import freeze
from recipe_engine import recipe_api

from . import bot_config_and_test_db as bdb_module
from . import builders
from . import steps


# Paths which affect recipe config and behavior in a way that survives
# deapplying user's patch.
RECIPE_CONFIG_PATHS = [
  'testing/buildbot/.*json$',
  'testing/buildbot/.*pyl$',
]

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
    return self.test_api.trybots


  def log(self, message):
    presentation = self.m.step.active_result.presentation
    presentation.logs.setdefault('stdout', []).append(message)

  def add_builders(self, builders):
    """Adds builders to our builder map"""
    self._builders.update(builders)

  def create_bot_config_object(self, mastername, buildername, builders=None):
    return self.create_generalized_bot_config_object(
        [self.create_bot_id(mastername, buildername)],
        builders=builders)

  def create_bot_id(self, mastername, buildername):
    return {'mastername': mastername, 'buildername': buildername}

  def create_generalized_bot_config_object(self, bot_ids, builders=None):
    try:
      return bdb_module.BotConfig(builders or self.builders, bot_ids)
    except Exception:
      if (self._test_data.enabled and
          not self._test_data.get('handle_bot_config_errors', True)):
        raise  # pragma: no cover
      self.m.python.failing_step(
          'Incorrect or missing bot configuration',
          [traceback.format_exc()],
          as_log='details')

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

  def get_config_defaults(self):
    return {'CHECKOUT_PATH': self.m.path['checkout']}

  def configure_build(self, bot_config, override_bot_type=None):
    # Get the buildspec version. It can be supplied as a build property or as
    # a recipe config value.
    buildspec_version = (self.m.properties.get('buildspec_version') or
                         bot_config.get('buildspec_version'))

    self.m.chromium.set_config(
        bot_config.get('chromium_config'),
        **bot_config.get('chromium_config_kwargs', {}))
    self.set_config(bot_config.get('chromium_tests_config', 'chromium'))

    self.m.gclient.set_config(
        bot_config.get('gclient_config'),
        PATCH_PROJECT=self.m.properties.get('patch_project'),
        BUILDSPEC_VERSION=buildspec_version,
        **bot_config.get('gclient_config_kwargs', {}))

    default_test_results_config = (
        'staging_server'
        if self.m.runtime.is_experimental
        else 'public_server')
    self.m.test_results.set_config(
        bot_config.get('test_results_config', default_test_results_config))

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

    for c in bot_config.get('chromium_tests_apply_config', []):
      self.apply_config(c)

    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    if bot_config.get('set_component_rev'):
      # If this is a component build and the main revision is e.g. blink,
      # webrtc, or v8, the custom deps revision of this component must be
      # dynamically set to either:
      # (1) the revision of the builder if this is a tester,
      # (2) 'revision' from the waterfall, or
      # (3) 'HEAD' for forced builds with unspecified 'revision'.
      component_rev = self.m.properties.get('revision') or 'HEAD'

      if bot_type == 'tester':
        component_rev = self.m.properties.get(
            'parent_got_revision', component_rev)
      dep = bot_config.get('set_component_rev')
      self.m.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev

      # Allow bots to configure a list of additional directories of which
      # the revision information will be stored into a build property.
      # This is mainly to make it possible for testers to sync the same revision
      # as the builder for multiple directories.
      for repo_dir, revision_property_name in bot_config.get(
          'extra_got_revision_properties', []):
        revision_property = self.m.properties.get(revision_property_name)
        if revision_property:
          self.m.gclient.c.revisions[repo_dir] = revision_property


  def set_up_swarming(self, bot_config):
    self.m.swarming.check_client_version()

    if bot_config.get('isolate_server'):
      self.m.isolate.isolate_server = bot_config.get('isolate_server')

    if bot_config.get('swarming_server'):
      self.m.swarming.swarming_server = bot_config.get('swarming_server')

    for key, value in bot_config.get('swarming_dimensions', {}).iteritems():
      self.m.swarming.set_default_dimension(key, value)

    if (bot_config.get('swarming_service_account') and
        not self.m.runtime.is_luci):
      self.m.swarming.service_account_json = (
          self.m.puppet_service_account.get_key_path(
              bot_config.get('swarming_service_account')))

    if (bot_config.get('isolate_service_account') and
        not self.m.runtime.is_luci):
      self.m.isolate.service_account_json = (
          self.m.puppet_service_account.get_key_path(
              bot_config.get('isolate_service_account')))

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

  def prepare_checkout(
      self, bot_config, root_solution_revision=None,
      disable_syntax_validation=False):
    update_step = self.m.chromium_checkout.ensure_checkout(
        bot_config, root_solution_revision, disable_syntax_validation)

    if (self.m.chromium.c.compile_py.compiler and
        'goma' in self.m.chromium.c.compile_py.compiler):
      self.m.chromium.ensure_goma(
          client_type=self.m.chromium.c.compile_py.goma_client_type)

    # Installs toolchains configured in the current bot, if any.
    self.m.chromium.ensure_toolchains()

    self.set_up_swarming(bot_config)
    self.runhooks(update_step)

    bot_db = bdb_module.BotConfigAndTestDB()
    bot_config.initialize_bot_db(self, bot_db, update_step)

    return update_step, bot_db

  def generate_tests_from_test_spec(self, test_spec, builder_dict,
      buildername, mastername, swarming_dimensions,
      scripts_compile_targets, generators, bot_update_step, bot_config):
    tests = builder_dict.get('tests', ())
    # TODO(phajdan.jr): Switch everything to scripts generators and simplify.
    for generator in generators:
      tests = (
          tuple(generator(
              self.m, self, mastername, buildername, test_spec,
              bot_update_step,
              swarming_dimensions=swarming_dimensions,
              scripts_compile_targets=scripts_compile_targets)) +
          tuple(tests))
    return tests

  def read_test_spec(self, test_spec_file):
    test_spec_path = self.c.test_spec_dir.join(test_spec_file)
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
      if serialize_tests:
        tests_list = [[t] for t in tests]
      else:
        tests_list = [tests]

      failed_tests = []
      for tl in tests_list:
        failed_ts = self.m.test_utils.run_tests(self.m, tl, suffix)
        failed_tests.extend(failed_ts)

      self.m.swarming.report_stats()

      if failed_tests:
        failed_tests_names = [t.name for t in failed_tests]
        raise self.m.step.StepFailure(
            '%d tests failed: %r' % (len(failed_tests), failed_tests_names))

    return test_runner

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

  def compile_specific_targets(
      self, bot_config, update_step, bot_db,
      compile_targets, tests_including_triggered,
      mb_mastername=None, mb_buildername=None, mb_config_path=None,
      override_bot_type=None):
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
          t.isolate_target
          for t in tests_including_triggered if t.uses_isolate
      ]

      if isolated_targets:
        self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)

      try:
        name_suffix = ''
        if self.m.tryserver.is_tryserver:
          name_suffix=' (with patch)'

        android_version_code = None
        android_version_name = None
        if bot_config.get('android_version'):
          version = self._convert_version(self.m.file.read_text('get version',
              self.m.path['checkout'].join(bot_config.get('android_version')),
              test_data='MAJOR=51\nMINOR=0\nBUILD=2704\nPATCH=0\n'))
          self.log('version:%s' % version)
          android_version_name = ('%s.%s.%s.%s'
              % (version['MAJOR'], version['MINOR'], version['BUILD'], version['PATCH']))
          self.log('android_version_name:%s' % android_version_name)
          # TODO: Consider CPU architecture
          android_version_code = '%d%03d' % (int(version['BUILD']), int(version['PATCH']))
          self.log('android_version_code:%s' % android_version_code)

        self.run_mb_and_compile(compile_targets, isolated_targets,
                                name_suffix=name_suffix,
                                mb_mastername=mb_mastername,
                                mb_buildername=mb_buildername,
                                mb_config_path=mb_config_path,
                                android_version_code=android_version_code,
                                android_version_name=android_version_name)
      except self.m.step.StepFailure:
        self.m.tryserver.set_compile_failure_tryjob_result()
        raise

      if isolated_targets:
        has_patch = self.m.tryserver.is_tryserver
        swarm_hashes_property_name = ''  # By default do not yield as property.
        if 'got_revision_cp' in update_step.presentation.properties:
          # Some recipes such as Findit's may build different revisions in the
          # same build. Hence including the commit position as part of the
          # property name.
          swarm_hashes_property_name = 'swarm_hashes_%s_%s_patch' % (
              update_step.presentation.properties['got_revision_cp'].replace(
                # At sign may clash with annotations format.
                '@', '(at)'), 'with' if has_patch else 'without')

        # 'compile' just prepares all information needed for the isolation,
        # and the isolation is a separate step.
        self.m.isolate.isolate_tests(
            self.m.chromium.output_dir,
            targets=list(set(isolated_targets)),
            verbose=True,
            swarm_hashes_property_name=swarm_hashes_property_name,
            use_exparchive=bot_config.get('force_exparchive', False))

        if bot_config.get('perf_isolate_lookup'):
          change = {
              'commits': [{
                  'repository': 'chromium',
                  'git_hash':
                      update_step.presentation.properties['got_revision'],
              }]
          }

          # FIXME: Move this property into a recipe module.
          deps_revision_overrides = self.m.properties.get(
              'deps_revision_overrides')
          if deps_revision_overrides:
            change['commits'] += (
                {'repository': repository, 'git_hash': git_hash}
                for repository, git_hash in deps_revision_overrides.iteritems())

          if self.m.tryserver.is_tryserver:
            change['patch'] = {
                'server': self.m.properties['patch_gerrit_url'],
                'change': self.m.properties['patch_issue'],
                'revision': self.m.properties['patch_set'],
            }

          self.m.perf_dashboard.upload_isolate(
              self.m.properties['buildername'],
              change,
              self.m.isolate.isolate_server,
              self.m.isolate.isolated_tests)

  def package_build(self, mastername, buildername, update_step, bot_db):
    """Zip and upload the build to google storage.

    This is currently used for transfer between builder and tester,
    including bisect testers.

    Note that:
      - this will only upload when called from pure builders. On builder_testers
        and testers, this is a no-op.
      - this is a no-op for builders that upload to clusterfuzz; those are
        handled in archive_build.
      - this may upload twice on perf builders.
    """
    bot_config = bot_db.get_bot_config(mastername, buildername)

    bot_type = bot_config.get('bot_type')
    assert bot_type == 'builder', (
        'package_build for %s:%s, which is a %s. '
        'This is a bug in your recipe.' % (mastername, buildername, bot_type))

    if not bot_config.get('cf_archive_build'):
      master_config = bot_db.get_master_settings(mastername)
      build_revision = update_step.presentation.properties.get(
          'got_revision',
          update_step.presentation.properties.get('got_src_revision'))


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


  def archive_build(self, mastername, buildername, update_step, bot_db):
    """Archive the build if the bot is configured to do so.

    See api.archive.clusterfuzz_archive and archive_build.py for more
    information.

    This is currently used to store builds long-term and to transfer them
    to clusterfuzz.
    """
    bot_config = bot_db.get_bot_config(mastername, buildername)

    if bot_config.get('archive_build') and not self.m.tryserver.is_tryserver:
      self.m.chromium.archive_build(
          'archive_build',
          bot_config['gs_bucket'],
          bot_config.get('gs_acl'),
          mode='dev',
          build_name=bot_config.get('gs_build_name'),
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

  def trigger_child_builds(self, mastername, buildername, update_step, bot_db,
                           additional_properties=None):
    additional_properties = additional_properties or {}

    # If you modify parameters or properties, make sure to modify it for both
    # legacy and LUCI cases below.
    if not self.m.runtime.is_luci:
      # Legacy buildbot-only triggering.
      # TODO(tandrii): get rid of legacy triggering.
      trigger_specs = []
      for _, loop_mastername, loop_buildername, builder_dict in sorted(
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
        trigger_spec['properties'].update(additional_properties)
        trigger_specs.append(trigger_spec)
      if trigger_specs:
        self.m.trigger(*trigger_specs)
      return

    # LUCI-Scheduler-based triggering (required on luci stack).
    properties = {
      'parent_mastername': mastername,
      'parent_buildername': buildername,
    }
    for name, value in update_step.presentation.properties.iteritems():
      if name.startswith('got_'):
        properties['parent_' + name] = value
    # Work around https://crbug.com/785462 in LUCI UI that ignores
    # buildset's revision and needs actual 'revision' property.
    if 'parent_got_revision' in properties:
      properties['revision'] = properties['parent_got_revision']

    properties.update(additional_properties)

    scheduler_jobs = collections.defaultdict(list)
    for luci_project, loop_mastername, loop_buildername, builder_dict in sorted(
        bot_db.bot_configs_matching_parent_buildername(
            mastername, buildername)):
      # LUCI mode will emulate triggering of builds inside master.chromium*
      # masters which are all mapped into luci.chromium.ci bucket. The
      # triggering will go through LUCI Scheduler to ensure that outstanding
      # triggers get merged if triggered builder (aka loop_buildername) is too
      # slow. LUCI Scheduler `project` is chromium and `job` names are the same
      # as builder names. Config is located here:
      # https://chromium.googlesource.com/chromium/src/+/infra/config/luci-scheduler.cfg
      #
      # Schematically:
      #   <this build> --triggers--> LUCI Scheduler --triggers--> Buildbucket.
      scheduler_jobs[luci_project].append(loop_buildername)

    if scheduler_jobs:
      self.m.scheduler.emit_triggers(
          ((self.m.scheduler.BuildbucketTrigger(properties=properties),
            project, jobs)
           for project, jobs in scheduler_jobs.iteritems()),
          step_name='trigger')

  def run_mb_and_compile(self, compile_targets, isolated_targets, name_suffix,
                         mb_mastername=None, mb_buildername=None,
                         mb_config_path=None, android_version_code=None,
                         android_version_name=None):
    use_goma_module=False
    if self.m.chromium.c.project_generator.tool == 'mb':
      mb_mastername = mb_mastername or self.m.properties['mastername']
      mb_buildername = mb_buildername or self.m.properties['buildername']
      use_goma = (self.m.chromium.c.compile_py.compiler and
                  'goma' in self.m.chromium.c.compile_py.compiler)
      self.m.chromium.run_mb(mb_mastername, mb_buildername,
                             mb_config_path=mb_config_path,
                             use_goma=use_goma,
                             isolated_targets=isolated_targets,
                             name='generate_build_files%s' % name_suffix,
                             android_version_code=android_version_code,
                             android_version_name=android_version_name)
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
    build_revision = (
        build_revision
        or self.m.properties.get('parent_got_revision')
        or update_step.presentation.properties.get('got_revision')
        or update_step.presentation.properties.get('got_src_revision'))
    build_archive_url = build_archive_url or self.m.properties.get(
        'parent_build_archive_url')
    if not build_archive_url:
      master_config = bot_db.get_master_settings(mastername)
      legacy_build_url = self._make_legacy_build_url(master_config, mastername)

    self.m.archive.download_and_unzip_build(
      step_name='extract build',
      target=self.m.chromium.c.build_config_fs,
      build_url=legacy_build_url,
      build_revision=build_revision,
      build_archive_url=build_archive_url)

    self.m.gn.get_args(
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

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
    with self.m.context(
        cwd=self.m.chromium_checkout.working_dir or self.m.path['start_dir'],
        env=self.m.chromium.get_env()):
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ('tester', 'builder_tester'):
        isolated_targets = [
            t.isolate_target
            for t in tests if t.uses_isolate]
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
            bot_id.mastername.startswith('chromium.perf') or
            bot_id.mastername.startswith('tryserver.chromium.perf'))
        self.m.chromium_android.common_tests_setup_steps(perf_setup=perf_setup)

      for test in (tests or []):
        for set_up_step in (test.set_up or []):
          self.m.python(
              set_up_step['name'],
              set_up_step['script'],
              args=set_up_step['args'])
      try:
        yield
      finally:
        for test in (tests or []):
          for tear_down_step in (test.tear_down or []):
            self.m.python(
                tear_down_step['name'],
                tear_down_step['script'],
                args=tear_down_step['args'])

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

    with self.m.context(cwd=self.m.chromium_checkout.working_dir):
      self.m.bot_update.deapply_patch(bot_update_step)

    with self.m.context(cwd=self.m.path['checkout']):
      self.m.chromium.runhooks(name='runhooks (without patch)')

  def _deapply_patch_build_isolate(self, failing_tests, bot_update_step):
    """Deapplies patch. Then builds and isolates failing test suites.

    This method requires that the following steps have occurred:
      * Patch applied
      * Test suites built + isolated
      * Test suites have been run. Some have failures.

    Args:
      failing_tests: An iterable of Test objects. Each represents a failing test
                     suite. The list of exact test failures are stored on the
                     Test object itself.
      bot_update_step: Properties from the update_step when the patch was
                       applied. Used to update presentation properties of the
                       isolate step.
    """
    # The implementation of bot_update.deapply_patch is stateful. It will
    # deapply the patch, but keep the same ToT revision from the initial patch
    # application. bot_update.deapply_patch will update DEPS, since it's
    # possible that the patch was a DEPS change.
    self.deapply_patch(bot_update_step)

    compile_targets = list(itertools.chain(
        *[t.compile_targets(self.m) for t in failing_tests]))
    if compile_targets:
      # Remove duplicate targets.
      compile_targets = sorted(set(compile_targets))
      failing_swarming_tests = [
          t.isolate_target
          for t in failing_tests if t.uses_isolate]
      if failing_swarming_tests:
        self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)
      self.run_mb_and_compile(compile_targets, failing_swarming_tests,
                              ' (without patch)')
      if failing_swarming_tests:
        swarm_hashes_property_name = 'swarm_hashes'
        if 'got_revision_cp' in bot_update_step.presentation.properties:
          swarm_hashes_property_name = 'swarm_hashes_%s_without_patch' % (
              bot_update_step.presentation.properties['got_revision_cp']
              .replace('@', '(at)'))
        self.m.isolate.isolate_tests(
            self.m.chromium.output_dir,
            swarm_hashes_property_name=swarm_hashes_property_name,
            verbose=True)

  def _should_retry_with_patch_deapplied(self, affected_files, disable_deapply_patch):
    """Whether to retry failing test suites with patch deapplied.

    Returns: (should_deapply_patch, deapply_patch_reason)
    """
    if disable_deapply_patch:
      return (False, 'disabled in recipes')

    # We skip the deapply_patch step if there are modifications that affect the
    # recipe itself, since that would potentially invalidate the previous test
    # results.
    exclusion_regexs = [re.compile(path) for path in RECIPE_CONFIG_PATHS]
    for f in affected_files:
      for regex in exclusion_regexs:
        if regex.match(f):
          return (False, 'build config changes detected')

    return (True, None)


  def _run_tests_on_tryserver(self, bot_config, tests, bot_update_step,
                              affected_files,
                              disable_deapply_patch=False):
    """Runs tests with retries.

    This function runs tests with the CL patched in. On failure, this will
    deapply the patch, rebuild/isolate binaries, and run the failing tests.
    """
    with self.wrap_chromium_tests(bot_config, tests):
      should_deapply_patch, deapply_patch_reason = (
          self._should_retry_with_patch_deapplied(affected_files,
                                                  disable_deapply_patch))
      if should_deapply_patch:
        deapply_patch_fn = functools.partial(self._deapply_patch_build_isolate,
                                             bot_update_step=bot_update_step)
        # Runs tests with patch. If there are failures, deapplies patch using
        # deapply_patch_fn, and then runs failing tests again.
        self.m.test_utils.determine_new_failures(
            self.m, tests, deapply_patch_fn)
      else:
        failing_tests = self.m.test_utils.run_tests_with_patch(
            self.m, tests)
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

  def get_common_args_for_scripts(self, bot_config=None):
    args = []

    args.extend(['--build-config-fs', self.m.chromium.c.build_config_fs])

    paths = {
      'checkout': self.m.path['checkout'],
      'runit.py': self.package_repo_resource('scripts', 'tools', 'runit.py'),
      'runtest.py': self.package_repo_resource(
          'scripts', 'slave', 'runtest.py'),
    }
    args.extend(['--paths', self.m.json.input(paths)])

    properties = {}
    # TODO(phajdan.jr): Remove buildnumber when no longer used.

    if not bot_config:
      mastername = self.m.properties.get('mastername')
      buildername = self.m.properties.get('buildername')
      master_dict = self.builders.get(mastername, {})
      bot_config = master_dict.get('builders', {}).get(buildername, {})

    for name in ('buildername', 'bot_id', 'buildnumber', 'mastername'):
      properties[name] = self.m.properties[name]
    properties['slavename'] = properties['bot_id']

    properties['target_platform'] = self.m.chromium.c.TARGET_PLATFORM

    args.extend(['--properties', self.m.json.input(properties)])

    return args

  def get_compile_targets_for_scripts(self, bot_config=None):
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
        ] + self.get_common_args_for_scripts(bot_config),
        step_test_data=lambda: self.m.json.test_api.output({}))
    return result.json.output

  def main_waterfall_steps(self, mb_config_path=None, bot_config=None):
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    if not bot_config:
      bot_config = self.create_generalized_bot_config_object(
          [self.create_bot_id(mastername, buildername)])

    self._report_builders(bot_config)

    self.configure_build(bot_config)
    update_step, bot_db = self.prepare_checkout(bot_config)

    bot_type = bot_config.get('bot_type')

    test_config = bot_config.get_tests(bot_db)
    if bot_type == 'tester':
      isolate_transfer = (
          # Some of the old buildbot trigger infrastructure may not be
          # able to handle the large number of hashes added to trigger
          # properties below (e.g. crbug.com/882889), so we restrict
          # isolate transfer to LUCI.
          self.m.runtime.is_luci and

          all(t.uses_isolate
              for t in test_config.tests_on(mastername, buildername)))
      package_transfer = not isolate_transfer
    else:
      isolate_transfer = (
          # Same as above.
          self.m.runtime.is_luci and

          any(t.uses_isolate
              for t in test_config.tests_triggered_by(mastername, buildername)))
      package_transfer = (
          # Always use package transfer on buildbot.
          not self.m.runtime.is_luci or

          any(not t.uses_isolate
              for t in test_config.tests_triggered_by(mastername, buildername)))

    compile_targets = self.get_compile_targets(
        bot_config, bot_db, test_config.all_tests())
    self.compile_specific_targets(
        bot_config, update_step, bot_db,
        compile_targets, test_config.all_tests(),
        mb_config_path=mb_config_path)

    additional_trigger_properties = {}
    if isolate_transfer:
      additional_trigger_properties['swarm_hashes'] = (
          self.m.isolate.isolated_tests)
    if package_transfer and bot_type == 'builder':
      self.package_build(mastername, buildername, update_step, bot_db)

    self.trigger_child_builds(
        mastername, buildername, update_step, bot_db,
        additional_properties=additional_trigger_properties)
    self.archive_build(mastername, buildername, update_step, bot_db)

    if isolate_transfer and bot_type == 'tester':
      self.m.file.rmtree(
        'build directory',
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))
    if package_transfer:
      self.download_and_unzip_build(mastername, buildername, update_step, bot_db)

    tests = test_config.tests_on(mastername, buildername)
    if not tests:
      return

    self.m.chromium_swarming.configure_swarming(
        'chromium', precommit=False, mastername=mastername)
    test_runner = self.create_test_runner(
        tests, serialize_tests=bot_config.get('serialize_tests'))
    with self.wrap_chromium_tests(bot_config, tests):
      test_runner()

  def trybot_steps(self, builders=None, trybots=None):
    with self.m.tryserver.set_failure_hash():
      (bot_config_object, bot_update_step, affected_files, tests,
       disable_deapply_patch) = self._trybot_steps_internal(
           builders=builders, trybots=trybots)

      self.m.python.succeeding_step('mark: before_tests', '')
      if tests:
        self._run_tests_on_tryserver(
            bot_config_object, tests, bot_update_step,
            affected_files, disable_deapply_patch=disable_deapply_patch)
        self.m.swarming.report_stats()

  def _trybot_steps_internal(self, builders=None, trybots=None):
    """Initial configuration for all trybots.

    The main purpose of this method is to determine which tests need to be run.

    Args:
      builders: An optional mapping from <mastername, buildername> to
                build/test settings. For an example of defaults for chromium,
                see scripts/slave/recipe_modules/chromium_tests/chromium.py
      trybots: An optional mapping from <mastername, buildername> of the trybot to
               configurations of the mirrored CI bot. Defaults are in
               ChromiumTestsApi.

    Returns: [a 5-tuple of the following]
      bot_config_object: Configuration for the tests to be run.
      bot_update_step: Holds state on build properties. Used to pass state between
                       methods.
      affected_files: A list of paths affected by the CL.
      tests: A list of Test objects [see chromium_tests/steps.py]. Stateful
             objects that can run tests [possibly remotely via swarming] and parse
             the results. Running tests multiple times is not idempotent -- the
             results of previous runs affect future runs.
      disable_deapply_patch: A flag that prevents the "deapply patch" series of
                             steps from running.
    """
    # Most trybots mirror a CI bot. They run the same suite of tests with the
    # same configuration.
    # This logic takes the <mastername, buildername> of the triggering trybot,
    # and looks up the configuration of the mirrored bot. For example,
    # <tryserver.chromium.mac, mac_chromium_dbg_ng> will return:
    # {
    #   'bot_ids': {
    #                'mastername': 'chromium.mac',
    #                'buildername': 'Mac Builder (dbg)',
    #                'tester': 'Mac10.13 Tests (dbg)',
    #              },
    #   'analyze_mode': None
    # }
    # See ChromiumTestsApi for more details.
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    trybot_config = (trybots or self.trybots).get(mastername, {}).get(
        'builders', {}).get(buildername)

    # Some trybots do not mirror a CI bot. In this case, return a configuration
    # that uses the same <mastername, buildername> of the triggering trybot.
    if not trybot_config:
      trybot_config = {
        'bot_ids': [self.create_bot_id(mastername, buildername)],
      }

    # bot_config_object contains build/test settings for the mirrored
    # <mastername, buildername>.
    bot_config_object = self.create_generalized_bot_config_object(
        trybot_config['bot_ids'], builders=builders)

    self._report_builders(bot_config_object)
    self.set_precommit_mode()

    # Applies build/test configurations from bot_config_object.
    self.configure_build(bot_config_object, override_bot_type='builder_tester')

    self.m.chromium_swarming.configure_swarming('chromium', precommit=True)

    self.m.chromium.apply_config('trybot_flavor')

    # This rolls chromium checkout, applies the patch, runs gclient sync to
    # update all DEPS.
    bot_update_step, bot_db = self.prepare_checkout(bot_config_object)

    # Determine the tests that would be run if this were a CI tester.
    # Tests are instances of class(Test) from chromium_tests/steps.py. These
    # objects know how to dispatch isolate tasks, parse results, and keep
    # state on the results of previous test runs.
    test_config = self.get_tests(bot_config_object, bot_db)
    tests = test_config.tests_in_scope()
    tests_including_triggered = test_config.all_tests()

    affected_files = self.m.chromium_checkout.get_files_affected_by_patch()

    if self.m.tryserver.is_tryserver:
      self.m.tryserver.set_subproject_tag('chromium')

    # Determine the compile targets for the tests that would be run.
    compile_targets = self.get_compile_targets(
        bot_config_object,
        bot_db,
        test_config.all_tests())
    test_targets = sorted(set(
        self._all_compile_targets(test_config.all_tests())))

    # Use analyze to determine the compile targets that are affected by the CL.
    # Use this to prune the relevant compile targets and test targets.
    if self.m.tryserver.is_tryserver:
      additional_compile_targets = sorted(
          set(compile_targets) - set(test_targets))
      analyze_names = ['chromium'] + list(trybot_config.get('analyze_names', []))
      mb_config_path = (
          self.m.chromium.c.project_generator.config_path
          or self.m.path['checkout'].join('tools', 'mb', 'mb_config.pyl'))
      test_targets, compile_targets = self.m.filter.analyze(
          affected_files, test_targets, additional_compile_targets,
          'trybot_analyze_config.json',
          mb_mastername=mastername,
          mb_buildername=buildername,
          mb_config_path=mb_config_path,
          additional_names=analyze_names)

    # If this is a compile-only trybot, then clear our all tests. This cannot be
    # done sooner because we still want to determine the minimal set of binaries
    # that need to be compiled, which requires knowing the set of tests that
    # would be run.
    if trybot_config.get('analyze_mode') == 'compile':
      tests = []
      tests_including_triggered = []

    # Compiles and isolates test suites.
    if compile_targets:
      tests = self._tests_in_compile_targets(test_targets, tests)
      tests_including_triggered = self._tests_in_compile_targets(
          test_targets, tests_including_triggered)

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
        tests = [t for t in tests if not t.compile_targets(self.m)]
      else:
        tests = []

    # A special configuration to disable the deapply_patch step for
    # mac_optional_gpu_tests_rel. This should not be necessary. See
    # https://crbug.com/883308.
    disable_deapply_patch = not trybot_config.get('deapply_patch', True)
    return (bot_config_object, bot_update_step, affected_files, tests,
            disable_deapply_patch)

  def _report_builders(self, bot_config):
    """Reports the builders being executed by the bot."""
    def present_bot(bot_id):
      if bot_id.tester:
        return ('running tester %r on master %r against builder %r on master %r'
                % (bot_id.tester, bot_id.tester_mastername,
                   bot_id.buildername, bot_id.mastername))
      bot_type = bot_config.get_bot_type(bot_id)
      if bot_type == 'builder_tester':
        bot_type = 'builder/tester'
      return ('running %s %r on master %r'
              % (bot_type, bot_id.buildername, bot_id.mastername))


    lines = [''] + [present_bot(b) for b in bot_config.bot_ids]
    self.m.python.succeeding_step('report builders', '<br/>'.join(lines))

  def _all_compile_targets(self, tests):
    """Returns the compile_targets for all the Tests in |tests|."""
    return sorted(set(x
                      for test in tests
                      for x in test.compile_targets(self.m)))

  def _is_source_file(self, filepath):
    """Returns true iff the file is a source file."""
    _, ext = self.m.path.splitext(filepath)
    return ext in ['.c', '.cc', '.cpp', '.h', '.java', '.mm']

  def _tests_in_compile_targets(self, compile_targets, tests):
    """Returns the tests in |tests| that have at least one of their compile
    targets in |compile_targets|."""
    result = []
    for test in tests:
      test_compile_targets = test.compile_targets(self.m)
      # Always return tests that don't require compile. Otherwise we'd never
      # run them.
      if ((set(compile_targets) & set(test_compile_targets)) or
          not test_compile_targets):
        result.append(test)
    return result

  def _convert_version(self, version):
    """ Convert the version string to a dict. """
    output = {}
    for line in version.splitlines():
      [k,v] = line.split('=', 1)
      output[k] = v
    return output
