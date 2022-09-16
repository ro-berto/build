# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import textwrap

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build.chromium import BuilderId

from PB.recipe_modules.build.chromium_tests_builder_config_migration import (
    properties as properties_pb)

DEPS = [
    'chromium_tests_builder_config',
    'chromium_tests_builder_config_migration',
    'recipe_engine/properties',
]

PROPERTIES = properties_pb.InputProperties


def RunSteps(api, properties):
  ctbc_api = api.chromium_tests_builder_config
  return api.chromium_tests_builder_config_migration(properties,
                                                     ctbc_api.builder_db,
                                                     ctbc_api.try_db)


def GenTests(api):
  expected_groupings = textwrap.dedent("""\
      {
        "migration.bar:bar-builder": {
          "builders": [
            "migration.bar:bar-builder",
            "migration.bar:bar-tests",
            "tryserver.migration.bar:bar-try-builder"
          ]
        },
        "migration.bar:bar-tests": {
          "builders": [
            "migration.bar:bar-builder",
            "migration.bar:bar-tests",
            "tryserver.migration.bar:bar-try-builder"
          ]
        },
        "migration.foo:foo-builder": {
          "builders": [
            "migration.foo:foo-builder",
            "migration.foo:foo-x-tests",
            "migration.foo:foo-y-tests",
            "tryserver.migration.foo:foo-try-builder"
          ]
        },
        "migration.foo:foo-x-tests": {
          "builders": [
            "migration.foo:foo-builder",
            "migration.foo:foo-x-tests",
            "migration.foo:foo-y-tests",
            "tryserver.migration.foo:foo-try-builder"
          ]
        },
        "migration.foo:foo-y-tests": {
          "builders": [
            "migration.foo:foo-builder",
            "migration.foo:foo-x-tests",
            "migration.foo:foo-y-tests",
            "tryserver.migration.foo:foo-try-builder"
          ]
        },
        "tryserver.migration.bar:bar-try-builder": {
          "builders": [
            "migration.bar:bar-builder",
            "migration.bar:bar-tests",
            "tryserver.migration.bar:bar-try-builder"
          ]
        },
        "tryserver.migration.foo:foo-try-builder": {
          "builders": [
            "migration.foo:foo-builder",
            "migration.foo:foo-x-tests",
            "migration.foo:foo-y-tests",
            "tryserver.migration.foo:foo-try-builder"
          ]
        }
      }""")

  yield api.test(
      'groupings',
      api.properties(
          groupings_operation={
              'output_path':
                  '/fake/output/path',
              'builder_group_filters': [
                  {
                      'builder_group_regex': r'(tryserver\.)?migration(\..+)?',
                  },
                  {
                      'builder_group_regex': r'migration\.excluded',
                      'exclude': True,
                  },
              ],
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'migration.foo': {
                  'foo-builder':
                      ctbc.BuilderSpec.create(),
                  'foo-x-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='foo-builder',
                      ),
                  'foo-y-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='foo-builder',
                      ),
              },
              'migration.bar': {
                  'bar-builder':
                      ctbc.BuilderSpec.create(),
                  'bar-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='bar-builder',
                      ),
              },
              'migration.excluded': {
                  'excluded-builder':
                      ctbc.BuilderSpec.create(),
                  'excluded-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='excluded-builder',
                      ),
              },
              'other': {
                  'other-builder': ctbc.BuilderSpec.create(),
              }
          }),
          ctbc.TryDatabase.create({
              'tryserver.migration.foo': {
                  'foo-try-builder':
                      ctbc.TrySpec.create([
                          ctbc.TryMirror.create(
                              builder_group='migration.foo',
                              buildername='foo-builder',
                              tester='foo-x-tests',
                          ),
                      ]),
              },
              'tryserver.migration.bar': {
                  'bar-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='migration.bar',
                          buildername='bar-builder',
                      ),
              },
          }),
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_check(lambda check, steps: \
          check(expected_groupings in steps['groupings'].cmd)),
      api.post_process(post_process.DropExpectation),
  )

  expected_non_existent_groupings = textwrap.dedent("""\
      {
        "non.existent:non-existent-builder": {
          "blockers": [
            "builder 'non.existent:non-existent-builder' does not exist"
          ],
          "builders": [
            "non.existent:non-existent-builder"
          ]
        }
      }""")

  yield api.test(
      'non-existent-builder',
      api.properties(
          groupings_operation={
              'output_path':
                  '/fake/output/path',
              'builder_group_filters': [
                  {
                      'builder_group_regex': r'non\.existent',
                  },
              ],
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'non.existent': {
                  'non-existent-builder': ctbc.BuilderSpec.create(),
              },
          }),
          ctbc.TryDatabase.create({}),
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_check(lambda check, steps: \
          check(expected_non_existent_groupings in steps['groupings'].cmd)),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'invalid-children',
      api.properties(
          groupings_operation={
              'output_path':
                  '/fake/output/path',
              'builder_group_filters': [
                  {
                      'builder_group_regex': r'(tryserver\.)?migration(\..+)?',
                  },
                  {
                      'builder_group_regex': r'migration\.excluded',
                      'exclude': True,
                  },
              ],
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'migration': {
                  'foo-builder': ctbc.BuilderSpec.create(),
              },
              'migration.excluded': {
                  'foo-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_builder_group='migration',
                          parent_buildername='foo-builder',
                      ),
              },
          }),
          ctbc.TryDatabase.create({}),
      ),
      api.post_check(post_process.MustRun,
                     'invalid children for migration:foo-builder'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'invalid-mirrors',
      api.properties(
          groupings_operation={
              'output_path':
                  '/fake/output/path',
              'builder_group_filters': [
                  {
                      'builder_group_regex': r'(tryserver\.)?migration(\..+)?',
                  },
                  {
                      'builder_group_regex': r'migration\.excluded',
                      'exclude': True,
                  },
              ],
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'migration.excluded': {
                  'bar-builder': ctbc.BuilderSpec.create(),
              },
          }),
          ctbc.TryDatabase.create({
              'tryserver.migration': {
                  'try-builder':
                      ctbc.TrySpec.create([
                          BuilderId.create_for_group('migration.excluded',
                                                     'bar-builder'),
                      ]),
              },
          })),
      api.post_check(
          post_process.MustRun,
          'invalid mirroring configuration for tryserver.migration:try-builder'
      ),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )
