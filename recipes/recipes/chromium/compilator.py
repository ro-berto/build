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

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'filter',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_utils',
]

PROPERTIES = InputProperties


def RunSteps(api, properties):
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
          orch_builder_id, orch_builder_config, test_suites, bot_update_step,
          'without patch')
    else:
      raw_result, task = api.chromium_tests.build_affected_targets(
          orch_builder_id,
          orch_builder_config,
          isolate_output_files_for_coverage=True)
      test_suites = task.test_suites

    if raw_result and raw_result.status != common_pb.SUCCESS:
      return raw_result

    # Isolate the tests first so the Orchestrator can trigger them asap
    if any(t.uses_isolate for t in test_suites):
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

    return raw_result


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
        'chromium.linux', {
            'Linux Builder': {
                'scripts': [{
                    "isolate_profile_data": True,
                    "name": "check_static_initializers",
                    "script": "check_static_initializers.py",
                    "swarming": {}
                }],
            },
            'Linux Tests': {
                'gtest_tests': [{
                    'name': 'browser_tests',
                    'swarming': {
                        'can_use_on_swarming_builders': True
                    },
                }],
            },
        })

  yield api.test(
      'basic',
      api.chromium.try_build(
          builder='linux-rel-compilator', revision='deadbeef'),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      api.filter.suppress_analyze(),
      override_test_spec(),
      api.post_process(post_process.StepTextContains, 'report builders', [
          "running tester 'Linux Tests' on group 'chromium.linux' against "
          "builder 'Linux Builder' on group 'chromium.linux'"
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
      api.chromium.try_build(builder='linux-rel-compilator'),
      api.platform.name('linux'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_root_solution_revision',
      api.chromium.try_build(builder='linux-rel-compilator'),
      api.platform.name('linux'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'),
              deps_revision_overrides={'src/v8': 'v8deadbeef'})),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'deps_revision_overrides_and_root_solution_revision',
      api.chromium.try_build(
          builder='linux-rel-compilator',
          git_repo='https://chromium.googlesource.com/v8/v8'),
      api.platform.name('linux'),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'),
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
          builder='linux-rel-compilator', revision='deadbeef'),
      api.chromium_tests_builder_config.try_db(_TEST_TRYBOTS),
      api.chromium_tests_builder_config.builder_db(_TEST_BUILDERS),
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
          builder='linux-rel-compilator', revision='deadbeef'),
      api.chromium_tests_builder_config.try_db(_TEST_TRYBOTS),
      api.chromium_tests_builder_config.builder_db(_TEST_BUILDERS),
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
      'without_patch',
      api.chromium.try_build(
          builder='linux-rel-compilator', revision='deadbeef'),
      api.platform.name('linux'),
      api.code_coverage(use_clang_coverage=True),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'),
              swarming_targets=['browser_tests'])),
      override_test_spec(),
      api.post_process(post_process.StepTextContains, 'report builders', [
          "running tester 'Linux Tests' on group 'chromium.linux' against "
          "builder 'Linux Builder' on group 'chromium.linux'"
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
          builder='linux-rel-compilator', revision='deadbeef'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      override_test_spec(),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'Linux Tests\' on group \'chromium.linux\'',
          'builder \'Linux Builder\' on group \'chromium.linux\''
      ]),
      api.post_process(post_process.DoesNotRun, 'compile (with patch)'),
      api.post_process(post_process.DoesNotRun, 'isolate tests (with patch)'),
      api.post_process(post_process.DoesNotRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'compile_failed',
      api.chromium.try_build(
          builder='linux-rel-compilator', revision='deadbeef'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      override_test_spec(),
      api.filter.suppress_analyze(),
      api.override_step_data('compile (with patch)', retcode=1),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'Linux Tests\' on group \'chromium.linux\'',
          'builder \'Linux Builder\' on group \'chromium.linux\''
      ]),
      api.post_process(post_process.DoesNotRun, 'isolate tests (with patch)'),
      api.post_process(post_process.DoesNotRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failing_local_test',
      api.chromium.try_build(
          builder='linux-rel-compilator', revision='deadbeef'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      override_test_spec(),
      api.filter.suppress_analyze(),
      api.override_step_data('check_static_initializers (with patch)',
                             api.test_utils.canned_gtest_output(False)),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'Linux Tests\' on group \'chromium.linux\'',
          'builder \'Linux Builder\' on group \'chromium.linux\''
      ]),
      api.post_process(post_process.MustRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
