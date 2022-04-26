# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import six

from recipe_engine import post_process, recipe_api

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.go.chromium.org.luci.swarming.proto.api import swarming as swarming_pb
from PB.recipe_modules.recipe_engine.led import properties as led_properties_pb

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/properties',
    'recipe_engine/step',
]

PROPERTIES = {
    'commit': recipe_api.Property(default=None),
    'set_output_commit': recipe_api.Property(default=True),
}


def RunSteps(api, commit, set_output_commit):
  # Create a nested step so that setup steps can be easily filtered out
  with api.step.nest('setup steps'):
    builder_id = api.chromium.get_builder_id()
    builder_id, builder_config = (
        api.chromium_tests_builder_config.lookup_builder())
    api.chromium_tests.configure_build(builder_config)
    update_step, _ = api.chromium_tests.prepare_checkout(
        builder_config, set_output_commit=set_output_commit)
    if commit is not None:
      commit = common_pb.GitilesCommit(**commit)

  api.chromium_tests.trigger_child_builds(
      builder_id, update_step, builder_config, commit=commit)


def GenTests(api):

  def filter_out_setup_steps():

    def step_filter(check, steps):
      del check
      return collections.OrderedDict([(k, v)
                                      for k, v in six.iteritems(steps)
                                      if not k.startswith('setup steps')])

    return api.post_process(step_filter)

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
      filter_out_setup_steps(),
  )

  yield api.test(
      'scheduler-with-no-commit',
      builder_with_tester_to_trigger(),
      api.properties(set_output_commit=False),
      api.post_check(post_process.MustRun, 'no commit for trigger'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'scheduler-with-commit-provided',
      builder_with_tester_to_trigger(),
      api.properties(
          commit=common_pb.GitilesCommit(
              host='fake-host',
              project='fake-project',
              ref='fake-ref',
              id='fake-revision',
          )),
      api.post_check(post_process.StatusSuccess),
      filter_out_setup_steps(),
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
      filter_out_setup_steps(),
  )
