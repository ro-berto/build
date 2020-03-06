# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  bot_config = api.chromium_tests.create_bot_config_object([builder_id])
  api.chromium_tests.configure_build(bot_config)
  update_step, _ = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.archive_build(builder_id, update_step, bot_config)


def GenTests(api):
  yield api.test(
      'cf_archive_build',
      api.chromium.ci_build(mastername='chromium.lkgr', builder='ASAN Release'),
  )

  yield api.test(
      'archive_build',
      api.chromium.ci_build(mastername='chromium', builder='linux-archive-rel'),
  )
