# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe for launching polymorphic builders.

The launcher enables creating a single polymorphic builder that can be
launched to perform operations on behalf of 1 or more target builders.
This prevents needing to create and maintain the configuration for
builders to mimic the standard builders when enabling alternate modes of
operation.
"""

from recipe_engine import post_process

from PB.go.chromium.org.luci.buildbucket.proto \
    import builder_common as builder_common_pb
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipes.build.chromium_polymorphic.launcher import InputProperties

PYTHON_VERSION_COMPATIBILITY = 'PY3'

PROPERTIES = InputProperties

DEPS = [
    'chromium_polymorphic',
    'recipe_engine/buildbucket',
    'recipe_engine/futures',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api, properties):
  futures = [
      api.futures.spawn(_trigger_runner, api, target_builder,
                        properties.runner_builder)
      for target_builder in properties.target_builders
  ]
  # Get the result of the futures so that if one of them failed, an exception
  # will be raised
  for f in api.futures.wait(futures):
    f.result()


def _trigger_runner(api, target_builder, runner_builder_id):
  b = target_builder.builder_id
  with api.step.nest(f'{b.project}/{b.bucket}/{b.builder}'):
    properties = api.chromium_polymorphic.get_target_properties(b)
    dimensions = [
        common_pb.RequestedDimension(key=k, value=v)
        for k, v in target_builder.dimensions.items()
    ]
    api.buildbucket.schedule([
        api.buildbucket.schedule_request(
            project=runner_builder_id.project,
            bucket=runner_builder_id.bucket,
            builder=runner_builder_id.builder,
            properties=properties,
            dimensions=dimensions,
            can_outlive_parent=True,
        ),
    ])


def GenTests(api):

  def properties_on_target_build(*, project, bucket, builder, properties):
    return api.chromium_polymorphic.properties_on_target_build(
        properties,
        step_name=f'{project}/{bucket}/{builder}.buildbucket.search')

  yield api.test(
      'basic',
      api.properties(
          InputProperties(
              runner_builder=builder_common_pb.BuilderID(
                  project='fake-project',
                  bucket='fake-bucket',
                  builder='fake-runner-builder',
              ),
              target_builders=[
                  InputProperties.TargetBuilder(
                      builder_id=builder_common_pb.BuilderID(
                          project='fake-project',
                          bucket='fake-target-bucket',
                          builder='fake-target-builder-foo',
                      ),
                      dimensions={
                          'foo-dim-1': 'foo-dim-value-1',
                          'foo-dim-2': 'foo-dim-value-2',
                      },
                  ),
                  InputProperties.TargetBuilder(
                      builder_id=builder_common_pb.BuilderID(
                          project='fake-project',
                          bucket='fake-target-bucket',
                          builder='fake-target-builder-bar',
                      ),
                      dimensions={
                          'bar-dim-1': 'bar-dim-value-1',
                          'bar-dim-2': 'bar-dim-value-2',
                      },
                  ),
              ],
          )),
      properties_on_target_build(
          project='fake-project',
          bucket='fake-target-bucket',
          builder='fake-target-builder-foo',
          properties={
              'builder_group': 'fake-foo-group',
              'foo-prop-1': 'foo-prop-value-1',
              'foo-prop-2': 'foo-prop-value-2',
          },
      ),
      properties_on_target_build(
          project='fake-project',
          bucket='fake-target-bucket',
          builder='fake-target-builder-bar',
          properties={
              'builder_group': 'fake-bar-group',
              'bar-prop-1': 'bar-prop-value-1',
              'bar-prop-2': 'bar-prop-value-2',
          },
      ),
      api.post_check(post_process.MustRun,
                     ('fake-project/fake-target-bucket/fake-target-builder-bar'
                      '.buildbucket.schedule')),
      api.post_check(post_process.MustRun,
                     ('fake-project/fake-target-bucket/fake-target-builder-foo'
                      '.buildbucket.schedule')),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
