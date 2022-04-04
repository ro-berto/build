# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Compiles with patch and isolates tests"""

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec
from PB.recipes.build.chromium.compilator import InputProperties
from PB.recipe_engine import result as result_pb2
from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from recipe_engine import post_process
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import common as resultdb_common
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import resultdb as resultdb_pb2

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'depot_tools/tryserver',
    'filter',
    'flakiness',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/cas',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'test_utils',
]

PROPERTIES = InputProperties

ORCHESTRATOR_ALL_TARGET_NAME = 'infra/orchestrator:orchestrator_all'
ORCHESTRATOR_RUNTIME_DEPS_FILE = 'orchestrator_all.runtime_deps'


def compilator_steps(api, properties):
  api.tryserver.require_is_tryserver()

  report_parent_orchestrator_build(api, properties)

  if not api.buildbucket.gitiles_commit.id and not (
      properties.deps_revision_overrides and properties.root_solution_revision):
    raise api.step.InfraFailure(
        'Compilator requires gitiles_commit or deps_revision_overrides to know'
        ' which revision to check out')

  with api.chromium.chromium_layout():
    orchestrator = properties.orchestrator.builder_name
    builder_group = properties.orchestrator.builder_group
    orch_builder_id = chromium.BuilderId.create_for_group(
        builder_group, orchestrator)

    _, orch_builder_config = (
        api.chromium_tests_builder_config.lookup_builder(
            builder_id=orch_builder_id))

    api.chromium_tests.report_builders(orch_builder_config)

    # Implies that this compilator build must be compiled without a patch
    # so that the orchestrator can retry these swarming tests without patch
    use_rts, _ = api.chromium_tests.get_quickrun_options(orch_builder_config)
    if properties.swarming_targets:
      api.chromium_tests.configure_build(
          orch_builder_config,
          use_rts,
      )
      api.chromium.apply_config('trybot_flavor')
      bot_update_step, targets_config = api.chromium_tests.prepare_checkout(
          orch_builder_config,
          timeout=3600,
          set_output_commit=orch_builder_config.set_output_commit,
          no_fetch_tags=True,
          enforce_fetch=True,
          patch=False,
          runhooks_suffix='without patch')

      # code coverage is ignored for without patch steps, but compile will
      # error if there is no files_to_instrument.txt file
      if api.code_coverage.using_coverage:
        api.code_coverage.instrument([])

      # properties.swarming_targets should only be targets required for
      # isolated swarming tests, but a non-isolated swarming test could,
      # although rare, have a target_name that is also used by an isolated
      # swarming test. Checking for t.uses_isolate makes sure that we don't
      # include those non-isolated tests and end up running them too in this
      # build.
      test_suites = [
          t for t in targets_config.all_tests
          if t.target_name in properties.swarming_targets and t.uses_isolate
      ]
      raw_result = api.chromium_tests.build_and_isolate_failing_tests(
          orch_builder_id,
          orch_builder_config,
          test_suites,
          bot_update_step,
          'without patch',
          additional_compile_targets=[ORCHESTRATOR_ALL_TARGET_NAME])
    else:
      raw_result, task = api.chromium_tests.build_affected_targets(
          orch_builder_id,
          orch_builder_config,
          isolate_output_files_for_coverage=True,
          additional_compile_targets=[ORCHESTRATOR_ALL_TARGET_NAME])
      test_suites = task.test_suites

      deleted_files = get_deleted_files(api, task.affected_files)
      if deleted_files:
        del_files_step = api.step.empty('deleted files')
        del_files_step.presentation.properties['deleted_files'] = deleted_files
        del_files_step.presentation.logs['deleted_files'] = (
            api.json.dumps(deleted_files, indent=2))

    if raw_result and raw_result.status != common_pb.SUCCESS:
      return raw_result

    if any(t.uses_isolate for t in test_suites):
      if ('remove_src_checkout_experiment' in
          api.buildbucket.build.input.experiments):
        archive_src_side_deps(api)

      # Isolate the tests first so the Orchestrator can trigger them asap
      trigger_properties = {}
      trigger_properties['swarming_command_lines_digest'] = (
          api.chromium_tests.archive_command_lines(
              api.chromium_tests.swarming_command_lines))
      trigger_properties['swarming_command_lines_cwd'] = (
          api.m.path.relpath(api.m.chromium.output_dir, api.m.path['checkout']))
      trigger_properties['swarm_hashes'] = api.isolate.isolated_tests

      properties_step = api.step('swarming trigger properties', [])
      properties_step.presentation.properties[
          'swarming_trigger_properties'] = trigger_properties
      properties_step.presentation.logs[
          'swarming_trigger_properties'] = api.m.json.dumps(
              trigger_properties, indent=2)

    non_isolated_tests = [t for t in test_suites if not t.uses_isolate]
    if non_isolated_tests:
      test_runner = api.chromium_tests.create_test_runner(
          non_isolated_tests,
          suffix='with patch',
      )
      with api.chromium_tests.wrap_chromium_tests(orch_builder_config,
                                                  non_isolated_tests):
        raw_result = test_runner()
        if raw_result and raw_result.status != common_pb.SUCCESS:
          return raw_result

      # check for new flaky tests on successful run w/ patch
      if api.flakiness.check_for_flakiness:
        new_tests = api.flakiness.find_tests_for_flakiness(
            non_isolated_tests, affected_files=task.affected_files)
        if new_tests:
          return api.chromium_tests.run_tests_for_flakiness(
              orch_builder_config, new_tests)

    return raw_result


def archive_src_side_deps(api):
  """Archives src-side deps that the Orchestrator needs to run tests/coverage"""
  with api.step.nest('archive src-side dep paths') as nested_step:
    dep_paths = get_src_side_dep_paths(api)

    digest = api.cas.archive('archive src-side deps', str(api.path['checkout']),
                             *dep_paths)
    nested_step.presentation.properties['src_side_deps_digest'] = digest
    nested_step.presentation.logs['dep paths'] = api.json.dumps(
        dep_paths, indent=2)


def get_src_side_dep_paths(api):
  """Get src-side paths to archive.

  The chromium compile step writes which src-side deps to archive.
  The orchestrator build will use the CAS hash to download these deps to run
  tests and code coverage.

  Returns:
    List of string paths
  """
  dep_paths = set()
  runtime_deps_file = api.chromium.output_dir.join(
      ORCHESTRATOR_RUNTIME_DEPS_FILE)
  paths = (
      api.file.read_text('read orchestrator_all.runtime_deps',
                         runtime_deps_file).rstrip().split('\n'))
  for path in paths:
    # Paths written in these files look like '../../testing/X.py' relative
    # to the output dir
    file_path = api.path.relpath(
        api.chromium.output_dir.join(path), api.path['checkout'])
    file_path = api.path['checkout'].join(file_path)

    # Path can be a regex pattern
    if "*" in str(file_path):
      paths = api.file.glob_paths('get files that match pattern',
                                  api.path['checkout'], str(file_path))
      dep_paths.update([str(p) for p in paths])
    else:
      dep_paths.add(str(file_path))
  return list(dep_paths)


def get_deleted_files(api, affected_files):
  deleted_files = []
  for f in affected_files:
    if not api.path.exists(api.path['checkout'].join(f)):
      deleted_files.append(f)
  return deleted_files


def report_parent_orchestrator_build(api, properties):
  result = api.step(
      'report parent orchestrator build: {}'.format(
          properties.orchestrator.builder_name), [])
  result.presentation.links['orchestrator build'] = (
      create_orchestrator_milo_link(
          api.buildbucket.build.infra.swarming.parent_run_id,
          api.buildbucket.build.infra.swarming.hostname))


def create_orchestrator_milo_link(swarming_task_id, host):
  return 'https://luci-milo.appspot.com/swarming/task/{}?server={}'.format(
      swarming_task_id, host)


def global_shutdown_summary_markdown(parent_build_url):
  message = ('Parent orchestrator [build]({}) ended, causing this build to be '
             'canceled.')
  return message.format(parent_build_url)


def RunSteps(api, properties):
  try:
    return compilator_steps(api, properties)
  finally:
    if api.runtime.in_global_shutdown:
      # pylint: disable=lost-exception
      # Compilator builds can experience a variety of exceptions when its
      # swarming tasks are killed, depending on where in the recipe it was
      # killed.
      # The important part is that the build status is CANCELED.
      return result_pb2.RawResult(
          status=common_pb.CANCELED,
          summary_markdown=global_shutdown_summary_markdown(
              create_orchestrator_milo_link(
                  api.buildbucket.build.infra.swarming.parent_run_id,
                  api.buildbucket.build.infra.swarming.hostname)))


def GenTests(api):
  _TEST_BUILDERS = ctbc.BuilderDatabase.create({
      'chromium.test': {
          'chromium-rel':
              ctbc.BuilderSpec.create(
                  chromium_config='chromium',
                  gclient_config='chromium',
              ),
      },
  })

  _TEST_TRYBOTS = ctbc.TryDatabase.create({
      'tryserver.chromium.test': {
          'rts-rel':
              ctbc.TrySpec.create(
                  mirrors=[
                      ctbc.TryMirror.create(
                          builder_group='chromium.test',
                          buildername='chromium-rel',
                          tester='chromium-rel',
                      ),
                  ],
                  regression_test_selection=try_spec.QUICK_RUN_ONLY,
              ),
      }
  })

  def override_test_spec():
    return api.chromium_tests.read_source_side_spec(
        'fake-group', {
            'fake-builder': {
                'scripts': [{
                    "isolate_profile_data": True,
                    "name": "check_static_initializers",
                    "script": "check_static_initializers.py",
                    "swarming": {},
                    "test_id_prefix": "ninja://check_static_initializers/"
                }],
            },
            'fake-tester': {
                'gtest_tests': [{
                    'name': 'browser_tests',
                    'swarming': {
                        'can_use_on_swarming_builders': True
                    },
                }],
            },
        })

  ctbc_api = api.chromium_tests_builder_config

  def ctbc_properties():
    return ctbc_api.properties(
        ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
            builder_group='fake-group',
            builder='fake-builder',
        ).with_mirrored_tester(
            builder_group='fake-group',
            builder='fake-tester',
        ).assemble())

  yield api.test(
      'basic',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      api.filter.suppress_analyze(),
      override_test_spec(),
      api.post_process(post_process.StepTextContains, 'report builders', [
          "running tester 'fake-tester' on group 'fake-group' against "
          "builder 'fake-builder' on group 'fake-group'"
      ]),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--patch_ref']),
      api.post_process(post_process.MustRun, 'compile (with patch)'),
      api.post_process(post_process.MustRun, 'isolate tests (with patch)'),
      api.post_process(post_process.MustRun, 'swarming trigger properties'),
      api.post_process(post_process.MustRun,
                       'check_static_initializers (with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_gitiles_commit_and_deps_revision_overrides',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
      ),
      api.platform.name('linux'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_root_solution_revision',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
      ),
      api.platform.name('linux'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'),
              deps_revision_overrides={'src/v8': 'v8deadbeef'})),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'deps_revision_overrides_and_root_solution_revision',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          git_repo='https://chromium.googlesource.com/v8/v8',
      ),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'),
              deps_revision_overrides={'src/v8': 'v8deadbeef'},
              root_solution_revision='srcdeadbeef')),
      api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
              'base': {
                  'exclusions': ['v8/f.*'],
              },
              'chromium': {
                  'exclusions': [],
              },
          })),
      override_test_spec(),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--patch_ref']),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--revision', 'src@srcdeadbeef']),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--revision', 'src/v8@v8deadbeef']),
      api.post_process(post_process.MustRun, 'compile (with patch)'),
      api.post_process(post_process.MustRun, 'isolate tests (with patch)'),
      api.post_process(post_process.MustRun, 'swarming trigger properties'),
      api.post_process(post_process.MustRun,
                       'check_static_initializers (with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'output_deleted_files',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      api.tryserver.get_files_affected_by_patch(['foo.cc', 'bar/baz.cc']),
      api.path.exists(api.path['checkout'].join('foo.cc')),
      api.post_process(post_process.MustRun, 'deleted files'),
      api.post_process(post_process.PropertyEquals, 'deleted_files',
                       ['bar/baz.cc']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'archive_src_side_runtime_deps',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
          experiments=['remove_src_checkout_experiment']),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      api.filter.suppress_analyze(),
      override_test_spec(),
      api.step_data(
          'archive src-side dep paths.read orchestrator_all.runtime_deps',
          api.file.read_text(
              '../../testing/merge_scripts/merge_api.py\n'
              '../../testing/merge_scripts/standard_gtest_merge.py')),
      api.post_process(
          post_process.LogContains, 'archive src-side dep paths', 'dep paths', [
              '[CACHE]/builder/src/testing/merge_scripts/merge_api.py',
              '[CACHE]/builder/src/testing/merge_scripts/'
              'standard_gtest_merge.py'
          ]),
      api.post_process(
          post_process.StepCommandContains,
          'compile (with patch)',
          [ORCHESTRATOR_ALL_TARGET_NAME],
      ),
      api.post_process(post_process.MustRun,
                       'archive src-side dep paths.archive src-side deps'),
      api.post_process(post_process.PropertiesContain, 'src_side_deps_digest'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'archive_src_side_runtime_deps_glob_pattern',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
          experiments=['remove_src_checkout_experiment']),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      api.filter.suppress_analyze(),
      override_test_spec(),
      api.step_data(
          'archive src-side dep paths.read orchestrator_all.runtime_deps',
          api.file.read_text('../../testing/buildbot/*.json')),
      api.step_data(
          'archive src-side dep paths.get files that match pattern',
          api.file.glob_paths([
              'testing/buildbot/chromium.linux.json',
              'testing/buildbot/chromium.android.json'
          ])),
      api.post_process(
          post_process.LogContains, 'archive src-side dep paths', 'dep paths', [
              '[CACHE]/builder/src/testing/buildbot/chromium.linux.json',
              '[CACHE]/builder/src/testing/buildbot/chromium.android.json'
          ]),
      api.post_process(
          post_process.StepCommandContains,
          'compile (with patch)',
          [ORCHESTRATOR_ALL_TARGET_NAME],
      ),
      api.post_process(post_process.MustRun,
                       'archive src-side dep paths.archive src-side deps'),
      api.post_process(post_process.PropertiesContain, 'src_side_deps_digest'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'quick run rts',
      api.properties(
          **{
              "$recipe_engine/cq": {
                  "active": True,
                  "dryRun": True,
                  "runMode": "QUICK_DRY_RUN",
                  "topLevel": True
              }
          }),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      api.chromium_tests_builder_config.databases(_TEST_BUILDERS,
                                                  _TEST_TRYBOTS),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_group='tryserver.chromium.test',
                  builder_name='rts-rel'))),
      api.chromium_tests.read_source_side_spec('chromium.test', {
          'chromium-rel': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.DropExpectation),
      api.filter.suppress_analyze(),
  )

  yield api.test(
      'quick run rts without_patch',
      api.properties(
          **{
              "$recipe_engine/cq": {
                  "active": True,
                  "dryRun": True,
                  "runMode": "QUICK_DRY_RUN",
                  "topLevel": True
              }
          }),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      api.chromium_tests_builder_config.databases(_TEST_BUILDERS,
                                                  _TEST_TRYBOTS),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_group='tryserver.chromium.test',
                  builder_name='rts-rel'),
              swarming_targets=['base_unittests'])),
      api.chromium_tests.read_source_side_spec('chromium.test', {
          'chromium-rel': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'global_shutdown',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      override_test_spec(),
      api.filter.suppress_analyze(),
      api.runtime.global_shutdown_on_step('isolate tests (with patch)'),
      api.post_process(post_process.ResultReasonRE,
                       '.*causing this build to be canceled.*'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'without_patch',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      api.platform.name('linux'),
      api.code_coverage(use_clang_coverage=True),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'),
              swarming_targets=['browser_tests'])),
      override_test_spec(),
      api.post_process(post_process.StepTextContains, 'report builders', [
          "running tester 'fake-tester' on group 'fake-group' against "
          "builder 'fake-builder' on group 'fake-group'"
      ]),
      api.post_process(post_process.StepCommandDoesNotContain,
                       'bot_update (without patch)', ['--patch_ref']),
      api.post_process(post_process.MustRun, 'compile (without patch)'),
      api.post_process(post_process.MustRun, 'isolate tests (without patch)'),
      api.post_process(post_process.MustRun, 'swarming trigger properties'),
      api.post_process(post_process.DoesNotRun, 'compile (with patch)'),
      api.post_process(post_process.DoesNotRun, 'isolate tests (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'check_static_initializers (with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_compile_no_isolate',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      override_test_spec(),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'fake-tester\' on group \'fake-group\'',
          'builder \'fake-builder\' on group \'fake-group\''
      ]),
      api.post_process(post_process.DoesNotRun, 'compile (with patch)'),
      api.post_process(post_process.DoesNotRun, 'isolate tests (with patch)'),
      api.post_process(post_process.DoesNotRun, 'swarming trigger properties'),
      api.post_process(post_process.DoesNotRun, 'archive src-side dep paths'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'compile_failed',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      override_test_spec(),
      api.filter.suppress_analyze(),
      api.override_step_data('compile (with patch)', retcode=1),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'fake-tester\' on group \'fake-group\'',
          'builder \'fake-builder\' on group \'fake-group\''
      ]),
      api.post_process(post_process.DoesNotRun, 'isolate tests (with patch)'),
      api.post_process(post_process.DoesNotRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failing_local_test',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      override_test_spec(),
      api.filter.suppress_analyze(),
      api.override_step_data('check_static_initializers (with patch)',
                             api.test_utils.canned_gtest_output(False)),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'fake-tester\' on group \'fake-group\'',
          'builder \'fake-builder\' on group \'fake-group\''
      ]),
      api.post_process(post_process.MustRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  def _generate_test_result(test_id,
                            test_variant,
                            status=test_result_pb2.PASS,
                            tags=None):
    vh = 'variant_hash'
    tr = test_result_pb2.TestResult(
        test_id=test_id,
        variant=test_variant,
        variant_hash=vh,
        expected=False,
        status=status,
    )
    if tags:
      all_tags = getattr(tr, 'tags')
      all_tags.append(tags)
    return tr

  correct_variant = resultdb_common.Variant()
  variant_def = getattr(correct_variant, 'def')
  variant_def['os'] = 'Ubuntu-18'
  variant_def['test_suite'] = ('check_static_initializers')

  tags = resultdb_common.StringPair(key='test_name', value='Test:Test1')

  test_id = ('ninja://check_static_initializers/Test:Test1')
  inv = 'invocations/build:8945511751514863184'
  current_patchset_invocations = {
      inv:
          api.resultdb.Invocation(test_results=[
              _generate_test_result(test_id, correct_variant, tags=tags)
          ])
  }

  recent_run = resultdb_pb2.GetTestResultHistoryResponse(entries=[])

  yield api.test(
      'basic_flakiness',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      override_test_spec(),
      # This additional analyze step is run by the flakiness module to ensure
      # that there's a test file change associated with the patch.
      api.step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.resultdb.query(
          current_patchset_invocations,
          ('check_static_initializers results'),
      ),
      api.flakiness(check_for_flakiness=True,),
      api.resultdb.get_test_result_history(
          recent_run,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.post_process(post_process.MustRun, 'searching_for_new_tests'),
      api.post_process(post_process.MustRun, 'test new tests for flakiness'),
      api.post_process(post_process.MustRun, 'calculate flake rates'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'flaky_test_failure',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
          revision='deadbeef',
      ),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      ctbc_properties(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      override_test_spec(),
      # This additional analyze step is run by the flakiness module to ensure
      # that there's a test file change associated with the patch.
      api.step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.resultdb.query(
          current_patchset_invocations,
          ('check_static_initializers results'),
      ),
      api.flakiness(check_for_flakiness=True,),
      api.resultdb.get_test_result_history(
          recent_run,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.override_step_data(
          'test new tests for flakiness.check_static_initializers results',
          stdout=api.json.invalid(
              api.test_utils.rdb_results(
                  'check_static_initializers',
                  flaky_tests=['Test.One'],
              ))),
      api.post_process(post_process.ResultReasonRE,
                       '.*check_static_initializers.*'),
      api.post_process(post_process.MustRun, 'calculate flake rates'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
