# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/python',
]


def RunSteps(api):
  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium.get_builder_id()])
  api.chromium_tests.configure_build(bot_config)
  api.python(
      'sample script',
      api.path['checkout'].join('testing', 'scripts', 'example.py'),
      api.chromium_tests.get_common_args_for_scripts(),
  )


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='chromium.perf',
          builder='linux-perf',
      ),
  )
