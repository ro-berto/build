# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'clang_coverage',
    'recipe_engine/properties',
]


def RunSteps(api):
  for i in range(3):
    step = 'step %d' % i
    api.clang_coverage.profdata_dir(step)
    api.clang_coverage.shard_merge(step)
  api.clang_coverage.create_report()

  # Exercise these properties to provide coverage only.
  _ = api.clang_coverage.using_coverage
  _ = api.clang_coverage.raw_profile_merge_script


def GenTests(api):
  yield (
      api.test('basic')
      + api.properties(
          buildername='linux-code-coverage-generation',
          buildnumber=54)
      + api.post_process(
          post_process.MustRunRE, 'ensure profdata dir for .*', 3, 3)
      + api.post_process(
          post_process.MustRun, 'merge profile data for 3 targets')
      + api.post_process(
          post_process.MustRun, 'gsutil upload merged profile data')
      + api.post_process(post_process.StatusCodeIn, 0)
      + api.post_process(post_process.DropExpectation)
  )

