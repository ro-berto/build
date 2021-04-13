# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine import recipe_api

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id, bot_config = api.chromium_tests.lookup_builder()
  api.chromium_tests.configure_build(bot_config)
  update_step, _ = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.package_build(
      builder_id, update_step, bot_config, reasons=['for test coverage'])


def GenTests(api):
  yield api.test(
      'standard',
      api.chromium.ci_build(
          builder_group='chromium.fake', builder='fake-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'chromium.fake': {
                  'fake-builder':
                      bot_spec.BotSpec.create(
                          build_gs_bucket='sample-bucket',
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
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
          builder_group='chromium.perf', builder='fake-perf-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'chromium.perf': {
                  'fake-perf-builder':
                      bot_spec.BotSpec.create(
                          build_gs_bucket='sample-bucket',
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
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
          builder_group='chromium.perf', builder='fake-bisect-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'chromium.perf': {
                  'fake-bisect-builder':
                      bot_spec.BotSpec.create(
                          bisect_archive_build=True,
                          bisect_gs_bucket='sample-bisect-bucket',
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.post_process(post_process.MustRun, 'package build for bisect'),
      api.post_process(post_process.DoesNotRun, 'package build'),
      api.post_process(
          post_process.StepCommandContains, 'package build for bisect',
          ['--build-url', 'gs://sample-bisect-bucket/fake-bisect-builder']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
