# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
]


def RunSteps(api):
  builder_name = api.buildbucket.builder_name
  bot_config = api.chromium_tests.create_bot_config_object([
      api.chromium_tests.create_bot_id(api.properties['mastername'],
                                       builder_name)
  ])
  api.chromium_tests.configure_build(bot_config)
  update_step, build_config = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.archive_build(api.properties['mastername'], builder_name,
                                   update_step, build_config)


def GenTests(api):
  yield api.test(
      'cf_archive_build',
      api.chromium.ci_build(mastername='chromium.lkgr', builder='ASAN Release'),
  )

  yield api.test(
      'archive_build',
      api.chromium.ci_build(mastername='chromium', builder='linux-archive-rel'),
  )
