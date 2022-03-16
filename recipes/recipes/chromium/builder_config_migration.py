# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe providing src-side builder config migration functionality.

This recipe is not used on any builder, it is used as part of a PRESUBMIT check
to prevent additional configs from being added to the recipe.
"""
# TODO(crbug.com/868153) Remove this once the builder config migration is
# complete

import collections
import re

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build import proto_validation
from RECIPE_MODULES.build.chromium import BuilderId

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb
from PB.recipes.build.chromium import (builder_config_migration as
                                       builder_config_migration_pb)

PYTHON_VERSION_COMPATIBILITY = 'PY3'

PROPERTIES = builder_config_migration_pb.InputProperties

DEPS = [
    'chromium_tests_builder_config',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api, properties):
  errors = VALIDATORS.validate(properties)
  if errors:
    summary = ['The following errors were found with the input properties:', '']
    summary.extend(errors)
    return result_pb.RawResult(
        status=common_pb.INFRA_FAILURE, summary_markdown='\n'.join(summary))

  if properties.groupings_operation:

    builder_group_filters = []
    for f in reversed(properties.groupings_operation.builder_group_filters):
      regex = re.compile('^{}$'.format(f.builder_group_regex))
      include = not f.exclude
      builder_group_filters.append((regex, include))

    def builder_filter(builder_id):
      builder_group = builder_id.group
      for regex, include in builder_group_filters:
        if regex.match(builder_group):
          return include
      return False

    groupings_by_builder_id = _compute_groupings(api, builder_filter)

    output_path = api.path.abspath(properties.groupings_operation.output_path)

    json = {}
    for b, grouping in groupings_by_builder_id.items():
      json[str(b)] = [str(b2) for b2 in sorted(grouping)]
    output = api.json.dumps(json, indent=2, separators=(',', ': '))

    # Include log during the tests so that the expectation file is easier to
    # review
    api.file.write_text(
        'groupings', output_path, output, include_log=api._test_data.enabled)

    return


VALIDATORS = proto_validation.Registry()


@VALIDATORS.register(builder_config_migration_pb.InputProperties)
def _validate_properties(message, ctx):
  operation = message.WhichOneof('operation')
  if operation:
    ctx.validate_field(message, operation)
  else:
    ctx.error('no operation is set')


@VALIDATORS.register(builder_config_migration_pb.GroupingsOperation)
def _validate_groupings_operation(message, ctx):
  ctx.validate_field(message, 'output_path')
  ctx.validate_repeated_field(message, 'builder_group_filters')


@VALIDATORS.register(
    builder_config_migration_pb.GroupingsOperation.BuilderGroupFilter)
def _validate_builder_group_filter(message, ctx):
  ctx.validate_field(message, 'builder_group_regex')


def _compute_groupings(api, builder_filter):

  groupings_by_builder_id = collections.defaultdict(set)

  def check_included(related_ids, step_name):
    included_by_builder_id = {}
    for related_id in related_ids:
      included_by_builder_id[related_id] = builder_filter(related_id)

    included = set(included_by_builder_id.values())
    if len(included) == 1:
      return next(iter(included))

    api.step.empty(
        step_name,
        status=api.step.INFRA_FAILURE,
        log_name='mismatched_inclusion',
        log_text=[
            '{} ignored: {}'.format(builder_id, included)
            for builder_id, included in included_by_builder_id.items()
        ])

  def update_groupings(builder_id, related_ids):
    grouping = groupings_by_builder_id[builder_id]
    grouping.add(builder_id)
    for related_id in related_ids:
      related_grouping = groupings_by_builder_id[related_id]
      related_grouping.add(related_id)
      grouping.update(related_grouping)
      for connected_id in related_grouping:
        groupings_by_builder_id[connected_id] = grouping

  builder_db = api.chromium_tests_builder_config.builder_db
  for builder_id, child_ids in builder_db.builder_graph.items():
    included = check_included([builder_id] + sorted(child_ids),
                              'invalid children for {}'.format(builder_id))
    if included:
      update_groupings(builder_id, child_ids)

  try_db = api.chromium_tests_builder_config.try_db
  for try_id, try_spec in try_db.items():
    mirrored_ids = []
    for mirror in try_spec.mirrors:
      mirrored_ids.append(mirror.builder_id)
      if mirror.tester_id:
        mirrored_ids.append(mirror.tester_id)
    included = check_included(
        mirrored_ids, 'invalid mirroring configuration for {}'.format(try_id))
    if included:
      update_groupings(try_id, mirrored_ids)

  return groupings_by_builder_id


def GenTests(api):
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
              'migration': {
                  'foo-builder': ctbc.BuilderSpec.create(),
              },
              'migration.excluded': {
                  'bar-builder': ctbc.BuilderSpec.create(),
              },
          }),
          ctbc.TryDatabase.create({
              'tryserver.migration': {
                  'try-builder':
                      ctbc.TrySpec.create([
                          BuilderId.create_for_group('migration',
                                                     'foo-builder'),
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

  def invalid_properties(*errors):
    test_data = api.post_check(post_process.StatusException)
    test_data += api.post_check(
        post_process.ResultReasonRE,
        '^The following errors were found with the input properties')
    for error in errors:
      test_data += api.post_check(post_process.ResultReasonRE, error)
    test_data += api.post_process(post_process.DropExpectation)
    return test_data

  yield api.test(
      'no-operation',
      invalid_properties('no operation is set'),
  )

  yield api.test(
      'bad-groupings-operation',
      api.properties(groupings_operation={}),
      invalid_properties(
          r'groupings_operation\.output_path is not set',
          r'groupings_operation\.builder_group_filters is empty'),
  )

  yield api.test(
      'bad-builder-group-filter',
      api.properties(groupings_operation={
          'builder_group_filters': [{}],
      }),
      invalid_properties((r'groupings_operation\.builder_group_filters\[0\]'
                          r'\.builder_group_regex is not set')),
  )
