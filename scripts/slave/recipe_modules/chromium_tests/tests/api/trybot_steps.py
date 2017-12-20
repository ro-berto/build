# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium_tests',
    'filter',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]


def RunSteps(api):
  api.chromium_tests.trybot_steps()
  assert api.chromium_tests.is_precommit_mode()


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data(
          'read test spec (chromium.linux.json)',
          api.json.output({
              'Linux Tests': {
                  'gtest_tests': ['base_unittests'],
              },
          })
      ) +
      api.filter.suppress_analyze()
  )

  yield (
      api.test('analyze_compile_mode') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_clobber_rel_ng')
  )

  yield (
      api.test('analyze_names') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='fuchsia_x64') +
      api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
            'base': {'exclusions': []},
            'chromium': {'exclusions': []},
            'fuchsia': {'exclusions': ['path/to/fuchsia/exclusion.py']},
          })) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('path/to/fuchsia/exclusion.py')) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('no_compile') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng')
  )

  yield (
      api.test('no_compile_no_source') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('OWNERS')
      )
  )

  # Check the 5% experiment for exparchive only runs on 5% of builds. It uses
  # the buildnumber to determine when to be enabled. When enabled you get
  # individual isolate steps for each test, when disabled you get a single
  # isolate step for all tests.
  yield (
    api.test('exparchive_5percent_experiment_enabled') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='linux_chromium_rel_ng',
        buildnumber=1020, # 5% is (x % 100/5 == 0)
        swarm_hashes = {
          'base_unittests':
          '[dummy hash for base_unittests]'}) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': [
                    {
                        'test': 'base_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                        }
                    }
                ],
            },
        })
    ) +
    api.filter.suppress_analyze() +
    api.post_process(
        post_process.MustRun, 'isolate tests') +
    api.post_process(post_process.DropExpectation)
  )
  for i in range(1, 20):
    yield (
      api.test('exparchive_5percent_experiment_disabled_%i' % i) +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          buildnumber=1020 + i,
          swarm_hashes = {
            'base_unittests':
            '[dummy hash for base_unittests]'}) +
      api.override_step_data(
          'read test spec (chromium.linux.json)',
          api.json.output({
              'Linux Tests': {
                  'gtest_tests': [
                      {
                          'test': 'base_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          }
                      }
                  ],
              },
          })
      ) +
      api.filter.suppress_analyze() +
      api.post_process(
          post_process.MustRun, 'isolate tests') +
      api.post_process(
          post_process.DoesNotRun, 'isolate base_unittests') +
      api.post_process(post_process.DropExpectation)
    )
