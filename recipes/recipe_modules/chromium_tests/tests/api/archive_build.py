# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

DEPS = [
    'chromium',
    'chromium_tests',
]


def RunSteps(api):
  builder_id, bot_config = api.chromium_tests.lookup_builder()
  api.chromium_tests.configure_build(bot_config)
  update_step, _ = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.archive_build(builder_id, update_step, bot_config)


def GenTests(api):
  yield api.test(
      'cf_archive_build',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-group': {
                  'fake-builder':
                      bot_spec.BotSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          cf_archive_build=True,
                          cf_archive_name='cf_archive_build_test',
                          cf_gs_bucket='clusterfuzz-gs-bucket',
                          cf_gs_acl='public-read',
                      ),
              },
          })),
  )

  yield api.test(
      'archive_build',
      api.chromium.ci_build(
          builder_group='chromium', builder='linux-archive-rel'),
  )
