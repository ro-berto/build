# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.recipe_modules.build.chromium_orchestrator.properties import (
    InputProperties)
from PB.infra.chromium import chromium_bootstrap
from PB.go.chromium.org.luci.swarming.proto.api import swarming as swarming_pb
from RECIPE_MODULES.build.chromium_orchestrator.api import (
    COMPILATOR_SWARMING_TASK_COLLECT_STEP)
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'chromium',
    'chromium_bootstrap',
    'chromium_orchestrator',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'depot_tools/tryserver',
    'recipe_engine/file',
    'recipe_engine/led',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_utils',
]


def RunSteps(api):
  assert api.tryserver.is_tryserver

  return api.chromium_orchestrator.trybot_steps()


def GenTests(api):
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

  cas_digest_hash = (
      "20688f6c4da520c005b5c9faa1e9f2bc8cf21fef55b7e17e31cc5d4c346e7974")
  cas_digest_size = 71
  expected_cas_ref = '{}/{}'.format(
      cas_digest_hash,
      str(cas_digest_size),
  )

  def setup():
    return sum([
        api.chromium.try_build(
            builder_group='fake-try-group',
            builder='fake-orchestrator',
            experiments=[
                'remove_src_checkout_experiment', 'other_experiment_name'
            ],
        ),
        ctbc_properties(),
        api.chromium_bootstrap.properties(
            exe=chromium_bootstrap.BootstrappedExe(
                cas=swarming_pb.CASReference(
                    cas_instance=(
                        'projects/chromium-swarm/instances/default_instance'),
                    digest=swarming_pb.Digest(
                        hash=cas_digest_hash,
                        size_bytes=cas_digest_size,
                    ),
                ),
                cmd='luciexe',
            )),
        api.code_coverage(use_clang_coverage=True),
        api.properties(
            **{
                '$build/chromium_orchestrator':
                    InputProperties(
                        compilator='fake-compilator',
                        compilator_watcher_git_revision='e841fc',
                    ),
                '$recipe_engine/led': {
                    'led_run_id':
                        'chromium/led/kimstephanie_google.com/88a27cab21a8ad2',
                },
            }),
    ], api.empty_test_data())

  yield api.test(
      'trigger_led_compilator',
      setup(),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_led_get_builder(),
      api.step_data(
          'read build.proto.json (with patch)',
          api.file.read_json(json_content=api.chromium_orchestrator
                             .get_read_build_proto_json())),
      api.post_process(post_process.MustRun,
                       'trigger led compilator build (with patch)'),
      api.post_process(
          post_process.StepCommandContains,
          'trigger led compilator build (with patch).led edit-payload',
          ['-cas-ref', expected_cas_ref],
      ),
      # TODO (crbug/1263282): Check `led launch` step log once led/api is
      # updated to output the proto for the `led launch` step
      api.post_process(
          post_process.LogDoesNotContain,
          'trigger led compilator build (with patch).led edit-payload',
          'proto.output',
          ['other_experiment_name'],
      ),
      api.post_process(
          post_process.StepCommandContains,
          'trigger led compilator build (with patch).led edit (3)',
          ['remove_src_checkout_experiment=true'],
      ),
      api.post_process(post_process.MustRun,
                       'collect led compilator build (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.DoesNotRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.MustRun, 'download src-side deps'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'trigger_without_patch_led_compilator',
      setup(),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_led_get_builder(),
      api.step_data(
          'read build.proto.json (with patch)',
          api.file.read_json(json_content=api.chromium_orchestrator
                             .get_read_build_proto_json())),
      api.step_data(
          'read build.proto.json (without patch)',
          api.file.read_json(
              json_content=api.chromium_orchestrator.get_read_build_proto_json(
                  with_patch=False))),
      api.chromium_orchestrator.override_led_get_builder(),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'without patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'trigger led compilator build (with patch)'),
      api.post_process(
          post_process.StepCommandContains,
          'trigger led compilator build (with patch).led edit-payload',
          ['-cas-ref', expected_cas_ref],
      ),
      api.post_process(post_process.MustRun,
                       'collect led compilator build (with patch)'),
      api.post_process(post_process.MustRun,
                       'trigger led compilator build (without patch)'),
      api.post_process(
          post_process.StepCommandContains,
          'trigger led compilator build (without patch).led edit-payload',
          ['-cas-ref', expected_cas_ref],
      ),
      api.post_process(post_process.MustRun,
                       'collect led compilator build (without patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.DoesNotRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.MustRun, 'download src-side deps'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip_without_patch_local_tests_failed',
      setup(),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_led_get_builder(),
      api.step_data(
          'read build.proto.json (with patch)',
          api.file.read_json(
              json_content=api.chromium_orchestrator.get_read_build_proto_json(
                  affected_files=['src/testing/buildbot/fake-group.json'],
                  status=common_pb.FAILURE,
                  summary=("1 Test Suite(s) failed.\n\n"
                           "**headless_python_unittests** failed."),
              ))),
      api.post_process(post_process.MustRun,
                       'trigger led compilator build (with patch)'),
      api.post_process(
          post_process.StepCommandContains,
          'trigger led compilator build (with patch).led edit-payload',
          ['-cas-ref', expected_cas_ref],
      ),
      api.post_process(post_process.MustRun,
                       'collect led compilator build (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.MustRun, 'download src-side deps'),
      api.post_process(post_process.DoesNotRun,
                       'trigger led compilator build (without patch)'),
      api.post_process(post_process.DoesNotRun,
                       'collect led compilator build (without patch)'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'triggered_compilator_infra_failed',
      setup(),
      api.override_step_data(
          'collect led compilator build (with patch)',
          retcode=1,
      ),
      api.post_process(post_process.MustRun,
                       'trigger led compilator build (with patch)'),
      api.post_process(
          post_process.StepCommandContains,
          'trigger led compilator build (with patch).led edit-payload',
          ['-cas-ref', expected_cas_ref],
      ),
      api.post_process(post_process.DoesNotRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.DoesNotRun, 'download src-side deps'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )
