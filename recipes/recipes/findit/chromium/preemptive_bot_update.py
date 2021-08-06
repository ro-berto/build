# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Checkout the chromium src tree at the latest revision.

This recipe is meant to be run on idle bots to keep their local checkouts up to
date as much as possible so that when they are required to run culprit-finding
jobs they have as low latency as possible in their bot_update steps."""

from RECIPE_MODULES.build import chromium

DEPS = [
    'builder_group',
    'chromium_checkout',
    'chromium_tests',
    'chromium_tests_builder_config',
    'depot_tools/gclient',
    'depot_tools/git',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/time',
]

# Which group/builder config to use for the bot_update step based on the
# current group/builder.
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


def TargetGroupAndBuilder(api):
  builder_group = api.builder_group.for_current
  buildername = api.buildbucket.builder_name
  return TARGET_MAPPING[builder_group][buildername]


def RunSteps(api):
  builder_id = chromium.BuilderId.create_for_group(*TargetGroupAndBuilder(api))
  _, builder_config = (
      api.chromium_tests_builder_config.lookup_builder(
          builder_id, use_try_db=False))
  api.chromium_tests.configure_build(builder_config)

  base_dir = api.chromium_checkout.checkout_dir
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
    api.chromium_tests.prepare_checkout(
        builder_config, report_cache_state=False)


def GenTests(api):
  yield api.test(
      'linux',
      api.buildbucket.try_build(builder='linux_chromium_variable'),
      api.builder_group.for_current('tryserver.chromium.linux'),
      api.path.exists(
          # buildbot path
          api.path['start_dir'].join('src'),
          # LUCI path
          api.path['cache'].join('builder', 'src')),
      api.properties(**{
          'bot_id': 'build1-a1',
      }),
  )
  yield api.test(
      'win',
      api.buildbucket.try_build(builder='win_chromium_variable'),
      api.builder_group.for_current('tryserver.chromium.win'),
      api.path.exists(
          # buildbot path
          api.path['start_dir'].join('src'),
          # LUCI path
          api.path['cache'].join('builder', 'src')),
      api.properties(**{
          'bot_id': 'build1-a1',
      }),
  )
  yield api.test(
      'mac',
      api.buildbucket.try_build(builder='mac_chromium_variable'),
      api.builder_group.for_current('tryserver.chromium.mac'),
      api.path.exists(
          # buildbot path
          api.path['start_dir'].join('src'),
          # LUCI path
          api.path['cache'].join('builder', 'src')),
      api.properties(**{
          'bot_id': 'build1-a1',
      }),
  )
  yield api.test(
      'linux_new',
      api.buildbucket.try_build(builder='linux_chromium_variable'),
      api.builder_group.for_current('tryserver.chromium.linux'),
      api.properties(**{
          'bot_id': 'build1-a1',
      }),
  )
