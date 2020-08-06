# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/properties',
]

def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  bot_config = api.chromium_tests.create_bot_config_object([builder_id])
  api.chromium_tests.configure_build(bot_config)
  update_step, _ = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.download_and_unzip_build(
      builder_id, update_step, bot_config, **api.properties.get('kwargs', {}))


def GenTests(api):
  yield api.test(
      'read-gn-args',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Tests'),
      api.properties(
          parent_builder_group='chromium.linux',
          parent_buildername='Linux Builder',
          kwargs=dict(read_gn_args=True)),
      api.post_process(post_process.MustRun, 'read GN args'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'do-not-read-gn-args',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Tests'),
      api.properties(
          parent_builder_group='chromium.linux',
          parent_buildername='Linux Builder',
          kwargs=dict(read_gn_args=False)),
      api.post_process(post_process.DoesNotRun, 'read GN args'),
      api.post_process(post_process.DropExpectation),
  )
