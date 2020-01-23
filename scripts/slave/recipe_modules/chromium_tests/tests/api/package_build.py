# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine import recipe_api

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
]


PROPERTIES = {
    'builders': recipe_api.Property(kind=dict),
}


def RunSteps(api, builders):
  builder_name = api.buildbucket.builder_name
  bot_id = api.chromium_tests.create_bot_id(api.properties['mastername'],
                                            builder_name)
  bot_config = api.chromium_tests.create_bot_config_object([bot_id],
                                                           builders=builders)
  api.chromium_tests.configure_build(bot_config)
  update_step, build_config = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.package_build(
      api.properties['mastername'],
      builder_name,
      update_step,
      build_config,
      reasons=['for test coverage'])


def GenTests(api):
  yield api.test(
      'standard',
      api.chromium.ci_build(mastername='chromium.fake', builder='fake-builder'),
      api.properties(
          builders={
              'chromium.fake': {
                  'settings': {
                      'build_gs_bucket': 'sample-bucket',
                  },
                  'builders': {
                      'fake-builder': {
                          'bot_type': 'builder',
                          'chromium_config': 'chromium',
                          'enable_package_transfer': True,
                          'gclient_config': 'chromium',
                      },
                  },
              }
          }),
      api.post_process(post_process.DoesNotRun, 'package build for bisect'),
      api.post_process(post_process.MustRun, 'package build'),
      api.post_process(
          post_process.StepCommandContains, 'package build',
          ['--build-url', 'gs://sample-bucket/chromium.fake/fake-builder']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'perf-upload',
      api.chromium.ci_build(
          mastername='chromium.perf', builder='fake-perf-builder'),
      api.properties(
          builders={
              'chromium.perf': {
                  'settings': {
                      'build_gs_bucket': 'sample-bucket',
                  },
                  'builders': {
                      'fake-perf-builder': {
                          'bot_type': 'builder',
                          'chromium_config': 'chromium',
                          'enable_package_transfer': True,
                          'gclient_config': 'chromium',
                      },
                  },
              }
          }),
      api.post_process(post_process.DoesNotRun, 'package build for bisect'),
      api.post_process(post_process.MustRun, 'package build'),
      api.post_process(post_process.StepCommandContains, 'package build',
                       ['--build-url', 'gs://sample-bucket/fake-perf-builder']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bisect',
      api.chromium.ci_build(
          mastername='chromium.perf', builder='fake-bisect-builder'),
      api.properties(
          builders={
              'chromium.perf': {
                  'settings': {
                      'bisect_build_gs_bucket': 'sample-bisect-bucket',
                      'bisect_builders': ['fake-bisect-builder',],
                  },
                  'builders': {
                      'fake-bisect-builder': {
                          'bot_type': 'builder',
                          'chromium_config': 'chromium',
                          'enable_package_transfer': True,
                          'gclient_config': 'chromium',
                      },
                  },
              }
          }),
      api.post_process(post_process.MustRun, 'package build for bisect'),
      api.post_process(post_process.DoesNotRun, 'package build'),
      api.post_process(
          post_process.StepCommandContains, 'package build for bisect',
          ['--build-url', 'gs://sample-bisect-bucket/fake-bisect-builder']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
