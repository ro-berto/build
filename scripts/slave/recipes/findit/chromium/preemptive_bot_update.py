# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Checkout the chromium src tree at the latest revision.

This recipe is meant to be run on idle bots to keep their local checkouts up to
date as much as possible so that when they are required to run culprit-finding
jobs they have as low latency as possible in their bot_update steps."""

from datetime import datetime

DEPS = [
    'chromium_checkout',
    'chromium_tests',
    'depot_tools/gclient',
    'depot_tools/git',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/time',
]

# Which master/builder config to use for the bot_update step based on the
# current master/builder.
TARGET_MAPPING = {
    'tryserver.chromium.linux': {
        'linux_chromium_variable': [
            'chromium.linux', 'Linux Builder'
        ],
        'linux_chromiumos_full_variable': [
            'chromium.linux', 'Linux Builder'
        ],
        'linux_chromium_chromeos_asan_variable': [
            'chromium.linux', 'Linux Builder'
        ],
    },
    'tryserver.chromium.win': {
        'win_chromium_variable': [
            'chromium.win', 'Win Builder'
        ],
    },
    'tryserver.chromium.mac': {
        'mac_chromium_variable_10.10': [
            'chromium.mac', 'Mac Builder'
        ],
        'mac_chromium_variable_10.11': [
            'chromium.mac', 'Mac Builder'
        ],
        'mac_chromium_variable': [
            'chromium.mac', 'Mac Builder'
        ],
    },
}

# Refresh the checkout if it's older than this.
NOT_FRESH = 600  # seconds


def TargetMasterAndBuilder(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  return TARGET_MAPPING[mastername][buildername]


def RunSteps(api):
  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(*TargetMasterAndBuilder(api))])
  api.chromium_tests.configure_build(
      bot_config, override_bot_type='builder_tester')

  base_dir = api.chromium_checkout.get_checkout_dir(bot_config)
  checkout_dir = base_dir.join(api.gclient.c.solutions[0].name)

  refresh_checkout = True
  if api.path.exists(checkout_dir):
    # Most recent commit in local checkout
    with api.context(cwd=checkout_dir):
      step_result = api.git(
          'log', '-1', '--pretty=format:%ct', 'refs/remotes/origin/master',
          stdout=api.raw_io.output_text(),
          step_test_data=lambda: api.raw_io.test_api.stream_output(
              '1333700000'))
    last_commit_ts = float(step_result.stdout)
    checkout_age_seconds = api.time.time() - last_commit_ts
    step_result.presentation.logs[
        'Checkout is ~%f seconds old' % checkout_age_seconds] = []
    refresh_checkout = checkout_age_seconds > NOT_FRESH
  if refresh_checkout:
    api.chromium_tests.prepare_checkout(bot_config)


def GenTests(api):
  yield (
      api.test('linux') +
      api.path.exists(api.path['start_dir'].join('src')) +
      api.properties(**{
          'mastername': 'tryserver.chromium.linux',
          'buildername': 'linux_chromium_variable',
          'bot_id': 'build1-a1',
          'buildnumber': '1',
      })
  )
  yield (
      api.test('win') +
      api.path.exists(api.path['start_dir'].join('src')) +
      api.properties(**{
          'mastername': 'tryserver.chromium.win',
          'buildername': 'win_chromium_variable',
          'bot_id': 'build1-a1',
          'buildnumber': '1',
      })
  )
  yield (
      api.test('mac') +
      api.path.exists(api.path['start_dir'].join('src')) +
      api.properties(**{
          'mastername': 'tryserver.chromium.mac',
          'buildername': 'mac_chromium_variable',
          'bot_id': 'build1-a1',
          'buildnumber': '1',
      })
  )
  yield (
      api.test('linux_new') +
      api.properties(**{
          'mastername': 'tryserver.chromium.linux',
          'buildername': 'linux_chromium_variable',
          'bot_id': 'build1-a1',
          'buildnumber': '1',
      })
  )
