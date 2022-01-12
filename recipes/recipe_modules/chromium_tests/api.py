# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import contextlib
import itertools
import re
import six

from six.moves.urllib.parse import urlencode

from recipe_engine import recipe_api

from PB.recipe_engine import result as result_pb2
from PB.recipe_modules.build.archive import properties as arch_prop
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec

from . import generators
from .steps import ExperimentalTest
from .targets_config import TargetsConfig

# These account ids are obtained by looking at gerrit API responses.
# Specifically, just find a build from a desired CL author, look at the
# json output of the "gerrit fetch current CL info" recipe step, and find the
# values of owner._account_id.
# chromium and v8-ci-autorollers
AUTOROLLER_ACCOUNT_IDS = (1302611, 1274527)

ALL_TEST_BINARIES_ISOLATE_NAME = 'all_test_binaries'


class Task(object):
  """Represents the configuration for build/test tasks.

  The fields in the task are immutable.

  Attributes:
    builder_config: BuilderConfig of the task runner bot.
    bot_update_step: Holds state on build properties. Used to pass state
                     between methods.
    tests: A list of Test objects [see chromium_tests/steps.py]. Stateful
           objects that can run tests [possibly remotely via swarming] and
           parse the results. Running tests multiple times is not idempotent
           -- the results of previous runs affect future runs.
      affected_files: A list of paths affected by the CL.
  """

  def __init__(self, builder_config, test_suites, bot_update_step,
               affected_files):
    self._builder_config = builder_config
    self._test_suites = test_suites
    self._bot_update_step = bot_update_step
    self._affected_files = affected_files

  @property
  def builder_config(self):
    return self._builder_config

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
    return self.builder_config.retry_failed_shards


class ChromiumTestsApi(recipe_api.RecipeApi):
  Task = Task

  def __init__(self, input_properties, **kwargs):
    super(ChromiumTestsApi, self).__init__(**kwargs)
    self._project_trigger_overrides = input_properties.project_trigger_overrides
    self._fixed_revisions = input_properties.fixed_revisions

    self._swarming_command_lines = {}
    self.filter_files_dir = None

  @property
  def swarming_command_lines(self):
    return self._swarming_command_lines

  def log(self, message):
    presentation = self.m.step.active_result.presentation
    presentation.logs.setdefault('stdout', []).append(message)

  def require_gerrit_cl(self):
    if self.m.tryserver.is_tryserver:
      return

    status = self.m.step.EXCEPTION
    step_text = 'This recipe requires a gerrit CL for the source under test'
    if self.m.led.launched_by_led:
      status = self.m.step.FAILURE
      step_text += (
          "\n run 'led edit-cr-cl <chromium/src CL URL>' to attach a CL to test"
      )
    self.m.step.empty('not a tryjob', status=status, step_text=step_text)

  def fix_cros_boards_gclient_arg(self, cros_boards_with_qemu_images):
    """Returns a new value for cros_boards if VM-optimizations aren't ready yet.

    Support for 'amd64-generic-vm' was added in crrev.com/c/314085 and rolled
    into chromium in crrev.com/c/3194491. So to safely swap builders to the new
    board and avoid breaking older bots on branches, we replace that new board
    with the old one for m95 and older.
    FIXME: Remove this when m95 and anything older is no longer tested.
    """
    if 'amd64-generic-vm' not in cros_boards_with_qemu_images:
      return cros_boards_with_qemu_images

    milestone_re = re.match(r'.*-m(\d+)$',
                            self.m.buildbucket.build.builder.project)
    if not milestone_re or int(milestone_re.group(1)) > 95:
      return cros_boards_with_qemu_images

    # cros_boards_with_qemu_images is a colon-joined list of boards, so split,
    # filter, then re-join.
    new_boards = cros_boards_with_qemu_images.split(':')
    new_boards = [
        'amd64-generic' if b == 'amd64-generic-vm' else b for b in new_boards
    ]
    return ':'.join(set(new_boards))

  def configure_build(self, builder_config, use_rts=False):
    self.m.chromium.set_config(builder_config.chromium_config,
                               **builder_config.chromium_config_kwargs)

    self.m.gclient.set_config(builder_config.gclient_config)

    default_test_results_config = (
        'staging_server' if self.m.runtime.is_experimental else 'public_server')
    self.m.test_results.set_config(builder_config.test_results_config or
                                   default_test_results_config)

    if builder_config.android_config:
      self.m.chromium_android.configure_from_properties(
          builder_config.android_config,
          **builder_config.chromium_config_kwargs)

    for c in builder_config.chromium_apply_config:
      self.m.chromium.apply_config(c)

    for c in builder_config.gclient_apply_config:
      self.m.gclient.apply_config(c)

    if use_rts:
      self.m.gclient.c.solutions[0].custom_vars['checkout_rts_model'] = 'True'

    if (self.m.chromium.c.TARGET_CROS_BOARDS or
        self.m.chromium.c.CROS_BOARDS_WITH_QEMU_IMAGES):
      gclient_solution = self.m.gclient.c.solutions[0]
      if self.m.chromium.c.CROS_BOARDS_WITH_QEMU_IMAGES:
        gclient_solution.custom_vars['cros_boards_with_qemu_images'] = (
            self.fix_cros_boards_gclient_arg(
                self.m.chromium.c.CROS_BOARDS_WITH_QEMU_IMAGES))
      if self.m.chromium.c.TARGET_CROS_BOARDS:
        gclient_solution.custom_vars['cros_boards'] = (
            self.m.chromium.c.TARGET_CROS_BOARDS)

    self.m.gclient.c.revisions.update(self._fixed_revisions)

    for c in builder_config.android_apply_config:
      self.m.chromium_android.apply_config(c)

  def runhooks(self, update_step, suffix=None):
    if suffix:
      self.m.chromium.runhooks(name='runhooks ({})'.format(suffix))
    elif self.m.tryserver.is_tryserver:
      try:
        self.m.chromium.runhooks(name='runhooks (with patch)')
      except self.m.step.StepFailure:
        # As part of deapplying patch we call runhooks without the patch.
        self.deapply_patch(update_step)
        raise
    else:
      self.m.chromium.runhooks()

  def create_targets_config(self, builder_config, update_step):
    # The scripts_compile_targets is indirected through a function so that we
    # don't execute unnecessary steps if there are no scripts that need to be
    # run
    # Memoize the call to get_compile_targets_for_scripts so that we only
    # execute the step once
    memo = []

    def scripts_compile_targets_fn():
      if not memo:
        memo.append(self.get_compile_targets_for_scripts())
      return memo[0]

    source_side_specs = {
        group: self.read_source_side_spec(spec_file)
        for group, spec_file in sorted(
            six.iteritems(builder_config.source_side_spec_files))
    }
    tests = {}

    for builder_id in builder_config.builder_ids_in_scope_for_testing:
      builder_tests = self.generate_tests_from_source_side_spec(
          source_side_specs[builder_id.group],
          builder_id.builder,
          builder_id.group,
          scripts_compile_targets_fn,
          update_step,
      )
      tests[builder_id] = builder_tests

    return TargetsConfig.create(
        builder_config=builder_config,
        source_side_specs=source_side_specs,
        tests=tests)

  def prepare_checkout(self,
                       builder_config,
                       report_cache_state=True,
                       set_output_commit=None,
                       root_solution_revision=None,
                       runhooks_suffix=None,
                       **kwargs):
    """
    Args:
      runhooks_suffix: Suffix for gclient runhooks step name
    """
    if set_output_commit is None:
      set_output_commit = builder_config.set_output_commit
    if report_cache_state:
      with self.m.step.nest('builder cache') as presentation:
        contents = self.m.file.listdir('check if empty',
                                       self.m.chromium_checkout.checkout_dir)
        is_cached = bool(contents)
        presentation.properties['is_cached'] = is_cached
        if is_cached:
          presentation.step_text = (
              '\nbuilder cache is present, '
              'build may or may not be fast depending on state of cache')
        else:
          presentation.step_text = (
              '\nbuilder cache is absent, expect a slow build')

    # The root_solution_revision input property can be used to checkout
    # the root solution at a certain branch. This can be used when attempting
    # to run a builder for a child repository on a certain branch,
    # and the same branch needs to be checked out for the root solution
    root_solution_revision = (root_solution_revision or
                              self.m.properties.get('root_solution_revision'))
    update_step = self.m.chromium_checkout.ensure_checkout(
        builder_config,
        set_output_commit=set_output_commit,
        root_solution_revision=root_solution_revision,
        **kwargs)

    if (self.m.chromium.c.compile_py.compiler and
        'goma' in self.m.chromium.c.compile_py.compiler):
      self.m.chromium.ensure_goma(
          client_type=self.m.chromium.c.compile_py.goma_client_type)

    # Installs toolchains configured in the current bot, if any.
    self.m.chromium.ensure_toolchains()

    self.runhooks(update_step, suffix=runhooks_suffix)

    targets_config = self.create_targets_config(builder_config, update_step)

    return update_step, targets_config

  def generate_tests_from_source_side_spec(self, source_side_spec, buildername,
                                           builder_group,
                                           scripts_compile_targets_fn,
                                           bot_update_step):
    test_specs = []

    # TODO(phajdan.jr): Switch everything to scripts generators and simplify.
    for generator in generators.ALL_GENERATORS:
      test_specs.extend(
          generator(
              self,
              builder_group,
              buildername,
              source_side_spec,
              bot_update_step,
              scripts_compile_targets_fn=scripts_compile_targets_fn))

    tests = []
    test_specs_by_disabled_reason = collections.defaultdict(list)
    for test_spec in test_specs:
      reason = test_spec.disabled_reason
      if reason:
        test_specs_by_disabled_reason[reason].append(test_spec)
      else:
        tests.append(test_spec.get_test())

    for reason, test_specs in sorted(test_specs_by_disabled_reason.items()):
      reason.report_tests(self, [t.name for t in test_specs])

    return tuple(tests)

  def read_source_side_spec(self, source_side_spec_file):
    source_side_spec_path = self.m.chromium.c.source_side_spec_dir.join(
        source_side_spec_file)
    spec_result = self.m.json.read(
        'read test spec (%s)' % self.m.path.basename(source_side_spec_path),
        source_side_spec_path,
        infra_step=True,
        step_test_data=lambda: self.m.json.test_api.output({}))
    spec_result.presentation.step_text = 'path: %s' % source_side_spec_path
    source_side_spec = spec_result.json.output

    return source_side_spec

  def create_test_runner(self,
                         tests,
                         suffix='',
                         serialize_tests=False,
                         retry_failed_shards=False,
                         retry_invalid_shards=False):
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
            self.m,
            tl,
            suffix,
            retry_failed_shards=retry_failed_shards,
            retry_invalid_shards=retry_invalid_shards)
        failed_tests = failed_tests.union(failed_ts, invalid_ts)

      self.m.chromium_swarming.report_stats()

      if failed_tests:
        return result_pb2.RawResult(
            status=common_pb.FAILURE,
            summary_markdown=self._format_unrecoverable_failures(
                failed_tests, suffix))

    return test_runner

  _ARCHITECTURE_DIGIT_MAP = {
      ('arm', 32): 0,
      ('arm', 64): 5,
      ('intel', 32): 1,
      ('intel', 64): 6,
      ('mips', 32): 2,
  }

  def get_android_version_details(self, version_file, log_details=False):
    if not version_file:
      return None, None

    version = self.m.chromium.get_version_from_file(
        self.m.path['checkout'].join(version_file))

    chromium_config = self.m.chromium.c
    arch_id = chromium_config.TARGET_ARCH, chromium_config.TARGET_BITS
    arch_digit = self._ARCHITECTURE_DIGIT_MAP.get(arch_id, None)
    assert arch_digit is not None, (
        'Architecture and bits (%r) does not have a version digit assigned' %
        arch_id)

    android_version_name = '%(MAJOR)s.%(MINOR)s.%(BUILD)s.%(PATCH)s' % version
    android_version_code = '%d%03d%d0' % (int(
        version['BUILD']), int(version['PATCH']), arch_digit)
    if log_details:
      self.log('version:%s' % self.m.py3_migration.consistent_dict_str(version))
      self.log('android_version_name:%s' % android_version_name)
      self.log('android_version_code:%s' % android_version_code)
    return android_version_name, android_version_code

  def _use_goma_set_in_recipe(self, chromium_config=None):
    chromium_config = chromium_config or self.m.chromium.c
    return (chromium_config.compile_py.compiler and
            'goma' in chromium_config.compile_py.compiler)

  def _use_goma_set_in_gn_args(self, gn_args):
    args = self.m.gn.parse_gn_args(gn_args)
    return args.get('use_goma') == 'true'

  def _use_reclient(self, gn_args):
    args = self.m.gn.parse_gn_args(gn_args)
    return args.get('use_remoteexec') == 'true' or args.get('use_rbe') == 'true'

  def compile_specific_targets(self,
                               builder_id,
                               builder_config,
                               update_step,
                               targets_config,
                               compile_targets,
                               tests,
                               mb_phase=None,
                               mb_config_path=None,
                               mb_recursive_lookup=True,
                               override_execution_mode=None,
                               use_rts=False,
                               rts_recall=None,
                               use_st=False,
                               isolate_output_files_for_coverage=False):
    """Runs compile and related steps for given builder.

    Allows finer-grained control about exact compile targets used.

    Args:
      builder_id - A BuilderId identifying the configuration to use when running
        mb.
      builder_config - The configuration for the builder being executed.
      update_step - The StepResult from the bot_update step.
      targets_config - The configuration of the current build.
      compile_targets - The list of targets to compile.
      tests - The list of tests to be built for this builder. The tests may or
        may not be executed by the builder and may be executed by another
        builder that is triggered. The compile operation will prepare and upload
        the isolates for the tests that use isolate.
      mb_phase - A phase argument to be passed to mb. Must be provided if the
        configuration identified by `builder_id` uses phases and must not be
        provided if the configuration identified by `builder_id` does not use
        phases.
      mb_config_path - An optional override specifying the file where mb will
        read configurations from.
      mb_recursive_lookup - A boolean indicating whether the lookup operation
        should recursively expand any included files. If False, then the lookup
        output will contain the include statement.
      override_execution_mode - An optional override to change the execution
        mode.
      use_rts - A boolean indicating whether to use regression test selection
        (bit.ly/chromium-rts)
      rts_recall - A float from (0 to 1] indicating what change recall rts
        should aim for, 0 being the fastest and 1 being the safest, and
        typically between .9 and 1
      isolate_output_files_for_coverage: Whether to also upload all test
        binaries and other required code coverage output files to one hash.
      use_st - A boolean indicating whether to filter out stable tests

    Returns:
      RawResult object with compile step status and failure message
    """

    assert isinstance(targets_config, TargetsConfig), \
        "targets_config argument %r was not a TargetsConfig" % targets_config
    execution_mode = override_execution_mode or builder_config.execution_mode

    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.clean_local_files()
      self.m.chromium_android.run_tree_truth()

    if execution_mode == ctbc.COMPILE_AND_TEST:
      isolated_targets = [t.isolate_target for t in tests if t.uses_isolate]
      # Skylab tests pretend to be isolated_targets at run_mb_and_compile step,
      # for generating the runtime deps. We upload the deps to GCS instead of
      # isolate server, because skylab DUT does not support isolate.
      skylab_isolates = [
          t.target_name
          for t in tests
          # Skylab test has different runner script and dependencies. A skylab
          # test target should not appear in isolated_targets.
          if t.is_skylabtest and not t.target_name in isolated_targets
      ]

      name_suffix = ''
      if self.m.tryserver.is_tryserver:
        name_suffix = ' (with patch)'

      android_version_name, android_version_code = (
          self.get_android_version_details(
              builder_config.android_version, log_details=True))

      raw_result = self.run_mb_and_compile(
          builder_id,
          compile_targets,
          isolated_targets + skylab_isolates,
          name_suffix=name_suffix,
          mb_phase=mb_phase,
          mb_config_path=mb_config_path,
          mb_recursive_lookup=mb_recursive_lookup,
          android_version_code=android_version_code,
          android_version_name=android_version_name,
          use_rts=use_rts,
          rts_recall=rts_recall,
          use_st=use_st)

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
                  '@',
                  '(at)'),
              'with' if has_patch else 'without')

        if isolate_output_files_for_coverage:
          file_paths = self.m.code_coverage.get_required_build_output_files(
              [t for t in tests if t.uses_isolate])

          self.m.isolate.write_isolate_files_for_binary_file_paths(
              file_paths, ALL_TEST_BINARIES_ISOLATE_NAME,
              self.m.chromium.output_dir)

          isolated_targets.append(ALL_TEST_BINARIES_ISOLATE_NAME)

        # 'compile' just prepares all information needed for the isolation,
        # and the isolation is a separate step.
        self.m.isolate.isolate_tests(
            self.m.chromium.output_dir,
            suffix=name_suffix,
            targets=list(set(isolated_targets)),
            verbose=True,
            swarm_hashes_property_name=swarm_hashes_property_name)

        self.set_test_command_lines(tests, name_suffix)

        if builder_config.perf_isolate_upload:
          instance = self.m.cas.instance
          self.m.perf_dashboard.upload_isolate(
              self.m.buildbucket.builder_name,
              self.m.perf_dashboard.get_change_info([{
                  'repository':
                      'chromium',
                  'git_hash':
                      update_step.presentation.properties['got_revision'],
              }]), instance, self.m.isolate.isolated_tests)

      if skylab_isolates:
        self._prepare_artifact_for_skylab(
            builder_config,
            [t for t in tests if t.target_name in skylab_isolates])
      return raw_result

  def set_test_command_lines(self, tests, suffix):
    step_result = self.m.python(
        'find command lines%s' % suffix,
        self.resource('find_command_lines.py'), [
            '--build-dir', self.m.chromium.output_dir, '--output-json',
            self.m.json.output()
        ],
        step_test_data=lambda: self.m.json.test_api.output({}))
    assert isinstance(step_result.json.output, dict)
    self._swarming_command_lines = step_result.json.output
    for test in tests:
      if test.runs_on_swarming or test.uses_isolate:
        command_line = self.swarming_command_lines.get(test.target_name, [])

        if command_line:
          test.raw_cmd = command_line
          test.relative_cwd = self.m.path.relpath(self.m.chromium.output_dir,
                                                  self.m.path['checkout'])

  def package_build(self, builder_id, update_step, builder_config,
                    reasons=None):
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
    builder_spec = builder_config.builder_db[builder_id]

    assert builder_spec.execution_mode == ctbc.COMPILE_AND_TEST, (
        'Called package_build for %s:%s, which is has execution mode %r. '
        'Only %r is supported by package_build. '
        'This is a bug in your recipe.' %
        (builder_id.group, builder_id.builder, builder_spec.execution_mode,
         ctbc.COMPILE_AND_TEST))

    if not builder_spec.cf_archive_build:
      build_revision = update_step.presentation.properties.get(
          'got_revision',
          update_step.presentation.properties.get('got_src_revision'))

      # For archiving 'chromium.perf', the builder also archives a version
      # without perf test files for manual bisect.
      # (https://bugs.chromium.org/p/chromium/issues/detail?id=604452)
      if builder_spec.bisect_archive_build:
        bisect_package_step = self.m.archive.zip_and_upload_build(
            'package build for bisect',
            self.m.chromium.c.build_config_fs,
            build_url=self._build_bisect_gs_archive_url(builder_spec),
            build_revision=build_revision,
            update_properties=update_step.presentation.properties,
            exclude_perf_test_files=True,
            store_by_hash=False,
            platform=self.m.chromium.c.TARGET_PLATFORM)
        bisect_reasons = list(reasons or [])
        bisect_reasons.extend([
            ' - %s is a bisect builder' % builder_id.builder,
            ' - bisect_gs_bucket is configured to %s' %
            builder_spec.bisect_gs_bucket,
        ])
        bisect_package_step.presentation.logs['why is this running?'] = (
            bisect_reasons)

      if builder_spec.build_gs_bucket:
        package_step = self.m.archive.zip_and_upload_build(
            'package build',
            self.m.chromium.c.build_config_fs,
            build_url=self._build_gs_archive_url(builder_spec, builder_id.group,
                                                 builder_id.builder),
            build_revision=build_revision,
            # TODO(machenbach): Make asan a configuration switch.
            package_dsym_files=(self.m.chromium.c.runtests.enable_asan and
                                self.m.chromium.c.HOST_PLATFORM == 'mac'),
        )
        standard_reasons = list(reasons or [])
        standard_reasons.extend([
            ' - build_gs_bucket is configured to %s' %
            builder_spec.build_gs_bucket,
        ])
        package_step.presentation.logs['why is this running?'] = (
            standard_reasons)

  def archive_build(self, builder_id, update_step, builder_config):
    """Archive the build if the bot is configured to do so.

    There are three types of builds that get archived: regular builds,
    clustefuzz builds, and generic archives.

    See api.archive.clusterfuzz_archive and archive_build.py for more
    information.

    This is currently used to store builds long-term and to transfer them
    to clusterfuzz.
    """
    builder_spec = builder_config.builder_db[builder_id]

    if builder_spec.cf_archive_build and not self.m.tryserver.is_tryserver:
      self.m.archive.clusterfuzz_archive(
          build_dir=self.m.chromium.c.build_dir.join(
              self.m.chromium.c.build_config_fs),
          update_properties=update_step.presentation.properties,
          gs_bucket=builder_spec.cf_gs_bucket,
          gs_acl=builder_spec.cf_gs_acl,
          archive_prefix=builder_spec.cf_archive_name,
          archive_subdir_suffix=builder_spec.cf_archive_subdir_suffix,
      )

    # TODO(crbug.com/1138672) Move custom_vars to higher level of recipes.
    custom_vars = {}
    custom_vars['chrome_version'] = self._get_chrome_version()

    # The goal of generic archive is to eventually replace most of the custom
    # archive logic with InputProperties driven archiving.
    # https://crbug.com/1076679.
    upload_results = self.m.archive.generic_archive(
        build_dir=self.m.chromium.output_dir,
        update_properties=update_step.presentation.properties,
        custom_vars=custom_vars)

    self.m.symupload(self.m.chromium.output_dir)
    return upload_results

  def _get_chrome_version(self):
    chrome_version = self.m.properties.get('chrome_version')
    if not chrome_version:
      ref = self.m.buildbucket.gitiles_commit.ref
      if ref.startswith('refs/tags/'):
        chrome_version = str(ref[len('refs/tags/'):])
    return chrome_version

  def _get_builders_to_trigger(self, builder_id, builder_config):
    """Get the builders to trigger.

    Args:
      * builder_id - The `BuilderId` identifying the builder to find the
        child builders for.
      * builder_config - The `BuilderConfig` associated with `builder_id`.

    Returns:
      A dict where the keys are the project name and the values are a
      list of names of the builders within the project to trigger.
    """
    to_trigger = collections.defaultdict(set)
    for child_id in sorted(builder_config.builder_db.builder_graph[builder_id]):
      child_spec = builder_config.builder_db[child_id]
      luci_project = self._project_trigger_overrides.get(
          child_spec.luci_project, child_spec.luci_project)
      to_trigger[luci_project].add(child_id.builder)
    return {
        luci_project: sorted(builders)
        for luci_project, builders in six.iteritems(to_trigger)
    }

  def _trigger_led_builds(self, to_trigger, properties):
    """Trigger builders using led.

    Args:
      * to_trigger - A dict where the keys are the project name and the
        values are a list of names of the builders within the project to
        trigger.
    """
    property_args = []
    for k, v in self.m.py3_migration.consistent_ordering(
        six.iteritems(properties)):
      property_args.append('-p')
      property_args.append('{}={}'.format(k, self.m.json.dumps(v)))

    with self.m.step.nest('trigger') as trigger_presentation:
      # Clear out SWARMING_TASK_ID in the environment so that the created tasks
      # do not have a parent task ID. This allows the triggered tasks to outlive
      # the current task instead of being cancelled when the current task
      # completes.
      # TODO(https://crbug.com/1140621) Use command-line option instead of
      # changing environment.
      with self.m.context(env={'SWARMING_TASK_ID': None}):
        for child_project, builders in six.iteritems(to_trigger):
          for child_builder in builders:
            # We don't actually know the bucket for child builders because our
            # config objects don't store anything about the bucket, but we
            # haven't had a reason to trigger builders in other buckets yet and
            # this is just for manual testing with led, so not important to
            # worry about at this time. This can be addressed in the future when
            # configuration is src-side and the bucket information can be
            # supplied by the starlark generation.
            child_bucket = self.m.buildbucket.build.builder.bucket

            child_builder_name = '{}/{}/{}'.format(child_project, child_bucket,
                                                   child_builder)
            with self.m.step.nest(child_builder_name) as builder_presentation:
              led_builder_id = 'luci.{}.{}:{}'.format(child_project,
                                                      child_bucket,
                                                      child_builder)
              led_job = self.m.led('get-builder', led_builder_id)

              led_job = self.m.led.inject_input_recipes(led_job)
              led_job = led_job.then('edit', *property_args)
              result = led_job.then('launch').launch_result

              swarming_task_url = result.swarming_task_url
              builder_presentation.links['swarming task'] = swarming_task_url
              trigger_presentation.links[child_builder_name] = swarming_task_url

  def trigger_child_builds(self,
                           builder_id,
                           update_step,
                           builder_config,
                           additional_properties=None,
                           commit=None):
    """Trigger builders that configure the current builder as parent.

    Args:
      * builder_id - The ID of the running builder. The
        `parent_builder_group` and `parent_buildername` properties will
        be set to refer to this builder.
      * update_step - The step result of the bot_update step. For each
        property in `update_step.presentation.properties` that starts
        with `got_`, the returned properties will contain a property
        with `parent_` prepended to the property and the same value. If
        `update_step.presentation.properties` contains a `got_revision`
        property, then the returned properties will have the `revision`
        property set to the same value. The `fixed_revisions` field of
        the `$build/chromium_tests` property will be set with a mapping
        to ensure that the triggered build checks out the same versions
        for the paths in `update_step.json.output['manifest']`.
      * builder_config - The configuration of the running builder.
      * additional_properties - Additional properties to set for the
        triggered builds. These properties will take precedence over
        properties computed from `builder_id` and `update_step`.
      * commit - The GitilesCommit message to set on the input of the
        triggered builds. If not provided,
        buildbucket.build.output.gitiles_commit will be used.
    """
    with self.m.context(infra_steps=True):
      to_trigger = self._get_builders_to_trigger(builder_id, builder_config)
      if not to_trigger:
        return

      properties = self._get_trigger_properties(builder_id, update_step,
                                                additional_properties)

      if self.m.led.launched_by_led:
        self._trigger_led_builds(to_trigger, properties)
        return

      if (commit is None and
          self.m.buildbucket.build.output.HasField('gitiles_commit')):
        commit = self.m.buildbucket.build.output.gitiles_commit

      if commit is None:
        step_result = self.m.step('no commit for trigger', [])
        step_result.presentation.status = self.m.step.EXCEPTION
        step_result.presentation.step_text = '\n'.join([
            'no commit was provided for trigger',
            'one of the following fixes should be made to the recipe:',
            '* pass `set_output_commit=True` to bot_update',
            "* pass `commit` to trigger_child_builds",
        ])
        self.m.step.raise_on_failure(step_result)

      repo = 'https://{}/{}'.format(commit.host, commit.project)
      trigger = self.m.scheduler.GitilesTrigger(
          repo=repo,
          ref=commit.ref,
          revision=commit.id,
          properties=properties,
      )

      scheduler_triggers = []
      for project, builders in six.iteritems(to_trigger):
        scheduler_triggers.append((trigger, project, builders))
      self.m.scheduler.emit_triggers(scheduler_triggers, step_name='trigger')

  def _get_trigger_properties(self,
                              builder_id,
                              update_step,
                              additional_properties=None):
    """Get the properties used for triggering child builds.

    Arguments:
      * builder_id - The ID of the running builder. The
        `parent_builder_group` and `parent_buildername` properties will
        be set to refer to this builder.
      * update_step - The step result of the bot_update step. For each
        property in `update_step.presentation.properties` that starts
        with `got_`, the returned properties will contain a property
        with `parent_` prepended to the property and the same value. If
        `update_step.presentation.properties` contains a `got_revision`
        property, then the returned properties will have the `revision`
        property set to the same value. The `fixed_revisions` field of
        the `$build/chromium_tests` property will be set with a mapping
        to ensure that the triggered build checks out the same versions
        for the paths in `update_step.json.output['manifest']`.
      * additional_properties - Additional properties to set for the
        triggered builds. These properties will take precedence over
        properties computed from `builder_id` and `update_step`.

    Returns:
      A dict containing the properties to be set when triggering another
      builder.
    """
    # LUCI-Scheduler-based triggering (required on luci stack).
    properties = {
        'parent_builder_group': builder_id.group,
        'parent_buildername': builder_id.builder,
    }
    for name, value in six.iteritems(update_step.presentation.properties):
      if name.startswith('got_'):
        properties['parent_' + name] = value
    # Work around https://crbug.com/785462 in LUCI UI that ignores
    # buildset's revision and needs actual 'revision' property.
    if 'parent_got_revision' in properties:
      properties['revision'] = properties['parent_got_revision']

    properties['$build/chromium_tests'] = {
        'fixed_revisions': {
            path: update_step.json.output['manifest'][path]['revision']
            for path in update_step.json.output['fixed_revisions']
        }
    }

    properties.update(additional_properties or {})

    self.m.chromium_bootstrap.update_trigger_properties(properties)

    return properties

  def run_mb_and_compile(self,
                         builder_id,
                         compile_targets,
                         isolated_targets,
                         name_suffix,
                         mb_phase=None,
                         mb_config_path=None,
                         mb_recursive_lookup=False,
                         android_version_code=None,
                         android_version_name=None,
                         use_rts=False,
                         rts_recall=None,
                         use_st=False):
    with self.m.chromium.guard_compile(suffix=name_suffix):
      use_goma_module = False
      if self.m.chromium.c.project_generator.tool == 'mb':
        use_goma_module = self._use_goma_set_in_recipe()
        gn_args = self.m.chromium.mb_gen(
            builder_id,
            phase=mb_phase,
            mb_config_path=mb_config_path,
            use_goma=use_goma_module,
            isolated_targets=isolated_targets,
            name='generate_build_files%s' % name_suffix,
            recursive_lookup=mb_recursive_lookup,
            android_version_code=android_version_code,
            android_version_name=android_version_name,
            use_rts=use_rts,
            rts_recall=rts_recall,
            use_st=use_st)
        use_goma_in_gn_args = self._use_goma_set_in_gn_args(gn_args)
        if use_goma_module and not use_goma_in_gn_args:
          self.m.step('goma is disabled by gn', cmd=None)
          use_goma_module = False
        use_reclient = self._use_reclient(gn_args)
        if use_reclient:
          use_goma_module = False

      # gn_logs.txt contains debug info for vars with smart defaults. Display
      # its contents in the build for easy debugging.
      gn_logs_path = self.m.chromium.c.build_dir.join(
          self.m.chromium.c.build_config_fs, 'gn_logs.txt')
      self.m.path.mock_add_paths(gn_logs_path)
      if self.m.path.exists(gn_logs_path):
        self.m.file.read_text('read gn_logs.txt', gn_logs_path)

      return self.m.chromium.compile(
          compile_targets,
          name='compile%s' % name_suffix,
          use_goma_module=use_goma_module,
          use_reclient=use_reclient)

  def download_and_unzip_build(self,
                               builder_id,
                               update_step,
                               builder_config,
                               build_archive_url=None,
                               build_revision=None,
                               override_execution_mode=None,
                               read_gn_args=True):
    assert isinstance(builder_config, ctbc.BuilderConfig), \
        "builder_config argument %r was not a BuilderConfig" % builder_config
    # We only want to do this for tester bots (i.e. those which do not compile
    # locally).
    builder_spec = builder_config.builder_db[builder_id]
    execution_mode = override_execution_mode or builder_spec.execution_mode
    if execution_mode != ctbc.TEST:  # pragma: no cover
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
        'remove build directory',
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

    legacy_build_url = None
    build_revision = (
        build_revision or self.m.properties.get('parent_got_revision') or
        update_step.presentation.properties.get('got_revision') or
        update_step.presentation.properties.get('got_src_revision'))
    build_archive_url = build_archive_url or self.m.properties.get(
        'parent_build_archive_url')
    if not build_archive_url:
      legacy_build_url = self._make_legacy_build_url(builder_spec,
                                                     builder_id.group)

    self.m.archive.download_and_unzip_build(
        step_name='extract build',
        target=self.m.chromium.c.build_config_fs,
        build_url=legacy_build_url,
        build_revision=build_revision,
        build_archive_url=build_archive_url)

    if read_gn_args:
      self.m.gn.get_args(
          self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

  def _make_legacy_build_url(self, builder_spec, builder_group):
    # The group where the build was zipped and uploaded from.
    source_group = self.m.builder_group.for_parent
    # TODO(gbeaty) I think this can be removed, this method is only used when
    # downloading and unzipping a build, which should always be on a builder
    # triggered, which will have the parent_builder_group property set
    if not source_group:
      source_group = self.m.builder_group.for_current  # pragma: no cover
    return self.m.archive.legacy_download_url(
        builder_spec.build_gs_bucket,
        extra_url_components=(None if builder_group.startswith('chromium.perf')
                              else source_group))

  @contextlib.contextmanager
  def wrap_chromium_tests(self, builder_config, tests=None):
    with self.m.context(
        cwd=self.m.chromium_checkout.working_dir or self.m.path['start_dir'],
        env=self.m.chromium.get_env()):
      # Some recipes use this wrapper to setup devices and have their own way
      # to run tests. If platform is Android and tests is None, run device
      # steps.
      require_device_steps = (
          tests is None or any([t.uses_local_devices for t in tests]))

      if (self.m.chromium.c.TARGET_PLATFORM == 'android' and
          require_device_steps):
        self.m.chromium_android.common_tests_setup_steps()

      for test in (tests or []):
        for set_up_step in (test.set_up or []):
          self.m.python(
              set_up_step.name, set_up_step.script, args=set_up_step.args)
      try:
        yield
      finally:
        for test in (tests or []):
          for tear_down_step in (test.tear_down or []):
            self.m.python(
                tear_down_step.name,
                tear_down_step.script,
                args=tear_down_step.args)

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

  def build_and_isolate_failing_tests(self, builder_id, builder_config,
                                      failing_tests, bot_update_step, suffix):
    """Builds and isolates test suites in |failing_tests|.

    Args:
      builder_config: A BuilderConfig wth the configuration for the running bot.
      failing_tests: An iterable of test_suites that need to be rebuilt.
      bot_update_step: Contains information about the current checkout. Used to
                       set swarming properties.
      suffix: Should be 'without patch'. Used to annotate steps and swarming
              properties.

    Returns:
      A RawResult object with the failure message and status
    """
    compile_targets = list(
        itertools.chain(*[t.compile_targets() for t in failing_tests]))
    if compile_targets:
      # Remove duplicate targets.
      compile_targets = sorted(set(compile_targets))
      failing_swarming_tests = [
          t.isolate_target for t in failing_tests if t.uses_isolate
      ]

      raw_result = self.run_mb_and_compile(builder_id, compile_targets,
                                           failing_swarming_tests,
                                           ' (%s)' % suffix)
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
          revision_cp = (
              bot_update_step.presentation.properties['got_revision_cp']
              .replace('@', '(at)'))
          swarm_hashes_property_name = 'swarm_hashes_%s_%s' % (
              revision_cp, suffix.replace(' ', '_'))
        self.m.isolate.isolate_tests(
            self.m.chromium.output_dir,
            failing_swarming_tests,
            suffix=' (%s)' % suffix,
            swarm_hashes_property_name=swarm_hashes_property_name,
            verbose=True)

        self.set_test_command_lines(failing_tests, suffix=' (%s)' % suffix)

  def should_skip_without_patch(self, builder_config, affected_files):
    """Determine whether the without patch steps should be skipped.

    If the without patch steps should be skipped, a no-op step will be
    output to indicate why it's being skipped.

    Returns: Whether or not the without patch steps should be skipped.
    """
    reasons = []
    logs = {}

    absolute_affected_files = set(
        str(self.m.chromium.c.CHECKOUT_PATH.join(f)).replace(
            '/', self.m.path.sep) for f in affected_files)
    absolute_spec_files = set(
        str(self.m.chromium.c.source_side_spec_dir.join(f))
        for f in six.itervalues(builder_config.source_side_spec_files))
    affected_spec_files = absolute_spec_files & absolute_affected_files
    if affected_spec_files:
      reasons.append('test specs that are consumed by the builder '
                     'are also affected by the CL')
      logs['affected_spec_files'] = sorted(affected_spec_files)

    if not builder_config.retry_without_patch:
      reasons.append('retry without patch is disabled in builder config')

    if not reasons:
      return False

    result = self.m.step('without patch steps are skipped', [])
    result.presentation.step_text = '\n'.join('* {}'.format(r) for r in reasons)
    result.presentation.logs.update(logs)
    return True

  def summarize_test_failures(self,
                              test_suites,
                              retried_without_patch_suites=()):
    """
    Takes test suites and an optional list of suites retried without patch.
    Summarizes the test results in the step UI, and returns the suites which
    can be presumptively attributed to the CL.
    Args:
      test_suites: Iterable of test suites
      retried_without_patch_suites (optional): Iterable of test suites retried
        on ToT. Must be a subset of the test_suites field. Default ().
    Returns:
      An array of test suites which failed and should not be forgiven.
    """
    culpable_failures = []
    for t in test_suites:
      if not t.has_failures_to_summarize():
        continue
      if t not in retried_without_patch_suites:
        self.m.test_utils.summarize_failing_test_with_no_retries(self.m, t)
        continue
      is_tot_fail = self.m.test_utils.summarize_test_with_patch_deapplied(
          self.m, t)
      if not is_tot_fail:
        culpable_failures.append(t)
    return culpable_failures

  def _run_tests_with_retries(self, builder_id, task, deapply_changes):
    """This function runs tests with the CL patched in. On failure, this will
    deapply the patch, rebuild/isolate binaries, and run the failing tests.

    Returns:
      A Tuple of
        A RawResult object with the failure message and status
          A non-None value here means test were not run and compile failed,
        An array of test suites which irrecoverably failed.
          If all test suites succeeded, returns an empty array.
    """
    with self.wrap_chromium_tests(task.builder_config, task.test_suites):
      # Run the test. The isolates have already been created.
      invalid_test_suites, failing_test_suites = (
          self.m.test_utils.run_tests_with_patch(
              self.m,
              task.test_suites,
              retry_failed_shards=task.should_retry_failures_with_changes()))

      if self.m.code_coverage.using_coverage:
        self.m.code_coverage.process_coverage_data(task.test_suites)

      # We explicitly do not want trybots to upload profiles to GS. We prevent
      # this by ensuring all trybots wanting to run the PGO workflow have
      # skip_profile_upload.
      if self.m.pgo.using_pgo and self.m.pgo.skip_profile_upload:
        self.m.pgo.process_pgo_data(task.test_suites)

      # Exit without retries if there were invalid tests or if all tests passed
      if invalid_test_suites or not failing_test_suites:
        self.summarize_test_failures(task.test_suites)
        return None, invalid_test_suites or []

      # Also exit if there are failures but we shouldn't deapply the patch
      if self.should_skip_without_patch(task.builder_config,
                                        task.affected_files):
        self.summarize_test_failures(task.test_suites)
        return None, failing_test_suites

      deapply_changes(task.bot_update_step)
      raw_result = self.build_and_isolate_failing_tests(builder_id,
                                                        task.builder_config,
                                                        failing_test_suites,
                                                        task.bot_update_step,
                                                        'without patch')
      if raw_result and raw_result.status != common_pb.SUCCESS:
        return raw_result, []

      self.m.test_utils.run_tests(
          self.m, failing_test_suites, 'without patch', sort_by_shard=True)

      # Returns test suites whose failure is probably the CL's fault
      return None, self.summarize_test_failures(task.test_suites,
                                                failing_test_suites)

  def _build_bisect_gs_archive_url(self, builder_spec):
    return self.m.archive.legacy_upload_url(
        builder_spec.bisect_gs_bucket,
        extra_url_components=builder_spec.bisect_gs_extra)

  def _build_gs_archive_url(self, builder_spec, builder_group, buildername):
    """Returns the archive URL to pass to self.m.archive.zip_and_upload_build.

    Most builders on most groups use a standard format for the build archive
    URL, but some builders on some groups may specify custom places to upload
    builds to. These special cases include:
      'chromium.perf' or 'chromium.perf.fyi':
        Exclude the name of the group from the url.
      'tryserver.chromium.perf', or
          linux_full_bisect_builder on 'tryserver.chromium.linux':
        Return None so that the archive url specified in build_properties
        (as set on the group's configuration) is used instead.
    """
    if builder_group.startswith('chromium.perf'):
      return self.m.archive.legacy_upload_url(
          builder_spec.build_gs_bucket, extra_url_components=None)
    else:
      return self.m.archive.legacy_upload_url(
          builder_spec.build_gs_bucket,
          extra_url_components=self.m.builder_group.for_current)

  def get_common_args_for_scripts(self):
    args = []

    args.extend(['--build-config-fs', self.m.chromium.c.build_config_fs])

    paths = {
        'checkout': self.m.path['checkout'],
        'runit.py': self.repo_resource('scripts', 'tools', 'runit.py'),
        'runtest.py': self.repo_resource('scripts', 'slave', 'runtest.py'),
    }
    args.extend(['--paths', self.m.json.input(paths)])

    properties = {}
    # TODO(phajdan.jr): Remove buildnumber when no longer used.

    properties['buildername'] = self.m.buildbucket.builder_name
    properties['buildnumber'] = self.m.buildbucket.build.number
    properties['bot_id'] = self.m.swarming.bot_id
    properties['slavename'] = self.m.swarming.bot_id
    # TODO(gbeaty) Audit scripts and remove/update this as necessary
    properties['mastername'] = self.m.builder_group.for_current

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
        script=self.m.path['checkout'].join('testing', 'scripts',
                                            'get_compile_targets.py'),
        args=[
            '--output',
            self.m.json.output(),
            '--',
        ] + self.get_common_args_for_scripts(),
        step_test_data=lambda: self.m.json.test_api.output({}))
    return result.json.output

  def main_waterfall_steps(self,
                           builder_id,
                           builder_config,
                           mb_config_path=None,
                           mb_phase=None,
                           root_solution_revision=None):
    """Compiles and runs tests for chromium recipe.

    Args:
      root_solution_revision: Git revision of Chromium to check out.
        Passed down to bot_update.ensure_checkout.
        Used by CI bots of projects which are Chromium components,
        like ANGLE CI bots, to run tests with a known good version of Chromium.
        If omitted, ToT Chromium is checked out.

    Returns:
      - A RawResult object with the status of the build
        and a failure message if a failure occurred.
      - None if no failures
    """
    self.report_builders(builder_config, report_mirroring_builders=True)
    self.print_link_to_results()
    self.configure_build(builder_config)
    update_step, targets_config = self.prepare_checkout(
        builder_config,
        timeout=3600,
        root_solution_revision=root_solution_revision,
        no_fetch_tags=not builder_config.fetch_tags,
        add_blamelists=True)
    if builder_config.execution_mode == ctbc.TEST:
      self.lookup_builder_gn_args(
          builder_id,
          builder_config,
          mb_config_path=mb_config_path,
          mb_phase=mb_phase)

    compile_result = self.compile_specific_targets(
        builder_id,
        builder_config,
        update_step,
        targets_config,
        targets_config.compile_targets,
        targets_config.all_tests,
        mb_config_path=mb_config_path,
        mb_phase=mb_phase)

    if compile_result and compile_result.status != common_pb.SUCCESS:
      return compile_result

    additional_trigger_properties = self.outbound_transfer(
        builder_id, builder_config, update_step, targets_config)

    self.trigger_child_builds(
        builder_id,
        update_step,
        builder_config,
        additional_properties=additional_trigger_properties)

    upload_results = self.archive_build(builder_id, update_step, builder_config)

    self.inbound_transfer(builder_config, builder_id, update_step,
                          targets_config)

    tests = targets_config.tests_on(builder_id)
    return self.run_tests(builder_id, builder_config, tests, upload_results)

  def outbound_transfer(self, builder_id, builder_config, bot_update_step,
                        targets_config):
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
      builder_config: a BuilderConfig object for the currently executing
        builder.
      bot_update_step: the result of a previously executed bot_update step.
      targets_config: a TargetsConfig object.
    Returns:
      A dict containing additional properties that should be added to any
      triggered child builds.
    """
    isolate_transfer = any(
        t.uses_isolate for t in targets_config.tests_triggered_by(builder_id)
    ) or builder_config.expose_trigger_properties
    non_isolated_tests = [
        t for t in targets_config.tests_triggered_by(builder_id)
        if not t.uses_isolate
    ]
    package_transfer = (
        bool(non_isolated_tests) or builder_config.bisect_archive_build)

    additional_trigger_properties = {}

    if isolate_transfer:
      additional_trigger_properties['swarm_hashes'] = (
          self.m.isolate.isolated_tests)

      if self.m.chromium.c.project_generator.tool == 'mb':
        additional_trigger_properties['swarming_command_lines_digest'] = (
            self.archive_command_lines(self.swarming_command_lines))
        additional_trigger_properties['swarming_command_lines_cwd'] = (
            self.m.path.relpath(self.m.chromium.output_dir,
                                self.m.path['checkout']))

      # This gets set if we don't trigger builds. Whatever wants the output of
      # this build probably wants access to the same properties, so expose them
      # here.
      if builder_config.expose_trigger_properties:
        self.m.step.active_result.presentation.properties[
            'trigger_properties'] = additional_trigger_properties

    if (package_transfer and
        builder_config.execution_mode == ctbc.COMPILE_AND_TEST):
      self.package_build(
          builder_id,
          bot_update_step,
          builder_config,
          reasons=self._explain_package_transfer(builder_config,
                                                 non_isolated_tests))
    return additional_trigger_properties

  def inbound_transfer(self, builder_config, builder_id, bot_update_step,
                       targets_config):
    """Handles the tester half of the builder->tester transfer flow.

    See outbound_transfer for a discussion of transfer mechanisms.

    For isolate-based transfers, this merely clears out the output directory.
    For package-based transfer, this downloads the build from GS.

    Args:
      builder_config: a BuilderConfig object for the currently executing tester.
      bot_update_step: the result of a previously executed bot_update step.
      targets_config: a TargetsConfig object.
    """
    if builder_config.execution_mode != ctbc.TEST:
      return

    tests = targets_config.tests_on(builder_id)

    tests_using_isolates = [t for t in tests if t.uses_isolate]

    non_isolated_tests = [t for t in tests if not t.uses_isolate]

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
          'remove build directory',
          self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

    if package_transfer:
      # No need to read the GN args since we looked them up for testers already
      self.download_and_unzip_build(
          builder_id,
          bot_update_step,
          targets_config.builder_config,
          read_gn_args=False)
      self.m.step.empty(
          'explain extract build',
          log_name='why is this running?',
          log_text=self._explain_package_transfer(builder_config,
                                                  non_isolated_tests))

    self.download_command_lines_for_tests(tests_using_isolates, builder_config)

  def download_command_lines_for_tests(self,
                                       tests,
                                       builder_config,
                                       swarming_command_lines_digest=None,
                                       swarming_command_lines_cwd=None):
    digest = (
        swarming_command_lines_digest or
        self.m.properties.get('swarming_command_lines_digest', ''))
    cwd = (
        swarming_command_lines_cwd or
        self.m.properties.get('swarming_command_lines_cwd', ''))
    if digest:
      self._swarming_command_lines = self._download_command_lines(digest)
      for test in tests:
        if test.runs_on_swarming:
          command_line = self.swarming_command_lines.get(test.target_name, [])
          if command_line:
            # lists come back from properties as tuples, but the swarming
            # api expects this to be an actual list.
            test.raw_cmd = list(command_line)
            test.relative_cwd = cwd

  def _explain_package_transfer(self, builder_config, non_isolated_tests):
    package_transfer_reasons = [
        'This builder is doing the full package transfer because:'
    ]
    for t in non_isolated_tests:
      package_transfer_reasons.append(" - %s doesn't use isolate" % t.name)
    return package_transfer_reasons

  def archive_command_lines(self, command_lines):
    command_lines_file = self.m.path['cleanup'].join('command_lines.json')
    self.m.file.write_json('write command lines', command_lines_file,
                           command_lines)
    return self.m.cas.archive('archive command lines to RBE-CAS',
                              self.m.path['cleanup'], command_lines_file)

  def _download_command_lines(self, command_lines_digest):
    self.m.cas.download('download command lines', command_lines_digest,
                        self.m.path['cleanup'])
    command_lines_file = self.m.path['cleanup'].join('command_lines.json')
    return self.m.file.read_json(
        'read command lines', command_lines_file, test_data={})

  def _get_valid_and_invalid_results(self, unrecoverable_test_suites):
    valid = []
    invalid = []
    for test_suite in unrecoverable_test_suites:
      # Both 'with patch' and 'without patch' must have valid results to
      # skip CQ retries.
      valid_results_with_patch, _ = (
          test_suite.with_patch_failures_including_retry())
      if valid_results_with_patch and test_suite.has_valid_results(
          'without patch'):
        valid.append(test_suite)
      else:
        invalid.append(test_suite)

    return valid, invalid

  def deapply_deps(self, bot_update_step):
    with self.m.context(cwd=self.m.chromium_checkout.working_dir):
      # If tests fail, we want to fix Chromium revision only. Tests will use
      # the dependencies versioned in 'src' tree.
      self.m.bot_update.resolve_fixed_revision(bot_update_step.json.output,
                                               'src')

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

  def integration_steps(self, builder_id, builder_config):
    return self.run_tests_with_and_without_changes(
        builder_id, builder_config, deapply_changes=self.deapply_deps)

  def trybot_steps(self,
                   builder_id,
                   builder_config,
                   root_solution_revision=None):
    """Compiles and runs tests for chromium recipe.

    Args:
      root_solution_revision: Git revision of Chromium to check out.
        Passed down to bot_update.ensure_checkout.
        Used by bots on CQs of projects which are Chromium components,
        like ANGLE CQ, to run tests with a known good version of Chromium.
        If omitted, ToT Chromium is checked out.

    Returns:
      - A RawResult object with the status of the build
        and a failure message if a failure occurred.
      - None if no failures
    """
    return self.run_tests_with_and_without_changes(
        builder_id,
        builder_config,
        deapply_changes=self.deapply_patch,
        root_solution_revision=root_solution_revision)

  def raise_failure_if_cq_depends_footer_exists(self):
    # CrOS CQ supports linking & testing CLs across different repos in one
    # build via the `Cq-Depends` footer. But Chrome's CQ does not. So check
    # if the CL author has mistakenly added the footer to their chromium CL
    # and fail loudly in that case to avoid confusion.
    if self.m.tryserver.is_tryserver:
      cq_depends_footer = self.m.tryserver.get_footer(
          self.m.tryserver.constants.CQ_DEPEND_FOOTER)
      if cq_depends_footer:
        raise self.m.step.StepFailure(
            'Commit message footer {} is not supported on Chrome builders. '
            'Please remove the line(s) from the commit message and try '
            'again.'.format(self.m.tryserver.constants.CQ_DEPEND_FOOTER))

  def run_tests_with_and_without_changes(self,
                                         builder_id,
                                         builder_config,
                                         deapply_changes,
                                         root_solution_revision=None):
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
    self.raise_failure_if_cq_depends_footer_exists()

    self.report_builders(builder_config)
    self.print_link_to_results()
    raw_result, task = self.build_affected_targets(
        builder_id,
        builder_config,
        root_solution_revision=root_solution_revision)
    if raw_result and raw_result.status != common_pb.SUCCESS:
      return raw_result

    self.m.step.empty('mark: before_tests')
    if task.test_suites:
      compile_failure, unrecoverable_test_suites = self._run_tests_with_retries(
          builder_id, task, deapply_changes)
      if compile_failure:
        return compile_failure

      self.m.chromium_swarming.report_stats()

      self.m.test_utils.summarize_findit_flakiness(self.m, task.test_suites)

      if unrecoverable_test_suites:
        self.handle_invalid_test_suites(unrecoverable_test_suites)
        return result_pb2.RawResult(
            summary_markdown=self._format_unrecoverable_failures(
                unrecoverable_test_suites, 'with patch'),
            status=common_pb.FAILURE)

      # This means the tests passed, and we'll check for new flaky tests if
      # enabled for the builder.
      if (raw_result and raw_result.status == common_pb.SUCCESS and
          self.m.flakiness.check_for_flakiness):
        new_tests = self.m.flakiness.find_tests_for_flakiness(task.test_suites)
        if new_tests:
          # Executing for flakiness checks is done in chromium_tests so that we
          # avoid a circular dependency between chromium_tests and flakiness.
          return self.run_tests_for_flakiness(builder_config, new_tests)

    return None

  def handle_invalid_test_suites(self, test_suites):
    # This means there was a failure of some sort
    if self.m.tryserver.is_tryserver:
      _, invalid_suites = self._get_valid_and_invalid_results(test_suites)
      # For DEPS autoroll analysis
      if not invalid_suites:
        self.m.cq.set_do_not_retry_build()

  def _format_unrecoverable_failures(self,
                                     unrecoverable_test_suites,
                                     suffix,
                                     size_limit=700,
                                     failure_limit=4):
    """Creates list of failed tests formatted using markdown.

    Args:
      unrecoverable_test_suites: List of failed Test
          (definition can be found in steps.py)
      suffix: phase of the build to format tests for.
              Note: not necessarily the current phase of the build.
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
    unrecoverable_test_suites = self.m.py3_migration.consistent_ordering(
        unrecoverable_test_suites, key=lambda suite: suite.name)
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

      for index, failure in enumerate(
          self.m.py3_migration.consistent_ordering(deterministic_failures)):
        if index >= failure_limit or current_size >= size_limit:
          failure_size = len(deterministic_failures)
          hint = '- ...%d more failure(s) (%d total)...' % (failure_size -
                                                            index, failure_size)
          test_summary_lines.append(hint)
          current_size += len(hint)
          break

        failure_line = '- %s' % failure
        test_summary_lines.append(failure_line)
        current_size += len(failure_line)

    return '\n\n'.join(test_summary_lines)

  def run_tests_for_flakiness(self, builder_config, new_test_objects):
    suffix = self.m.flakiness.test_suffix

    with self.m.step.nest('test new tests for flakiness') as p:
      p.step_text = ('If you see failures unrelated with flaky new tests, '
                     'please use "Validate-Test-Flakiness: skip" git footer to '
                     'skip new test flakiness check and file a crbug to '
                     'Infra>Test>Flakiness component.')
      with self.wrap_chromium_tests(builder_config, new_test_objects):
        # we don't need failed test_suites because they'll be analyzed for flake
        # rates anyways through their invocation ids below.
        _, invalid_test_suites, _ = (
            self.m.test_utils.run_tests_once(self.m, new_test_objects, suffix))

        if invalid_test_suites:
          return result_pb2.RawResult(
              summary_markdown=self._format_unrecoverable_failures(
                  invalid_test_suites, suffix),
              status=common_pb.FAILURE)

    failure_counts = collections.defaultdict(int)
    # In this step, flaky tests in experimental suites (test objects) are non
    # fatal, otherwise they are fatal and will fail the build.
    flaky_non_experimental_test_objects = []
    flaky_experimental_test_objects = []
    with self.m.step.nest('calculate flake rates') as p:
      p.step_text = (
          'Tests that have exceeded the tolerated flake rate most likely '
          'indicate flakiness. See logs for details of the flaky test '
          'and the flake rate.')
      for t in new_test_objects:
        flaky = False
        rdb_results = t.get_rdb_results(suffix)
        for test_name, results in rdb_results.individual_results.items():
          for res in results:
            if res != test_result_pb2.PASS:
              key = '_'.join([t.name, test_name, rdb_results.variant_hash])
              failure_counts[key] += 1
              flaky = True
        if flaky:
          if isinstance(t, ExperimentalTest):
            flaky_experimental_test_objects.append(t)
          else:
            flaky_non_experimental_test_objects.append(t)

      # Equivalent to `if failure_counts:`.
      if flaky_experimental_test_objects or flaky_non_experimental_test_objects:
        p.logs['flaky tests'] = ('\n'.join([
            'test: {}, # of failures: {}, total # of runs: {}'.format(
                k, v, self.m.flakiness._repeat_count)
            for k, v in failure_counts.items()
        ]))

        if flaky_non_experimental_test_objects:
          p.status = self.m.step.FAILURE
          # TODO(crbug/1204163) - Update the summary markdown to reflect flaky
          # tests and their flake rates for easier identification for fatal and
          # non-fatal flakiness.
          return result_pb2.RawResult(
              summary_markdown=self._format_unrecoverable_failures(
                  flaky_non_experimental_test_objects, suffix),
              status=common_pb.FAILURE)

        # When there is non fatal flakiness, let users know why the build
        # doesn't fail.
        p.step_text += ('\nFlaky tests in logs are non fatal because they come '
                        'from experimental suites.')

    return None

  def determine_compilation_targets(self, builder_id, builder_config,
                                    affected_files, targets_config):
    compile_targets = targets_config.compile_targets
    test_targets = sorted(
        set(self._all_compile_targets(targets_config.all_tests)))

    # Use analyze to determine the compile targets that are affected by the CL.
    # Use this to prune the relevant compile targets and test targets.
    if self.m.tryserver.is_tryserver:
      skip_analysis_reasons = list(
          self.m.chromium_bootstrap.skip_analysis_reasons)
      skip_analysis_logs = {}

      absolute_affected_files = set(
          str(self.m.chromium.c.CHECKOUT_PATH.join(f)).replace(
              '/', self.m.path.sep) for f in affected_files)
      absolute_spec_files = set(
          str(self.m.chromium.c.source_side_spec_dir.join(f))
          for f in six.itervalues(builder_config.source_side_spec_files))
      affected_spec_files = absolute_spec_files & absolute_affected_files
      # If any of the spec files that we used for determining the targets/tests
      # is affected, skip doing analysis, just build/test all of them
      if affected_spec_files:
        skip_analysis_reasons.append(
            'test specs that are consumed by the builder '
            'are also affected by the CL')
        skip_analysis_logs['affected_spec_files'] = sorted(affected_spec_files)

      if skip_analysis_reasons:
        step_result = self.m.step('analyze', [])
        text = ['skipping analyze'] + skip_analysis_reasons
        step_result.presentation.step_text = '\n* '.join(text)
        for log, contents in sorted(six.iteritems(skip_analysis_logs)):
          step_result.presentation.logs[log] = contents
        return test_targets, compile_targets

      additional_compile_targets = sorted(
          set(compile_targets) - set(test_targets))
      analyze_names = ['chromium'] + list(builder_config.analyze_names)
      mb_config_path = (
          self.m.chromium.c.project_generator.config_path or
          self.m.path['checkout'].join('tools', 'mb', 'mb_config.pyl'))
      analyze_names.append(self.m.chromium.c.TARGET_PLATFORM)
      test_targets, compile_targets = self.m.filter.analyze(
          affected_files,
          test_targets,
          additional_compile_targets,
          'trybot_analyze_config.json',
          builder_id=builder_id,
          mb_config_path=mb_config_path,
          additional_names=analyze_names)

    return test_targets, compile_targets

  def configure_swarming(self, precommit, task_output_stdout=None, **kwargs):
    self.m.chromium_swarming.configure_swarming(
        'chromium', precommit=precommit, **kwargs)

    if task_output_stdout:
      self.m.chromium_swarming.task_output_stdout = task_output_stdout

  def get_quickrun_options(self, builder_config):
    use_rts = (
        self.m.cq.active and self.m.cq.run_mode == self.m.cq.QUICK_DRY_RUN and
        builder_config.regression_test_selection == try_spec.QUICK_RUN_ONLY
    ) or builder_config.regression_test_selection == try_spec.ALWAYS

    use_st = (self.m.cq.active and
              self.m.cq.run_mode == self.m.cq.QUICK_DRY_RUN and
              builder_config.filter_stable_test == try_spec.QUICK_RUN_ONLY
             ) or builder_config.filter_stable_test == try_spec.ALWAYS

    if use_rts or use_st:
      step_result = self.m.step('quick run options', [])
      if use_rts:
        step_result.presentation.properties['rts_was_used'] = use_rts
        step_result.presentation.links[
            'use_rts: true'] = 'https://bit.ly/chromium-rts'
        step_result.presentation.links['file a bug'] = (
            'https://bugs.chromium.org/p/chromium/issues/entry?'
            'template=Quick%20Run%20Issue')

        # RTS-enabled Quick Run builds can't be reused for non-quick runs
        # because they are slightly less safe than normal builds
        if builder_config.regression_test_selection == try_spec.QUICK_RUN_ONLY:
          self.m.cq.allow_reuse_for(self.m.cq.QUICK_DRY_RUN)

      if use_st:
        step_result.presentation.properties['st_was_used'] = use_st
        step_result.presentation.step_text += '<br/>use_st: true'

        # RTS-enabled Quick Run builds can't be reused for non-quick runs
        # because they are slightly less safe than normal builds
        if builder_config.filter_stable_test == try_spec.QUICK_RUN_ONLY:
          self.m.cq.allow_reuse_for(self.m.cq.QUICK_DRY_RUN)

    return (use_rts, use_st)

  def build_affected_targets(self,
                             builder_id,
                             builder_config,
                             root_solution_revision=None,
                             isolate_output_files_for_coverage=False):
    """Builds targets affected by change.

    Args:
      builders: An optional mapping from <group, buildername> to
                build/test settings. For an example of defaults for chromium,
                see scripts/slave/recipe_modules/chromium_tests/chromium.py
      mirrored_bots: An optional mapping from <group, buildername> of the
                     trybot to configurations of the mirrored CI bot. Defaults
                     are in ChromiumTestsApi.
      isolate_output_files_for_coverage: Whether to also upload all test
        binaries and other required code coverage output files to one hash.

    Returns:
      A Tuple of
        RawResult object with the status of compile step
          and the failure message if it failed
        Configuration of the build/test.
    """
    use_rts, use_st = self.get_quickrun_options(builder_config)

    self.configure_build(builder_config, use_rts)

    self.m.chromium.apply_config('trybot_flavor')

    # This rolls chromium checkout, applies the patch, runs gclient sync to
    # update all DEPS.
    # Chromium has a lot of tags which slow us down, we don't need them on
    # trybots, so don't fetch them.
    bot_update_step, targets_config = self.prepare_checkout(
        builder_config,
        timeout=3600,
        no_fetch_tags=True,
        root_solution_revision=root_solution_revision)

    self.configure_swarming(
        self.m.tryserver.is_tryserver, task_output_stdout='none')

    affected_files = self.m.chromium_checkout.get_files_affected_by_patch(
        report_via_property=True
    )
    is_deps_only_change = affected_files == ["DEPS"]

    # Must happen before without patch steps.
    if self.m.code_coverage.using_coverage:
      self.m.code_coverage.instrument(
          affected_files, is_deps_only_change=is_deps_only_change)

    tests = []
    if not builder_config.is_compile_only:
      tests = targets_config.all_tests

    test_targets, compile_targets = self.determine_compilation_targets(
        builder_id, builder_config, affected_files, targets_config)

    # Compiles and isolates test suites.
    raw_result = result_pb2.RawResult(status=common_pb.SUCCESS)
    if compile_targets:
      tests = self.tests_in_compile_targets(test_targets, tests)

      compile_targets = sorted(set(compile_targets))
      raw_result = self.compile_specific_targets(
          builder_id,
          builder_config,
          bot_update_step,
          targets_config,
          compile_targets,
          tests,
          override_execution_mode=ctbc.COMPILE_AND_TEST,
          use_rts=use_rts,
          rts_recall=builder_config.regression_test_selection_recall,
          use_st=use_st,
          isolate_output_files_for_coverage=isolate_output_files_for_coverage)
    else:
      # Even though the patch doesn't require a compile on this platform,
      # we'd still like to run tests not depending on
      # compiled targets (that's obviously not covered by the
      # 'analyze' step) if any source files change.
      if any(self._is_source_file(f) for f in affected_files):
        tests = [t for t in tests if not t.compile_targets()]
      else:
        tests = []

    return raw_result, Task(builder_config, tests, bot_update_step,
                            affected_files)

  def get_first_tag(self, key):
    '''Returns the first buildbucket tag value for a given key

    Buildbucket tags can have multiple values for a single key, but in most
    cases, we can assume just one value.

    Args:
      key: the key to look up
    Returns:
      the first value for this key or None
    '''
    for string_pair in self.m.buildbucket.build.tags:
      if string_pair.key == key:
        return string_pair.value

    return None

  def report_builders(self, builder_config, report_mirroring_builders=False):
    """Reports the builders being executed by the bot."""

    # Tester - returns (parent ID, builder ID)
    # Builder - returns (builder ID, )
    # This way testers sort after their triggering builder and before
    # other builders
    def details(builder_id):
      spec = builder_config.builder_db[builder_id]
      if not spec.parent_buildername:
        return (builder_id,)
      parent_builder_id = chromium.BuilderId.create_for_group(
          spec.parent_builder_group or builder_id.group,
          spec.parent_buildername)
      return (parent_builder_id, builder_id)

    builder_ids = (
        builder_config.builder_ids_in_scope_for_testing
        if self.m.tryserver.is_tryserver else builder_config.builder_ids)

    builder_details = sorted(details(b) for b in builder_ids)

    def present(details):
      if len(details) == 1:
        builder_id = details[0]
        return "running builder '{}' on group '{}'".format(
            builder_id.builder, builder_id.group)
      else:
        parent_builder_id, builder_id = details
        return ("running tester '{}' on group '{}'"
                " against builder '{}' on group '{}'").format(
                    builder_id.builder, builder_id.group,
                    parent_builder_id.builder, parent_builder_id.group)

    lines = [''] + [present(d) for d in sorted(builder_details)]

    result = self.m.step.empty('report builders', step_text='\n'.join(lines))

    if report_mirroring_builders and builder_config.mirroring_try_builders:
      # TODO(gbeaty): This property is not well named, it suggests the opposite
      # relationship of what it is
      result.presentation.properties['mirrored_builders'] = sorted([
          '{}:{}'.format(m.group, m.builder)
          for m in builder_config.mirroring_try_builders
      ])

    # Links to upstreams help people figure out if upstreams are broken too
    # TODO(gbeaty): When we switch to using buckets to identify builders instead
    # of group, we can have an authoritative value for the bucket to use
    # in these links, for now rely on convention:
    # try -> ci
    for d in builder_details:
      for builder_id in d:
        result.presentation.links[builder_id.builder] = (
            'https://ci.chromium.org/p/{}/builders/{}/{}'.format(
                self.m.buildbucket.build.builder.project,
                self.m.buildbucket.build.builder.bucket.replace('try', 'ci'),
                builder_id.builder,
            ))

  def print_link_to_results(self):
    """Prints a step with a link to the 'test results' tab in Milo.

    Useful for led builds that are stuck on the old UI but are still able to
    render the results tab given the right URL.

    TODO(crbug.com/1264479): Remove this once led builds are fully on the new UI
    """
    if not self.m.led.launched_by_led:
      return
    server = self.m.swarming.current_server
    server = server.replace('http://', '')
    server = server.replace('https://', '')
    url = 'https://luci-milo.appspot.com/ui/inv/task-{}-{}/test-results'.format(
        server, self.m.swarming.task_id)
    result = self.m.step('test results link', cmd=None)
    result.presentation.links['results UI'] = url

  def _all_compile_targets(self, tests):
    """Returns the compile_targets for all the Tests in |tests|."""
    return sorted(set(x for test in tests for x in test.compile_targets()))

  def _is_source_file(self, filepath):
    """Returns true iff the file is a source file."""
    _, ext = self.m.path.splitext(filepath)
    return ext in ['.c', '.cc', '.cpp', '.h', '.java', '.mm']

  def tests_in_compile_targets(self, compile_targets, tests):
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

  def lookup_builder_gn_args(self,
                             builder_id,
                             builder_config,
                             mb_config_path=None,
                             mb_phase=None):
    # Lookup GN args for the associated builder
    parent_builder_id = chromium.BuilderId.create_for_group(
        builder_config.parent_builder_group or builder_id.group,
        builder_config.parent_buildername)
    parent_builder_spec = builder_config.builder_db[parent_builder_id]

    # Make the chromium config that the parent would use
    parent_chromium_config = self.m.chromium.make_config(
        parent_builder_spec.chromium_config,
        **parent_builder_spec.chromium_config_kwargs)
    for c in parent_builder_spec.chromium_apply_config:
      self.m.chromium.apply_config(c, parent_chromium_config)

    android_version_name, android_version_code = (
        self.get_android_version_details(parent_builder_spec.android_version))
    self.m.chromium.mb_lookup(
        parent_builder_id,
        mb_config_path=mb_config_path,
        chromium_config=parent_chromium_config,
        phase=mb_phase,
        use_goma=self._use_goma_set_in_recipe(parent_chromium_config),
        android_version_name=android_version_name,
        android_version_code=android_version_code,
        name='lookup builder GN args')

  def _gen_runtime_dict_for_skylab(self, target):
    """Generate the rel path of runtime deps to src dir.

    Skylab DUT in CrOS does not support isolate. We reuse the isolate file
    generated at compile step to decide the runtime dependencies.

    Args:
      target: The ninja build target for the test, e.g. url_unittests.

    Returns:
      runtime_dict: Relative paths to the src dir of the runtime deps, with
          the key of its relative path to build dir, original form in the
          isolate file.
    """
    with self.m.step.nest('collect runtime deps for %s' % target) as step:
      src_dir = self.m.path['checkout']
      build_dir = self.m.chromium.output_dir
      abs_runtime_deps = build_dir.join(target + '.isolate')
      if not self.m.path.exists(abs_runtime_deps):
        failure_msg = 'Failed to find the %s.isolate.' % target
        step.presentation.status = self.m.step.FAILURE
        raise self.m.step.StepFailure(failure_msg)

      content = self.m.file.read_text('read isolate file', abs_runtime_deps)
      try:
        isolate_dict = eval(content.strip())
      except:
        failure_msg = 'Failed to parse the %s.isolate' % target
        step.presentation.status = self.m.step.FAILURE
        raise self.m.step.StepFailure(failure_msg)

      if len(isolate_dict.get('variables', {}).get('files', [])) == 0:
        failure_msg = 'No dependencies attached to target %s.' % target
        step.presentation.status = self.m.step.FAILURE
        raise self.m.step.StepFailure(failure_msg)

      runtime_dict = {}
      for f in isolate_dict['variables']['files']:
        abs_file_path = self.m.path.abspath(self.m.path.join(build_dir, f))
        rel_to_out_dir = self.m.path.relpath(abs_file_path, src_dir)
        runtime_dict[f] = str(rel_to_out_dir)

      return runtime_dict

  def _upload_runtime_deps_for_skylab(self, gcs_bucket, gcs_path, target,
                                      runtime_deps):

    def is_dir(rel_path):
      return self.m.path.isdir(self.m.path['checkout'].join(rel_path))

    def is_file(rel_path):
      return self.m.path.isfile(self.m.path['checkout'].join(rel_path))

    # Allow other account to access files we send to skylab.
    # Some tests may use non-root account to run the executable in
    # squashfs, which does not exist in the build bot. For these tests,
    # we make the squashfs image account agnostic by expanding its
    # content's mode bit of others, e.g. 750 to 755 or 640 to 644.
    def _update_perm(rel_path):
      self.m.step(
          'update permissions for %s' % rel_path,
          ['chmod', '-R', 'o=g',
           str(self.m.path['checkout'].join(rel_path))])
      return rel_path

    with self.m.step.nest('upload skylab runtime deps for %s' % target):
      #TODO(crbug/1276489): Remove below condition once we get rid of the
      # build target lacros_version_metadata in src.
      if not self.m.path.exists(
          self.m.chromium.output_dir.join('metadata.json')):
        version = self.m.chromium.get_version()
        version_str = '%(MAJOR)s.%(MINOR)s.%(BUILD)s.%(PATCH)s' % version
        self.m.file.write_json(
            'write metadata.json',
            self.m.chromium.output_dir.join('metadata.json'),
            dict(content={'version': version_str}, metadata_version=1))

      # Lacros TLS provision requires a metadata.json containing the chrome
      # version along with the squashfs file. If user does not configure it
      # in the compile targets, we create one for the tests.
      out_dir = self.m.path.relpath(self.m.chromium.output_dir,
                                    self.m.chromium_checkout.checkout_dir)

      metadata_arch = arch_prop.ArchiveData(
          gcs_bucket=gcs_bucket,
          gcs_path='%s/%s' % (gcs_path, target),
          archive_type=arch_prop.ArchiveData.ARCHIVE_TYPE_FLATTEN_FILES,
          base_dir=str(out_dir),
          files=['metadata.json'],
      )
      squash_arch = arch_prop.ArchiveData(
          gcs_bucket=gcs_bucket,
          gcs_path='%s/%s/lacros_compressed.squash' % (gcs_path, target),
          archive_type=arch_prop.ArchiveData.ARCHIVE_TYPE_SQUASHFS,
          base_dir='src',
          files=[_update_perm(v) for v in runtime_deps.values() if is_file(v)],
          dirs=[_update_perm(v) for v in runtime_deps.values() if is_dir(v)],
          root_permission_override='755',
      )
      self.m.archive.generic_archive(
          build_dir=self.m.chromium_checkout.checkout_dir,
          update_properties={},
          config=arch_prop.InputProperties(
              archive_datas=[squash_arch, metadata_arch]))
      return 'gs://{}{}/{}/{}'.format(
          gcs_bucket, '/experimental' if self.m.runtime.is_experimental else '',
          gcs_path, target)

  def _prepare_artifact_for_skylab(self, builder_config, tests):
    if not (builder_config.skylab_gs_bucket and tests):
      return
    gcs_path = ''
    if builder_config.skylab_gs_extra:
      gcs_path += '%s/' % builder_config.skylab_gs_extra
    gcs_path += '%d' % self.m.buildbucket.build.id
    with self.m.step.nest('prepare skylab tests'):
      tests_by_target = collections.defaultdict(list)
      for t in tests:
        tests_by_target[t.target_name].append(t)
      runtime_dict_by_target = {
          t: self._gen_runtime_dict_for_skylab(t)
          for t in sorted(tests_by_target)
      }
      gcs_path_by_target = {
          t:
          self._upload_runtime_deps_for_skylab(builder_config.skylab_gs_bucket,
                                               gcs_path, t, r)
          for t, r in runtime_dict_by_target.items()
      }
      for target, tests in tests_by_target.items():
        for t in tests:
          t.exe_rel_path = runtime_dict_by_target.get(target).get(
              './chrome' if t.is_tast_test else 'bin/run_%s' % t.target_name)
          t.lacros_gcs_path = gcs_path_by_target.get(target)

  def run_tests(self, builder_id, builder_config, tests, upload_results=None):
    if not tests:
      return

    self.configure_swarming(False, builder_group=builder_id.group)
    test_runner = self.create_test_runner(
        tests,
        serialize_tests=builder_config.serialize_tests,
        # If any tests export coverage data we want to retry invalid shards due
        # to an existing issue with occasional corruption of collected coverage
        # data.
        retry_invalid_shards=any(
            t.runs_on_swarming and t.isolate_profile_data for t in tests),
    )
    with self.wrap_chromium_tests(builder_config, tests):
      test_failure_summary = test_runner()

      if self.m.code_coverage.using_coverage:
        self.m.code_coverage.process_coverage_data(tests)

      if self.m.pgo.using_pgo:
        self.m.pgo.process_pgo_data(tests)

      test_success = True
      if test_failure_summary:
        test_success = False

      self.m.archive.generic_archive_after_tests(
          build_dir=self.m.chromium.output_dir,
          upload_results=upload_results,
          test_success=test_success)

      return test_failure_summary

  def get_milo_test_results_url(self, test_name):
    """Returns a URL to the "Test Results" tab in Milo for the current build."""
    url = 'https://luci-milo.appspot.com/ui/inv/'
    inv_name = self.m.resultdb.current_invocation
    if inv_name.startswith('invocations/'):
      inv_name = inv_name[12:]
    return url + inv_name + '/test-results?' + urlencode({'q': test_name})
