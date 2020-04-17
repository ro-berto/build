# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

from recipe_engine import post_process


def RunSteps(api):
  bot = api.chromium_tests.lookup_bot_metadata(builders=None)
  api.chromium_tests.configure_build(bot.settings)
  api.chromium_tests.prepare_checkout(
      bot.settings, timeout=3600, no_fetch_tags=True)

  debug_lines = [
      '%s : %s' % (k, v) for (k, v) in api.properties.thaw().iteritems()
  ]
  api.python.succeeding_step('debug_lines', '<br/>'.join(debug_lines))


def GenTests(api):
  yield (api.test(
      'recipe-coverage',
      api.chromium_tests.platform([{
          'mastername': 'chromium.perf',
          'buildername': 'linux-perf'
      }]),
      api.chromium.ci_build(
          mastername='chromium.perf',
          builder='linux-perf',
          parent_buildername='linux-builder-perf')) + api.post_process(
              post_process.StatusSuccess) + api.post_process(
                  post_process.DropExpectation))
