# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium_tests',
    'clang_coverage',
    'recipe_engine/properties',
]


def RunSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  bot_config_object = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)],
      builders=None)
  api.chromium_tests.configure_build(bot_config_object)
  if 'tryserver' in mastername:
    api.clang_coverage.instrument([
        'some/path/to/file.cc',
        'some/other/path/to/file.cc',
    ])

  for i in range(3):
    step = 'step %d' % i
    api.clang_coverage.profdata_dir(step)
    api.clang_coverage.shard_merge(step)
  api.clang_coverage.process_coverage_data([
      api.chromium_tests.steps.SwarmingGTestTest('base_unittests')])

  # Exercise these properties to provide coverage only.
  _ = api.clang_coverage.using_coverage
  _ = api.clang_coverage.raw_profile_merge_script


def GenTests(api):
  yield (
      api.test('basic')
      + api.properties.generic(
          mastername='chromium.fyi',
          buildername='linux-code-coverage',
          buildnumber=54)
      + api.post_process(
          post_process.MustRunRE, 'ensure profdata dir for .*', 3, 3)
      + api.post_process(
          post_process.MustRun, 'merge profile data for 3 targets')
      + api.post_process(
          post_process.MustRun, 'generate html report for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload html report')
      + api.post_process(
          post_process.DoesNotRun, 'generate git diff locally')
      + api.post_process(
          post_process.MustRun, 'generate metadata for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload metadata')
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('tryserver')
      + api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='linux-coverage-rel',
          buildnumber=54)
      + api.post_process(
          post_process.MustRun, 'save paths of affected files')
      + api.post_process(
          post_process.MustRunRE, 'ensure profdata dir for .*', 3, 3)
      + api.post_process(
          post_process.MustRun, 'merge profile data for 3 targets')
      + api.post_process(
          post_process.MustRun, 'generate html report for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload html report')
      + api.post_process(
          post_process.MustRun, 'generate git diff locally')
      + api.post_process(
          post_process.MustRun, 'generate metadata for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload metadata')
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

