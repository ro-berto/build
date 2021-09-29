# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process, recipe_api

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.go.chromium.org.luci.swarming.proto.api import swarming as swarming_pb
from PB.recipe_modules.recipe_engine.led import properties as led_properties_pb

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/properties',
]

PROPERTIES = {
    'commit': recipe_api.Property(default=None),
}


def RunSteps(api, commit):
  builder_id = api.chromium.get_builder_id()
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  api.chromium_tests.configure_build(builder_config)
  update_step, _ = api.chromium_tests.prepare_checkout(
      builder_config, set_output_commit=True)
  if commit is not None:
    commit = common_pb.GitilesCommit(**commit)
  api.chromium_tests.trigger_child_builds(
      builder_id, update_step, builder_config, commit=commit)


def GenTests(api):

  # Check the status before applying the filter so that the $result step
  # doesn't need to be retained
  def filter_to_trigger():
    return api.post_process(post_process.Filter().include_re('^trigger.*'))

  def builder_with_tester_to_trigger(**kwargs):
    return api.chromium_tests_builder_config.ci_build(
        builder_group='fake-group',
        builder='fake-builder',
        builder_db=ctbc.BuilderDatabase.create({
            'fake-group': {
                'fake-builder':
                    ctbc.BuilderSpec.create(
                        chromium_config='chromium',
                        gclient_config='chromium',
                    ),
                'fake-tester':
                    ctbc.BuilderSpec.create(
                        execution_mode=ctbc.TEST,
                        chromium_config='chromium',
                        gclient_config='chromium',
                        parent_buildername='fake-builder',
                    )
            }
        }),
        **kwargs)

  yield api.test(
      'scheduler',
      builder_with_tester_to_trigger(),
      api.post_check(post_process.StatusSuccess),
      filter_to_trigger(),
  )

  yield api.test(
      'scheduler-use_gitiles_trigger-experiment',
      builder_with_tester_to_trigger(experiments={
          'chromium.chromium_tests.use_gitiles_trigger': 100,
      }),
      api.post_check(post_process.StatusSuccess),
      filter_to_trigger(),
  )

  yield api.test(
      'scheduler-commit-provided-not-in-use_gitiles_trigger-experiment',
      builder_with_tester_to_trigger(),
      api.properties(
          commit=common_pb.GitilesCommit(
              host='fake-host',
              project='fake-project',
              ref='fake-ref',
              id='fake-revision',
          )),
      api.post_check(post_process.StatusSuccess),
      filter_to_trigger(),
  )

  yield api.test(
      'led',
      builder_with_tester_to_trigger(),
      api.properties(
          **{
              '$recipe_engine/led':
                  led_properties_pb.InputProperties(
                      led_run_id='fake-run-id',
                      rbe_cas_input=swarming_pb.CASReference(
                          cas_instance=(
                              'projects/example/instances/default_instance'),
                          digest=swarming_pb.Digest(
                              hash='examplehash',
                              size_bytes=71,
                          ),
                      ),
                  ),
          }),
      api.post_check(post_process.StatusSuccess),
      filter_to_trigger(),
  )
