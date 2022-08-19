# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/buildbucket',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
  # Create a nested step so that setup steps can be easily filtered out
  with api.step.nest('setup steps'):
    _, builder_config = api.chromium_tests_builder_config.lookup_builder()
    api.chromium_tests.configure_build(builder_config)
    update_step, _ = api.chromium_tests.prepare_checkout(builder_config)
  api.chromium_tests.deapply_patch(update_step)


def GenTests(api):

  def filter_out_setup_steps():

    def step_filter(check, steps):
      del check
      return collections.OrderedDict([
          (k, v) for k, v in steps.items() if not k.startswith('setup steps')
      ])

    return api.post_process(step_filter)

  ctbc_api = api.chromium_tests_builder_config

  yield api.test(
      'basic',
      api.platform('win', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      filter_out_setup_steps(),
  )
