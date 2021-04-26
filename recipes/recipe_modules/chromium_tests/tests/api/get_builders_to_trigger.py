# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/assertions',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  api.chromium_tests.configure_build(builder_config)
  actual = api.chromium_tests._get_builders_to_trigger(builder_id,
                                                       builder_config)

  # Convert the mappings to comparable types
  actual = {k: sorted(v) for k, v in actual.iteritems()}
  expected = {k: sorted(v) for k, v in api.properties['expected'].iteritems()}

  api.assertions.assertEqual(actual, expected)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Builder',
      ),
      api.properties(expected={
          'chromium': ['Linux Tests'],
      }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'dedup',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          # Multiple entries for 'fake-tester' in different builder
          # groups, as would be the case when making a copy for changing
          # the builder group
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(luci_project='foo-project'),
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='fake-builder',
                      ),
              },
              'fake-group2': {
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_builder_group='fake-group',
                          parent_buildername='fake-builder',
                      ),
              },
          })),
      api.properties(expected={
          'chromium': ['fake-tester'],
      }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'luci-project-overridden-for-tester',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(),
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          luci_project='fake-project',
                          execution_mode=ctbc.TEST,
                          parent_buildername='fake-builder',
                      ),
              },
          })),
      api.properties(expected={
          'fake-project': ['fake-tester'],
      }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'same-project-trigger-override',
      api.chromium_tests_builder_config.ci_build(
          project='bar-project',
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(luci_project='foo-project'),
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='fake-builder',
                          luci_project='foo-project',
                      ),
              },
          })),
      api.properties(
          expected={
              'bar-project': ['fake-tester'],
          },
          **{
              '$build/chromium_tests': {
                  'project_trigger_overrides': {
                      'foo-project': 'bar-project',
                  },
              },
          }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
