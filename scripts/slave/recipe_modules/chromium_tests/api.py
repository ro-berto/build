# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import contextlib
import copy
import itertools
import json
import re
import traceback

from recipe_engine.types import freeze
from recipe_engine import recipe_api

from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

from RECIPE_MODULES.build import chromium

from . import bot_config as bot_config_module
from . import bot_spec
from . import builders as builders_module
from . import generators
from . import trybots as trybots_module
from . import steps


# Paths which affect recipe config and behavior in a way that survives
# deapplying user's patch.
RECIPE_CONFIG_PATHS = [
  'testing/buildbot/.*json$',
  'testing/buildbot/.*pyl$',
]

class BotMetadata(object):

  def __init__(self, builder_id, config, settings):
    self.builder_id = builder_id
    self.config = config
    self.settings = settings

  def is_compile_only(self):
    return self.config.get('analyze_mode') == 'compile'

class Task(object):
  """Represents the configuration for build/test tasks.

  The fields in the task are immutable.

  Attributes:
    bot: BotMetadata of the task runner bot.
    bot_update_step: Holds state on build properties. Used to pass state
                     between methods.
    tests: A list of Test objects [see chromium_tests/steps.py]. Stateful
           objects that can run tests [possibly remotely via swarming] and
           parse the results. Running tests multiple times is not idempotent
           -- the results of previous runs affect future runs.
      affected_files: A list of paths affected by the CL.
  """

  def __init__(self, bot, test_suites, bot_update_step, affected_files):
    self._bot = bot
    self._test_suites = test_suites
    self._bot_update_step = bot_update_step
    self._affected_files = affected_files

  @property
  def bot(self):
    return self._bot

  @property
  def test_suites(self):
    return self._test_suites

  @property
  def bot_update_step(self):
    return self._bot_update_step

  @property
  def affected_files(self):
    return self._affected_files

  def should_retry_failures_with_changes(self):
    return self.bot.config.get('retry_failed_shards', True)

class ChromiumTestsApi(recipe_api.RecipeApi):
  BotMetadata = BotMetadata
  Task = Task

  def __init__(self, input_properties, **kwargs):
    super(ChromiumTestsApi, self).__init__(**kwargs)
    self._builders = builders_module.BUILDERS
    self._bucketed_triggers = input_properties.bucketed_triggers

  @property
  def builders(self):
    return self._builders

  @property
  def trybots(self):
    return trybots_module.TRYBOTS

  def log(self, message):
    presentation = self.m.step.active_result.presentation
    presentation.logs.setdefault('stdout', []).append(message)

  def create_bot_config_object(self, builder_ids_or_bot_mirrors, builders=None):
    try:
      return bot_config_module.BotConfig(builders or self.builders,
                                         builder_ids_or_bot_mirrors)
    except Exception:
      if (self._test_data.enabled and
          not self._test_data.get('handle_bot_config_errors', True)):
        raise  # pragma: no cover
      self.m.python.failing_step(
          'Incorrect or missing bot configuration',
          [traceback.format_exc()],
          as_log='details')

  def get_config_defaults(self):
    return {'CHECKOUT_PATH': self.m.path['checkout']}

  def _chromium_config(self, bot_config):
    chromium_config = self.m.chromium.make_config(
        bot_config.get('chromium_config'),
        **bot_config.get('chromium_config_kwargs', {}))

    for c in bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c, chromium_config)

    return chromium_config

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

    if self.m.chromium.c.TARGET_CROS_BOARD:
      self.m.gclient.c.solutions[0].custom_vars['cros_board'] = (
          self.m.chromium.c.TARGET_CROS_BOARD)

    for c in bot_config.get('android_apply_config', []):
      self.m.chromium_android.apply_config(c)

    for c in bot_config.get('chromium_tests_apply_config', []):
      self.apply_config(c)

    bot_type = override_bot_type or bot_config.get('bot_type',
                                                   bot_spec.BUILDER_TESTER)

    if bot_config.get('set_component_rev'):
      # If this is a component build and the main revision is e.g. blink,
      # webrtc, or v8, the custom deps revision of this component must be
      # dynamically set to either:
      # (1) the revision of the builder if this is a tester,
      # (2) gitiles commit id from the waterfall, or
      # (3) 'HEAD' for forced builds with unspecified gitiles commit.
      component_rev = self.m.buildbucket.gitiles_commit.id or 'HEAD'

      if bot_type == bot_spec.TESTER:
        component_rev = self.m.properties.get(
            'parent_got_revision', component_rev)
      dep = bot_config.get('set_component_rev')
      self.m.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev


  def set_up_swarming(self, bot_config):
    self.m.chromium_swarming.check_client_version()

    if bot_config.get('isolate_server'):
      self.m.isolate.isolate_server = bot_config.get('isolate_server')

    if bot_config.get('swarming_server'):
      self.m.chromium_swarming.swarming_server = bot_config.get(
          'swarming_server')

    for key, value in bot_config.get('swarming_dimensions', {}).iteritems():
      self.m.chromium_swarming.set_default_dimension(key, value)

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

  def prepare_checkout(self, bot_config, **kwargs):
    update_step = self.m.chromium_checkout.ensure_checkout(bot_config, **kwargs)

    if (self.m.chromium.c.compile_py.compiler and
        'goma' in self.m.chromium.c.compile_py.compiler):
      self.m.chromium.ensure_goma(
          client_type=self.m.chromium.c.compile_py.goma_client_type)

    # Installs toolchains configured in the current bot, if any.
    self.m.chromium.ensure_toolchains()

    self.set_up_swarming(bot_config)
    self.runhooks(update_step)

    build_config = bot_config.create_build_config(self, update_step)

    return update_step, build_config

  def generate_tests_from_source_side_spec(self, source_side_spec, builder_dict,
      buildername, mastername, swarming_dimensions,
      scripts_compile_targets, bot_update_step):
    tests = builder_dict.get('tests', ())
    # TODO(phajdan.jr): Switch everything to scripts generators and simplify.
    for generator in generators.ALL_GENERATORS:
      tests = (
          tuple(generator(
              self.m, self, mastername, buildername, source_side_spec,
              bot_update_step,
              swarming_dimensions=swarming_dimensions,
              scripts_compile_targets=scripts_compile_targets)) +
          tuple(tests))
    return tests

  def read_source_side_spec(self, source_side_spec_file):
    source_side_spec_path = self.m.chromium.c.source_side_spec_dir.join(
        source_side_spec_file)
    spec_result = self.m.json.read(
        'read test spec (%s)' % self.m.path.basename(source_side_spec_path),
        source_side_spec_path,
        step_test_data=lambda: self.m.json.test_api.output({}))
    spec_result.presentation.step_text = 'path: %s' % source_side_spec_path
    source_side_spec = spec_result.json.output

    return source_side_spec

  def create_test_runner(self, tests, suffix='', serialize_tests=False,
                         retry_failed_shards=False, retry_invalid_shards=False):
    """Creates a test runner to run a set of tests.

    Args
      api: API of the calling recipe.
      tests: List of step.Test objects to be run.
      suffix: Suffix to be passed when running the tests.
      serialize_tests: True if this bot should run all tests serially
        (specifically, tests run on Swarming). Used to reduce the load
        generated by waterfall bots.
      retry_failed_shards: If true, retry swarming tests that fail. See
        run_tests documentation in test_utils module.
      retry_invalid_shards: If true, retry swarming tests with no valid results,
        See run_tests documentation in test_utils module.

    Returns:
      A function that can be passed to setup_chromium_tests or run directly.

    """

    def test_runner():
      if serialize_tests:
        tests_list = [[t] for t in tests]
      else:
        tests_list = [tests]

      failed_tests = set()
      for tl in tests_list:
        invalid_ts, failed_ts = self.m.test_utils.run_tests(
            self.m, tl, suffix, retry_failed_shards=retry_failed_shards,
            retry_invalid_shards=retry_invalid_shards)
        failed_tests = failed_tests.union(failed_ts, invalid_ts)

      self.m.chromium_swarming.report_stats()

      if failed_tests:
        return result_pb2.RawResult(
            status=common_pb.FAILURE,
            summary_markdown=self._format_unrecoverable_failures(
                failed_tests, suffix)
        )

    return test_runner

  def get_compile_targets(self, bot_config, build_config, tests):
    assert isinstance(build_config, bot_config_module.BuildConfig), \
        "build_config argument %r was not a BuildConfig" % (build_config)

    compile_targets = bot_config.get_compile_targets(self, build_config, tests)
    return sorted(set(compile_targets))

  _ARCHITECTURE_DIGIT_MAP = {
      ('arm', 32): 0,
      ('arm', 64): 5,
      ('intel', 32): 1,
      ('intel', 64): 6,
      ('mips', 32): 2,
  }

  def get_android_version_details(self, bot_config, log_details=False):
    version = bot_config.get('android_version')
    if not version:
      return None, None

    version = self.m.chromium.get_version_from_file(
        self.m.path['checkout'].join(version))

    chromium_config = self.m.chromium.c
    arch_id = chromium_config.TARGET_ARCH, chromium_config.TARGET_BITS
    arch_digit = self._ARCHITECTURE_DIGIT_MAP.get(arch_id, None)
    assert arch_digit is not None, (
        'Architecture and bits (%r) does not have a version digit assigned'
        % arch_id)

    android_version_name = '%(MAJOR)s.%(MINOR)s.%(BUILD)s.%(PATCH)s' % version
    android_version_code = '%d%03d%d0' % (int(version['BUILD']),
                                          int(version['PATCH']),
                                          arch_digit)
    if log_details:
      self.log('version:%s' % version)
      self.log('android_version_name:%s' % android_version_name)
      self.log('android_version_code:%s' % android_version_code)
    return android_version_name, android_version_code

  def _use_goma(self, chromium_config=None):
    chromium_config = chromium_config or self.m.chromium.c
    return (chromium_config.compile_py.compiler and
            'goma' in chromium_config.compile_py.compiler)

  def compile_specific_targets(self,
                               bot_config,
                               update_step,
                               build_config,
                               compile_targets,
                               tests_including_triggered,
                               builder_id=None,
                               mb_phase=None,
                               mb_config_path=None,
                               mb_recursive_lookup=False,
                               override_bot_type=None):
    """Runs compile and related steps for given builder.

    Allows finer-grained control about exact compile targets used.

    Args:
      bot_config - The configuration for the bot being executed.
      update_step - The StepResult from the bot_update step.
      build_config - The configuration of the current build.
      compile_targets - The list of targets to compile.
      tests_including_triggered - The list of tests that will be executed by
        this builder and any triggered builders. The compile operation will
        prepare and upload the isolates for the tests that use isolate.
      builder_id - A BuilderId identifying the configuration to use when running
        mb. If not provided, `chromium.get_builder_id()` will be used.
      mb_phase - A phase argument to be passed to mb. Must be provided if the
        configuration identified by `builder_id` uses phases and must not be
        provided if the configuration identified by `builder_id` does not use
        phases.
      mb_config_path - An optional override specifying the file where mb will
        read configurations from.
      mb_recursive_lookup - A boolean indicating whether the lookup operation
        should recursively expand any included files. If False, then the lookup
        output will contain the include statement.
      override_bot_type - An optional override to change the bot type.

    Returns:
      RawResult object with compile step status and failure message
    """

    assert isinstance(build_config, bot_config_module.BuildConfig), \
        "build_config argument %r was not a BuildConfig" % (build_config)
    bot_type = override_bot_type or bot_config.get('bot_type',
                                                   bot_spec.BUILDER_TESTER)

    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.clean_local_files()
      self.m.chromium_android.run_tree_truth()

    if bot_type in bot_spec.BUILDER_TYPES:
      isolated_targets = [
          t.isolate_target
          for t in tests_including_triggered if t.uses_isolate
      ]

      if isolated_targets:
        self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)

      name_suffix = ''
      if self.m.tryserver.is_tryserver:
        name_suffix=' (with patch)'

      android_version_name, android_version_code = (
          self.get_android_version_details(bot_config, log_details=True))

      raw_result = self.run_mb_and_compile(
          compile_targets,
          isolated_targets,
          name_suffix=name_suffix,
          builder_id=builder_id,
          mb_phase=mb_phase,
          mb_config_path=mb_config_path,
          mb_recursive_lookup=mb_recursive_lookup,
          android_version_code=android_version_code,
          android_version_name=android_version_name)

      if raw_result.status != common_pb.SUCCESS:
        self.m.tryserver.set_compile_failure_tryjob_result()
        return raw_result

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
            suffix=name_suffix,
            targets=list(set(isolated_targets)),
            verbose=True,
            swarm_hashes_property_name=swarm_hashes_property_name)

        if bot_config.get('perf_isolate_lookup'):
          self.m.perf_dashboard.upload_isolate(
              self.m.buildbucket.builder_name,
              self.m.perf_dashboard.get_change_info([{
                  'repository': 'chromium',
                  'git_hash':
                      update_step.presentation.properties['got_revision'],
              }]),
              self.m.isolate.isolate_server,
              self.m.isolate.isolated_tests)
      return raw_result

  def package_build(self, builder_id, update_step, build_config, reasons=None):
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
    bot_config = build_config.get_bot_config(builder_id)

    bot_type = bot_config.get('bot_type')
    assert bot_type in bot_spec.BUILDER_TYPES, (
        'Called package_build for %s:%s, which is a "%s". '
        'package_build only supports "builder" and "builder_tester". '
        'This is a bug in your recipe.' % (builder_id.master,
                                           builder_id.builder, bot_type))

    if not bot_config.get('cf_archive_build'):
      master_config = build_config.get_master_settings(builder_id.master)
      build_revision = update_step.presentation.properties.get(
          'got_revision',
          update_step.presentation.properties.get('got_src_revision'))


      # For archiving 'chromium.perf', the builder also archives a version
      # without perf test files for manual bisect.
      # (https://bugs.chromium.org/p/chromium/issues/detail?id=604452)
      if (master_config.get('bisect_builders') and
          builder_id.builder in master_config.get('bisect_builders') and
          'bisect_build_gs_bucket' in master_config):
        bisect_package_step = self.m.archive.zip_and_upload_build(
            'package build for bisect',
            self.m.chromium.c.build_config_fs,
            build_url=self._build_bisect_gs_archive_url(master_config),
            build_revision=build_revision,
            cros_board=self.m.chromium.c.TARGET_CROS_BOARD,
            update_properties=update_step.presentation.properties,
            exclude_perf_test_files=True,
            store_by_hash=False,
            platform=self.m.chromium.c.TARGET_PLATFORM
        )
        bisect_reasons = list(reasons or [])
        bisect_reasons.extend([
            ' - %s is listed in bisect_builders' % builder_id.builder,
            ' - bisect_build_gs_bucket is configured to %s' %
            master_config.get('bisect_build_gs_bucket'),
        ])
        bisect_package_step.presentation.logs['why is this running?'] = (
            bisect_reasons)

      if 'build_gs_bucket' in master_config:
        package_step = self.m.archive.zip_and_upload_build(
            'package build',
            self.m.chromium.c.build_config_fs,
            build_url=self._build_gs_archive_url(
                builder_id.master, master_config, builder_id.builder),
            build_revision=build_revision,
            cros_board=self.m.chromium.c.TARGET_CROS_BOARD,
            # TODO(machenbach): Make asan a configuration switch.
            package_dsym_files=(self.m.chromium.c.runtests.enable_asan and
                                self.m.chromium.c.HOST_PLATFORM == 'mac'),
        )
        standard_reasons = list(reasons or [])
        standard_reasons.extend([
            ' - build_gs_bucket is configured to %s'
                % master_config.get('build_gs_bucket'),
        ])
        package_step.presentation.logs['why is this running?'] = (
            standard_reasons)


  def archive_build(self, builder_id, update_step, build_config):
    """Archive the build if the bot is configured to do so.

    See api.archive.clusterfuzz_archive and archive_build.py for more
    information.

    This is currently used to store builds long-term and to transfer them
    to clusterfuzz.
    """
    bot_config = build_config.get_bot_config(builder_id)

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

  def _get_scheduler_jobs_to_trigger(self, builder_id, build_config):
    """Get the LUCI scheduler jobs to trigger.

    Child builds are triggered through LUCI scheduler rather than buildbucket
    so that if so configured, multiple outstanding triggers are collapsed into a
    single build (e.g. a CI builder completes multiple builds during a CI tester
    run, only a single additional run of the test occurs).
    """
    get_job_name = lambda buildername: buildername
    if self._bucketed_triggers:
      prefix = self.m.buildbucket.build.builder.bucket + '-'
      get_job_name = lambda buildername: prefix + buildername

    scheduler_jobs = collections.defaultdict(list)
    for luci_project, _, loop_buildername, _ in sorted(
        build_config.bot_configs_matching_parent_buildername(builder_id)):
      job = get_job_name(loop_buildername)
      scheduler_jobs[luci_project].append(job)

    return scheduler_jobs

  def trigger_child_builds(self,
                           builder_id,
                           update_step,
                           build_config,
                           additional_properties=None):
    additional_properties = additional_properties or {}

    # LUCI-Scheduler-based triggering (required on luci stack).
    properties = {
        'parent_mastername': builder_id.master,
        'parent_buildername': builder_id.builder,
    }
    for name, value in update_step.presentation.properties.iteritems():
      if name.startswith('got_'):
        properties['parent_' + name] = value
    # Work around https://crbug.com/785462 in LUCI UI that ignores
    # buildset's revision and needs actual 'revision' property.
    if 'parent_got_revision' in properties:
      properties['revision'] = properties['parent_got_revision']

    properties.update(additional_properties)

    scheduler_jobs = self._get_scheduler_jobs_to_trigger(
        builder_id, build_config)

    if scheduler_jobs:
      self.m.scheduler.emit_triggers(
          ((self.m.scheduler.BuildbucketTrigger(properties=properties),
            project, jobs)
           for project, jobs in scheduler_jobs.iteritems()),
          step_name='trigger')

  def run_mb_and_compile(self,
                         compile_targets,
                         isolated_targets,
                         name_suffix,
                         builder_id=None,
                         mb_phase=None,
                         mb_config_path=None,
                         mb_recursive_lookup=False,
                         android_version_code=None,
                         android_version_name=None):
    with self.m.chromium.guard_compile(suffix=name_suffix):
      use_goma_module = False
      if self.m.chromium.c.project_generator.tool == 'mb':
        builder_id = builder_id or self.m.chromium.get_builder_id()
        use_goma = self._use_goma()
        self.m.chromium.mb_gen(
            builder_id,
            phase=mb_phase,
            mb_config_path=mb_config_path,
            use_goma=use_goma,
            isolated_targets=isolated_targets,
            name='generate_build_files%s' % name_suffix,
            recursive_lookup=mb_recursive_lookup,
            android_version_code=android_version_code,
            android_version_name=android_version_name)
        if use_goma:
          use_goma_module = True

      return self.m.chromium.compile(
          compile_targets,
          name='compile%s' % name_suffix,
          use_goma_module=use_goma_module)

  def download_and_unzip_build(self,
                               builder_id,
                               update_step,
                               build_config,
                               build_archive_url=None,
                               build_revision=None,
                               override_bot_type=None,
                               read_gn_args=True):
    assert isinstance(build_config, bot_config_module.BuildConfig), \
        "build_config argument %r was not a BuildConfig" % (build_config)
    # We only want to do this for tester bots (i.e. those which do not compile
    # locally).
    bot_type = override_bot_type or build_config.get_bot_config(builder_id).get(
        'bot_type')
    if bot_type != bot_spec.TESTER:  # pragma: no cover
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
      master_config = build_config.get_master_settings(builder_id.master)
      legacy_build_url = self._make_legacy_build_url(master_config,
                                                     builder_id.master)

    self.m.archive.download_and_unzip_build(
      step_name='extract build',
      target=self.m.chromium.c.build_config_fs,
      build_url=legacy_build_url,
      build_revision=build_revision,
      build_archive_url=build_archive_url)

    if read_gn_args:
      self.m.gn.get_args(
          self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

  def _make_legacy_build_url(self, master_config, mastername):
    # The master where the build was zipped and uploaded from.
    source_master = self.m.properties.get('parent_mastername')
    # TODO(gbeaty) I think this can be removed, this method is only used when
    # downloading and unzipping a build, which should always be on a builder
    # triggered, which will have the parent_mastername property set
    if not source_master:
      source_master = self.m.properties['mastername']  # pragma: no cover
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
      bot_type = bot_config.get('bot_type', bot_spec.BUILDER_TESTER)

      if bot_type in bot_spec.TESTER_TYPES:
        isolated_targets = [
            t.isolate_target
            for t in tests if t.uses_isolate]
        if isolated_targets:
          self.m.isolate.find_isolated_tests(self.m.chromium.output_dir)

      # Some recipes use this wrapper to setup devices and have their own way
      # to run tests. If platform is Android and tests is None, run device
      # steps.
      require_device_steps = (tests is None or
                              any([t.uses_local_devices for t in tests]))

      if (self.m.chromium.c.TARGET_PLATFORM == 'android' and
          require_device_steps):

        def is_perf(mastername):
          return any(
              mastername.startswith(m)
              for m in ('chromium.perf', 'tryserver.chromium.perf'))

        #TODO(prasadv): Remove this hack and implement specific functions
        # at the point of call.
        perf_setup = any(is_perf(b.master) for b in bot_config.builder_ids)
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

  def _build_and_isolate_failing_tests(self, failing_tests, bot_update_step,
                                       suffix):
    """Builds and isolates test suites in |failing_tests|.

    Args:
      failing_tests: An iterable of test_suites that need to be rebuilt.
      bot_update_step: Contains information about the current checkout. Used to
                       set swarming properties.
      suffix: Should be 'without patch'. Used to annotate steps and swarming
              properties.

    Returns:
      A RawResult object with the failure message and status
    """
    compile_targets = list(itertools.chain(
        *[t.compile_targets() for t in failing_tests]))
    if compile_targets:
      # Remove duplicate targets.
      compile_targets = sorted(set(compile_targets))
      failing_swarming_tests = [
          t.isolate_target
          for t in failing_tests if t.uses_isolate]
      if failing_swarming_tests:
        self.m.isolate.clean_isolated_files(self.m.chromium.output_dir)
      raw_result = self.run_mb_and_compile(
          compile_targets,
          failing_swarming_tests,
          ' (%s)' % suffix
      )
      if raw_result:
        # Clobber the bot upon compile failure without patch.
        # See crbug.com/724533 for more detail.
        if raw_result.status == common_pb.FAILURE:
          self.m.file.rmtree('clobber', self.m.chromium.output_dir)

        if raw_result.status != common_pb.SUCCESS:
          return raw_result

      if failing_swarming_tests:
        swarm_hashes_property_name = 'swarm_hashes'
        if 'got_revision_cp' in bot_update_step.presentation.properties:
          revision_cp = (bot_update_step.
              presentation.properties['got_revision_cp'].replace('@', '(at)'))
          swarm_hashes_property_name = 'swarm_hashes_%s_%s' % (
              revision_cp, suffix.replace(' ', '_'))
        self.m.isolate.isolate_tests(
            self.m.chromium.output_dir,
            suffix=' (%s)' % suffix,
            swarm_hashes_property_name=swarm_hashes_property_name,
            verbose=True)

  def _should_retry_with_patch_deapplied(self, affected_files):
    """Whether to retry failing test suites with patch deapplied.

    Returns: Boolean
    """
    # We skip the deapply_patch step if there are modifications that affect the
    # recipe itself, since that would potentially invalidate the previous test
    # results.
    exclusion_regexs = [re.compile(path) for path in RECIPE_CONFIG_PATHS]
    for f in affected_files:
      for regex in exclusion_regexs:
        if regex.match(f):
          return False

    return True

  def _run_tests_with_retries(self, task, deapply_changes):
    """This function runs tests with the CL patched in. On failure, this will
    deapply the patch, rebuild/isolate binaries, and run the failing tests.

    Returns:
      A Tuple of
        A RawResult object with the failure message and status
          A non-None value here means test were not run and compile failed,
        An array of test suites which irrecoverably failed.
          If all test suites succeeded, returns an empty array.
    """
    with self.wrap_chromium_tests(task.bot.settings, task.test_suites):
      # Run the test. The isolates have already been created.
      invalid_test_suites, failing_test_suites = (
          self.m.test_utils.run_tests_with_patch(
              self.m,
              task.test_suites,
              retry_failed_shards=task.should_retry_failures_with_changes()))

      if self.m.code_coverage.using_coverage:
        self.m.code_coverage.process_coverage_data(task.test_suites)

      def summarize_all_test_failures_with_no_retries():
        for t in task.test_suites:
          if t.has_failures_to_summarize():
            self.m.test_utils.summarize_failing_test_with_no_retries(self.m, t)

      if invalid_test_suites:
        summarize_all_test_failures_with_no_retries()
        return None, invalid_test_suites

      if not failing_test_suites:
        summarize_all_test_failures_with_no_retries()
        return None, []

      # If there are failures but we shouldn't deapply the patch, then we're
      # done.
      if not self._should_retry_with_patch_deapplied(task.affected_files):
        self.m.python.succeeding_step(
            'without patch steps are skipped',
            '<br/>because this CL changed following recipe config paths:<br/>' +
            '<br/>'.join(RECIPE_CONFIG_PATHS))

        for t in task.test_suites:
          if t.has_failures_to_summarize():
            self.m.test_utils.summarize_failing_test_with_no_retries(self.m, t)
        return None, failing_test_suites

      deapply_changes(task.bot_update_step)
      raw_result = self._build_and_isolate_failing_tests(
          failing_test_suites, task.bot_update_step, 'without patch')
      if raw_result and raw_result.status != common_pb.SUCCESS:
        return raw_result, []

      self.m.test_utils.run_tests(
          self.m, failing_test_suites, 'without patch', sort_by_shard=True)

      unrecoverable_test_suites = []
      for t in task.test_suites:
        if not t.has_failures_to_summarize():
          continue

        if t not in failing_test_suites:
          # 'Without patch' steps only apply to failed test suites, so when a
          # test suite didn't fail, but still has failures to summarize
          # (known flaky failures), it is summarized in a way that
          # "without patch" step didn't happen.
          self.m.test_utils.summarize_failing_test_with_no_retries(self.m, t)
          continue

        if not self.m.test_utils.summarize_test_with_patch_deapplied(self.m, t):
          unrecoverable_test_suites.append(t)

      return None, unrecoverable_test_suites

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
    else:
      return self.m.archive.legacy_upload_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=self.m.properties['mastername'])

  def get_common_args_for_scripts(self, bot_config=None):
    args = []

    args.extend(['--build-config-fs', self.m.chromium.c.build_config_fs])

    paths = {
      'checkout': self.m.path['checkout'],
      'runit.py': self.repo_resource('scripts', 'tools', 'runit.py'),
      'runtest.py': self.repo_resource(
          'scripts', 'slave', 'runtest.py'),
    }
    args.extend(['--paths', self.m.json.input(paths)])

    properties = {}
    # TODO(phajdan.jr): Remove buildnumber when no longer used.

    if not bot_config:
      mastername = self.m.properties.get('mastername')
      buildername = self.m.buildbucket.builder_name
      master_dict = self.builders.get(mastername, {})
      bot_config = master_dict.get('builders', {}).get(buildername, {})

    properties['buildername'] = self.m.buildbucket.builder_name
    properties['buildnumber'] = self.m.buildbucket.build.number
    for name in ('bot_id', 'mastername'):
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

  def main_waterfall_steps(self, mb_config_path=None, builders=None):
    """Compiles and runs tests for chromium recipe.

    Returns:
      - A RawResult object with the status of the build
        and a failure message if a failure occurred.
      - None if no failures
    """
    bot = self.lookup_bot_metadata(builders)
    self.configure_build(bot.settings)
    # TODO(crbug.com/1019824): We fetch tags here because |no_fetch_tags|
    # is not specified as True. Since chromium has 10k+ tags this can be slow.
    # We should pass False here for bots that do not need tags. (Do any bots
    # need tags?)
    update_step, build_config = self.prepare_checkout(
        bot.settings, timeout=3600)

    bot_type = bot.settings.get('bot_type')
    if bot_type == bot_spec.TESTER:
      self._lookup_builder_gn_args(bot, mb_config_path, builders)

    compile_targets = self.get_compile_targets(bot.settings, build_config,
                                               build_config.all_tests())
    compile_result = self.compile_specific_targets(
        bot.settings,
        update_step,
        build_config,
        compile_targets,
        build_config.all_tests(),
        mb_config_path=mb_config_path)

    if compile_result and compile_result.status != common_pb.SUCCESS:
      return compile_result

    additional_trigger_properties = self.outbound_transfer(
        bot, update_step, build_config)

    self.trigger_child_builds(
        bot.builder_id,
        update_step,
        build_config,
        additional_properties=additional_trigger_properties)
    self.archive_build(bot.builder_id, update_step, build_config)

    self.inbound_transfer(bot, update_step, build_config)

    return self._run_tests(bot, build_config)

  def outbound_transfer(self, bot, bot_update_step, build_config):
    """Handles the builder half of the builder->tester transfer flow.

    We support two different transfer mechanisms:
     - Isolate transfer: builders upload tests + any required runtime
       dependencies to isolate, then pass the isolate hashes to testers via
       properties. Testers use those hashes to trigger swarming tasks but do
       not directly download the isolates.
     - Package transfer: builders package and upload some of the output
       directory (see package_build for details). Testers download the zip
       and proceed to run tests.

    These can be used concurrently -- e.g., a builder that triggers two
    different testers, one that supports isolate transfer and one that
    doesn't, would run both the isolate transfer flow *and* the package
    transfer flow.

    For isolate-based transfers, this function just sets a trigger property,
    as tests get isolated immediately after compilation (see
    compile_specific_targets).

    For package-based transfers, this uploads some of the output directory
    to GS. (See package_build for more details.)

    Args:
      bot: a BotMetadata object for the currently executing builder.
      bot_update_step: the result of a previously executed bot_update step.
      build_config: a BuildConfig object.
    Returns:
      A dict containing additional properties that should be added to any
      triggered child builds.
    """
    bot_type = bot.settings.get('bot_type')

    isolate_transfer = any(
        t.uses_isolate for t in build_config.tests_triggered_by(bot.builder_id))
    non_isolated_tests = [
        t for t in build_config.tests_triggered_by(bot.builder_id)
        if not t.uses_isolate
    ]
    package_transfer = (
        bool(non_isolated_tests) or bot.settings.get('enable_package_transfer'))

    additional_trigger_properties = {}
    if isolate_transfer:
      additional_trigger_properties['swarm_hashes'] = (
          self.m.isolate.isolated_tests)
    if package_transfer and bot_type in bot_spec.BUILDER_TYPES:
      self.package_build(
          bot.builder_id,
          bot_update_step,
          build_config,
          reasons=self._explain_package_transfer(bot, non_isolated_tests))
    return additional_trigger_properties

  def inbound_transfer(self, bot, bot_update_step, build_config):
    """Handles the tester half of the builder->tester transfer flow.

    See outbound_transfer for a discussion of transfer mechanisms.

    For isolate-based transfers, this merely clears out the output directory.
    For package-based transfer, this downloads the build from GS.

    Args:
      bot: a BotMetadata object for the currently executing tester.
      bot_update_step: the result of a previously executed bot_update step.
      build_config: a BuildConfig object.
    """
    bot_type = bot.settings.get('bot_type')

    if not bot_type == bot_spec.TESTER:
      return

    non_isolated_tests = [
        t for t in build_config.tests_on(bot.builder_id) if not t.uses_isolate
    ]
    isolate_transfer = not non_isolated_tests
    # The inbound portion of the isolate transfer is a strict subset of the
    # inbound portion of the package transfer. A builder that has to handle
    # the package transfer logic does not need to do the isolate logic under
    # any circumstance, as it'd just be deleting the output directory twice.
    package_transfer = not isolate_transfer

    if isolate_transfer:
      # This was lifted from download_and_unzip_build out of an abundance of
      # caution during the initial implementation of isolate transfer. It may
      # be possible to remove it, though there likely isn't a significant
      # benefit to doing so.
      self.m.file.rmtree(
          'build directory',
          self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))
    if package_transfer:
      # No need to read the GN args since we looked them up for testers already
      self.download_and_unzip_build(
          bot.builder_id, bot_update_step, build_config, read_gn_args=False)
      self.m.python.succeeding_step(
          'explain extract build',
          self._explain_package_transfer(bot, non_isolated_tests),
          as_log='why is this running?')

  def _explain_package_transfer(self, bot, non_isolated_tests):
    package_transfer_reasons = [
        'This builder is doing the full package transfer because:'
    ]
    for t in non_isolated_tests:
      package_transfer_reasons.append(" - %s doesn't use isolate" % t.name)
    if bot.settings.get('enable_package_transfer'):
      package_transfer_reasons.append(
          " - package transfer is explicitly enabled")
    return package_transfer_reasons

  def _contains_invalid_results(self, unrecoverable_test_suites):
    for test_suite in unrecoverable_test_suites:
      # Both 'with patch' and 'without patch' must have valid results to
      # skip CQ retries.
      valid_results, _ = (
          test_suite.with_patch_failures_including_retry())
      if not valid_results:
        return True

      if not test_suite.has_valid_results('without patch'):
        return True

    return False

  def deapply_deps(self, bot_update_step):
    with self.m.context(cwd=self.m.chromium_checkout.working_dir):
      # If tests fail, we want to fix Chromium revision only. Tests will use
      # the dependencies versioned in 'src' tree.
      self.m.bot_update.resolve_fixed_revision(
          bot_update_step.json.output, 'src')

      # NOTE: 'ignore_input_commit=True' gets a checkout using the commit
      # before the tested commit, effectively deapplying the gitiles commit
      # (latest commit currently being tested) and reverts back to DEPS
      # revisions.
      # Chromium has a lot of tags which slow us down, we don't need them to
      # deapply, so don't fetch them.
      self.m.bot_update.ensure_checkout(
          patch=False,
          no_fetch_tags=True,
          update_presentation=False,
          ignore_input_commit=True)

    with self.m.context(cwd=self.m.path['checkout']):
      # NOTE: "without patch" phrase is used to keep consistency with the API
      self.m.chromium.runhooks(name='runhooks (without patch)')

  def integration_steps(self, builders=None, bots=None):
    return self.run_tests_with_and_without_changes(
      builders=builders, mirrored_bots=bots,
      deapply_changes=self.deapply_deps)

  def trybot_steps(self, builders=None, trybots=None):
    return self.run_tests_with_and_without_changes(
        builders=builders,
        mirrored_bots=trybots,
        deapply_changes=self.deapply_patch)

  def trybot_steps_for_tests(self, builders=None, trybots=None, tests=None):
    """Similar to trybot_steps, but only runs certain tests.

    This is currently experimental code. Talk to martiniss@ if you want to
    use this."""
    return self.run_tests_with_and_without_changes(
        builders=builders,
        mirrored_bots=trybots,
        deapply_changes=self.deapply_patch,
        tests=tests)

  def run_tests_with_and_without_changes(self,
                                         builders,
                                         mirrored_bots,
                                         deapply_changes,
                                         tests=None):
    """Compile and run tests for chromium_trybot recipe.

    Args:
      builders: All the builders which exist.
      mirrored_bots: The set of mirrored bots.
      deapply_changes: A function which deapplies changes to the code being
        tested.
      tests: A list of tests to run on this bot. Before using this argument,
        please talk to martiniss@.

    Returns:
      - A RawResult object with the status of the build and
      failure message if an error occurred.
      - None if no failures
    """
    raw_result, task = self._calculate_tests_to_run(
        builders=builders, mirrored_bots=mirrored_bots, tests_to_run=tests)
    if raw_result and raw_result.status != common_pb.SUCCESS:
      return raw_result

    self.m.python.succeeding_step('mark: before_tests', '')
    if task.test_suites:
      compile_failure, unrecoverable_test_suites = self._run_tests_with_retries(
        task, deapply_changes)
      if compile_failure:
        return compile_failure

      self.m.chromium_swarming.report_stats()

      self.m.test_utils.summarize_findit_flakiness(self.m, task.test_suites)

      if not unrecoverable_test_suites:
        return None

      if (self.m.tryserver.is_tryserver and
          not self._contains_invalid_results(unrecoverable_test_suites)):
        self.m.cq.set_do_not_retry_build()

      return result_pb2.RawResult(
          summary_markdown=self._format_unrecoverable_failures(
              unrecoverable_test_suites, 'with patch'),
          status=common_pb.FAILURE)

  def _format_unrecoverable_failures(self, unrecoverable_test_suites,
                                     suffix, size_limit=700, failure_limit=4):
    """Creates list of failed tests formatted using markdown.

    Args:
      unrecoverable_test_suites: List of failed Test
          (definition can be found in steps.py)
      suffix: current Test suffix, which represents the phase
      size_limit: max size of the message in characters
      failure_limit: max number of deterministic failures listed per test suite

    Returns:
      String containing a markdown formatted list of test failures
    """
    test_size = len(unrecoverable_test_suites)
    header = '%d Test Suite(s) failed.' % test_size
    test_summary_lines = [header]
    if self._test_data.enabled:
      size_limit = self._test_data.get('change_size_limit', 200)
      failure_limit = size_limit / 100

    current_size = 0
    for index, suite in enumerate(unrecoverable_test_suites):
      test_suite_header = '**%s** failed.' % suite.name

      if suffix:
        is_valid, deterministic_failures = suite.failures_including_retry(
            suffix)
        if is_valid:
          is_valid, failures_to_ignore = suite.without_patch_failures_to_ignore(
          )
          if is_valid:
            deterministic_failures = deterministic_failures - failures_to_ignore
      else:
        # All the failures on CI builders are unrecoverable.
        deterministic_failures = suite.deterministic_failures(suffix)

      deterministic_failures = deterministic_failures or set()
      if deterministic_failures:
        test_suite_header = '**%s** failed because of:' % suite.name

      current_size += len(test_suite_header)
      if current_size >= size_limit:
        hint = '#### ...%d more test(s)...' % (test_size - index)
        test_summary_lines.append(hint)
        return '\n\n'.join(test_summary_lines)

      test_summary_lines.append(test_suite_header)

      for index, failure in enumerate(deterministic_failures):
        if index >= failure_limit or current_size >= size_limit:
          failure_size = len(deterministic_failures)
          hint = '- ...%d more failure(s) (%d total)...' % (
              failure_size - index, failure_size)
          test_summary_lines.append(hint)
          current_size += len(hint)
          break

        failure_line = '- %s' % failure
        test_summary_lines.append(failure_line)
        current_size += len(failure_line)

    return '\n\n'.join(test_summary_lines)

  def lookup_bot_metadata(self, builders, mirrored_bots=None):
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
    bots = mirrored_bots or self.trybots
    builder_id = self.m.chromium.get_builder_id()
    config = bots.get(builder_id.master, {}).get('builders',
                                                 {}).get(builder_id.builder)

    if not config:
      # Some trybots do not mirror a CI bot. In this case, return a
      # configuration that uses the same <mastername, buildername> of the
      # triggering trybot.
      config = {
          'bot_ids': [builder_id],
      }

    # contains build/test settings for the bot
    settings = self.create_bot_config_object(
        config['bot_ids'], builders=builders)

    self._report_builders(settings)

    return BotMetadata(builder_id, config, settings)

  def _determine_compilation_targets(self, bot, affected_files, build_config):
    compile_targets = self.get_compile_targets(bot.settings, build_config,
                                               build_config.all_tests())
    test_targets = sorted(
        set(self._all_compile_targets(build_config.all_tests())))

    # Use analyze to determine the compile targets that are affected by the CL.
    # Use this to prune the relevant compile targets and test targets.
    if self.m.tryserver.is_tryserver:
      additional_compile_targets = sorted(
          set(compile_targets) - set(test_targets))
      analyze_names = ['chromium'] + list(
          bot.config.get('analyze_names', []))
      mb_config_path = (
          self.m.chromium.c.project_generator.config_path
          or self.m.path['checkout'].join('tools', 'mb', 'mb_config.pyl'))
      test_targets, compile_targets = self.m.filter.analyze(
          affected_files,
          test_targets,
          additional_compile_targets,
          'trybot_analyze_config.json',
          builder_id=bot.builder_id,
          mb_config_path=mb_config_path,
          additional_names=analyze_names)

    return test_targets, compile_targets

  def _gather_tests_to_run(self, bot, build_config):
    if bot.is_compile_only():
      return [], []

    # Determine the tests that would be run if this were a CI tester.
    # Tests are instances of class(Test) from chromium_tests/steps.py. These
    # objects know how to dispatch isolate tasks, parse results, and keep
    # state on the results of previous test runs.
    return build_config.tests_in_scope(), build_config.all_tests()

  def _calculate_tests_to_run(self,
                              builders=None,
                              mirrored_bots=None,
                              tests_to_run=None):
    """Determines which tests need to be run.

    Args:
      builders: An optional mapping from <mastername, buildername> to
                build/test settings. For an example of defaults for chromium,
                see scripts/slave/recipe_modules/chromium_tests/chromium.py
      mirrored_bots: An optional mapping from <mastername, buildername> of the
                     trybot to configurations of the mirrored CI bot. Defaults
                     are in ChromiumTestsApi.
      tests_to_run: A list of test suites to run.

    Returns:
      A Tuple of
        RawResult object with the status of compile step
          and the failure message if it failed
        Configuration of the build/test.
    """
    bot = self.lookup_bot_metadata(builders, mirrored_bots=mirrored_bots)

    # Applies build/test configurations from bot.settings.
    self.configure_build(
        bot.settings, override_bot_type=bot_spec.BUILDER_TESTER)

    self.m.chromium.apply_config('trybot_flavor')

    # This rolls chromium checkout, applies the patch, runs gclient sync to
    # update all DEPS.
    # Chromium has a lot of tags which slow us down, we don't need them on
    # trybots, so don't fetch them.
    bot_update_step, build_config = self.prepare_checkout(
        bot.settings, timeout=3600, no_fetch_tags=True)

    self.m.chromium_swarming.configure_swarming(
      'chromium', precommit=self.m.tryserver.is_tryserver)

    affected_files = self.m.chromium_checkout.get_files_affected_by_patch()

    # Must happen before without patch steps.
    if self.m.code_coverage.using_coverage:
      self.m.code_coverage.instrument(affected_files)

    tests, tests_including_triggered = self._gather_tests_to_run(
        bot, build_config)

    test_targets, compile_targets = self._determine_compilation_targets(
        bot, affected_files, build_config)

    if tests_to_run:
      compile_targets = [t for t in compile_targets if t in tests_to_run]
      test_targets = [t for t in test_targets if t in tests_to_run]
      # TODO(crbug.com/840252): Using startswith for now to allow layout tests
      # to work, since the # ninja target which gets computed has exparchive as
      # the suffix. Can switch to plain comparison after the bug is fixed.
      tests = [
          t for t in tests if any(
              t.target_name.startswith(target_name)
              for target_name in tests_to_run)
      ]
      tests_including_triggered = [
          t for t in tests_including_triggered if any(
              t.target_name.startswith(target_name)
              for target_name in tests_to_run)
      ]

    # Compiles and isolates test suites.
    raw_result = result_pb2.RawResult(status=common_pb.SUCCESS)
    if compile_targets:
      tests = self._tests_in_compile_targets(test_targets, tests)
      tests_including_triggered = self._tests_in_compile_targets(
          test_targets, tests_including_triggered)

      compile_targets = sorted(set(compile_targets))
      raw_result = self.compile_specific_targets(
          bot.settings,
          bot_update_step,
          build_config,
          compile_targets,
          tests_including_triggered,
          override_bot_type=bot_spec.BUILDER_TESTER)
    else:
      # Even though the patch doesn't require a compile on this platform,
      # we'd still like to run tests not depending on
      # compiled targets (that's obviously not covered by the
      # 'analyze' step) if any source files change.
      if any(self._is_source_file(f) for f in affected_files):
        tests = [t for t in tests if not t.compile_targets()]
      else:
        tests = []

    return raw_result, Task(bot, tests, bot_update_step, affected_files)

  def _report_builders(self, bot_config):
    """Reports the builders being executed by the bot."""

    def present_bot(bot_mirror):
      if bot_mirror.tester_id:
        return ('running tester %r on master %r against builder %r on master %r'
                % (bot_mirror.tester_id.builder, bot_mirror.tester_id.master,
                   bot_mirror.builder_id.builder, bot_mirror.builder_id.master))
      bot_type = bot_config.get_bot_type(bot_mirror.builder_id)
      if bot_type == bot_spec.BUILDER_TESTER:
        bot_type = 'builder/tester'
      return ('running %s \'%s\' on master %r' %
              (bot_type, bot_mirror.builder_id.builder,
               bot_mirror.builder_id.master))

    lines = [''] + [present_bot(m) for m in bot_config.bot_mirrors]
    result = self.m.python.succeeding_step(
        'report builders', '<br/>'.join(lines))

    def as_dict(bot_mirror):
      if bot_mirror.tester_id:
        return {
            'mastername': bot_mirror.builder_id.master,
            'buildername': bot_mirror.builder_id.builder,
            'tester_buildername': bot_mirror.tester_id.builder,
            'tester_mastername': bot_mirror.tester_id.master,
            'bot_type': bot_spec.TESTER,
        }
      bot_type = bot_config.get_bot_type(bot_mirror.builder_id)
      if bot_type == bot_spec.BUILDER_TESTER:
        bot_type = 'builder/tester'
      return {
          'mastername': bot_mirror.builder_id.master,
          'buildername': bot_mirror.builder_id.builder,
          'bot_type': bot_type,
      }

    bots_json = [as_dict(b) for b in bot_config.bot_mirrors]
    result.presentation.logs['bots.json'] = self.m.json.dumps(
        bots_json, indent=2).split('/n')

    # Links to upstreams help people figure out if upstreams are broken too
    # TODO(gbeaty): When we switch to using buckets to identify builders instead
    # of master name, we can have an authoritative value for the bucket to use
    # in these links, for now rely on convention:
    # try -> ci
    # try-beta -> ci-beta
    # try-stable -> ci-stable
    for bot_mirror in bot_config.bot_mirrors:
      if bot_mirror.tester_id:
        result.presentation.links[bot_mirror.tester_id.builder] = (
            'https://ci.chromium.org/p/%s/builders/%s/%s' % (
                self.m.buildbucket.build.builder.project,
                self.m.buildbucket.build.builder.bucket.replace('try', 'ci'),
                bot_mirror.tester_id.builder,
            ))

      result.presentation.links[bot_mirror.builder_id.builder] = (
          'https://ci.chromium.org/p/%s/builders/%s/%s' % (
              self.m.buildbucket.build.builder.project,
              self.m.buildbucket.build.builder.bucket.replace('try', 'ci'),
              bot_mirror.builder_id.builder,
          ))


  def _all_compile_targets(self, tests):
    """Returns the compile_targets for all the Tests in |tests|."""
    return sorted(set(x
                      for test in tests
                      for x in test.compile_targets()))

  def _is_source_file(self, filepath):
    """Returns true iff the file is a source file."""
    _, ext = self.m.path.splitext(filepath)
    return ext in ['.c', '.cc', '.cpp', '.h', '.java', '.mm']

  def _tests_in_compile_targets(self, compile_targets, tests):
    """Returns the tests in |tests| that have at least one of their compile
    targets in |compile_targets|."""
    result = []
    for test in tests:
      test_compile_targets = test.compile_targets()
      # Always return tests that don't require compile. Otherwise we'd never
      # run them.
      if ((set(compile_targets) & set(test_compile_targets)) or
          not test_compile_targets):
        result.append(test)
    return result


  def _lookup_builder_gn_args(self,
                              bot_meta_data,
                              mb_config_path=None,
                              builders=None):
    # Lookup GN args for the associated builder
    parent_builder_id = chromium.BuilderId.create_for_master(
        bot_meta_data.settings.get('parent_mastername',
                                   bot_meta_data.builder_id.master),
        bot_meta_data.settings.get('parent_buildername'))
    parent_bot_config = self.create_bot_config_object([parent_builder_id],
                                                      builders=builders)
    parent_chromium_config = self._chromium_config(parent_bot_config)
    android_version_name, android_version_code = (
        self.get_android_version_details(parent_bot_config))
    self.m.chromium.mb_lookup(
        parent_builder_id,
        mb_config_path=mb_config_path,
        chromium_config=parent_chromium_config,
        use_goma=self._use_goma(parent_chromium_config),
        android_version_name=android_version_name,
        android_version_code=android_version_code,
        name='lookup builder GN args')

  def _run_tests(self, bot_meta_data, build_config):
    tests = build_config.tests_on(bot_meta_data.builder_id)
    if not tests:
      return

    self.m.chromium_swarming.configure_swarming(
        'chromium',
        precommit=False,
        mastername=bot_meta_data.builder_id.master,
        default_priority=bot_meta_data.settings.get(
            'swarming_default_priority'))
    test_runner = self.create_test_runner(
        tests,
        serialize_tests=bot_meta_data.settings.get('serialize_tests'),
        # If any tests export coverage data we want to retry invalid shards due
        # to an existing issue with occasional corruption of collected coverage
        # data.
        retry_invalid_shards=any(
            t.runs_on_swarming and t.isolate_coverage_data for t in tests),
    )
    with self.wrap_chromium_tests(bot_meta_data.settings, tests):
      test_failure_summary = test_runner()

      if self.m.code_coverage.using_coverage:
        self.m.code_coverage.process_coverage_data(tests)

      if test_failure_summary:
        return test_failure_summary
