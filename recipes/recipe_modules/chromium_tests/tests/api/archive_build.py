# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/step',
]


def RunSteps(api):
  # Create a nested step so that setup steps can be easily filtered out
  with api.step.nest('setup steps'):
    builder_id, builder_config = (
        api.chromium_tests_builder_config.lookup_builder())
    api.chromium_tests.configure_build(builder_config)
    update_step, _ = api.chromium_tests.prepare_checkout(builder_config)
  api.chromium_tests.archive_build(builder_id, update_step, builder_config)


def GenTests(api):

  def filter_out_setup_steps():

    def step_filter(check, steps):
      del check
      return collections.OrderedDict([(k, v)
                                      for k, v in steps.iteritems()
                                      if not k.startswith('setup steps')])

    return api.post_process(step_filter)

  yield api.test(
      'cf_archive_build',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          cf_archive_build=True,
                          cf_archive_name='cf_archive_build_test',
                          cf_gs_bucket='clusterfuzz-gs-bucket',
                          cf_gs_acl='public-read',
                      ),
              },
          })),
      filter_out_setup_steps(),
  )

  yield api.test(
      'archive_build',
      api.chromium.ci_build(
          builder_group='chromium', builder='linux-archive-rel'),
      filter_out_setup_steps(),
  )
