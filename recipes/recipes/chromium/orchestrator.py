# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Triggers compilator and tests"""

from recipe_engine import post_process
from PB.recipes.build.chromium.orchestrator import InputProperties

DEPS = [
    'builder_group',
    'chromium',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
    'recipe_engine/step',
    'recipe_engine/swarming',
]

PROPERTIES = InputProperties


def RunSteps(api, properties):
  if not properties.compilator:
    raise api.step.InfraFailure('Missing compilator input')

  # Scheduled build inherits current build's project and bucket
  request = api.buildbucket.schedule_request(
      builder=properties.compilator,
      swarming_parent_run_id=api.swarming.task_id,
      properties={
          'orchestrator': {
              'builder_name': api.buildbucket.builder_name,
              'builder_group': api.builder_group.for_current
          }
      },
      tags=api.buildbucket.tags(**{'hide-in-gerrit': 'pointless'}))

  build = api.buildbucket.run([request], collect_interval=20, timeout=7200)[0]
  del build


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      api.post_process(post_process.MustRun, 'buildbucket.run'),
      api.post_process(post_process.MustRun, 'buildbucket.run.collect'),
      api.post_process(
          post_process.LogContains, 'buildbucket.run.schedule', 'request',
          ['orchestrator', 'tryserver.chromium.linux', 'linux-rel-compilator']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_builder_to_trigger_passed_in',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.post_process(post_process.DoesNotRun, 'buildbucket.run'),
      api.post_process(post_process.DoesNotRun, 'buildbucket.run.collect'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )
