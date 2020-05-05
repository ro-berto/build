# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import (steps, try_spec as
                                                 try_spec_module)

DEPS = [
    'chromium',
    'chromium_tests',
    'code_coverage',
    'pgo',
    'profiles',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  builder_id = chromium.BuilderId.create_for_master(
      api.properties['mastername'], api.properties['buildername'])
  try_spec = api.chromium_tests.trybots.get(builder_id)
  if try_spec is None:
    try_spec = try_spec_module.TrySpec.create(bot_ids=[builder_id])

  bot_config = api.chromium_tests.create_bot_config_object(try_spec.mirrors)
  api.chromium_tests.configure_build(bot_config)
  # Fake path.
  api.profiles._merge_scripts_dir = api.path['start_dir']

  if api.properties.get('mock_merged_profdata', True):
    api.path.mock_add_paths(
        api.profiles.profile_dir().join('pgo_final_aggregate.profdata'))

  tests = [steps.SwarmingIsolatedScriptTest('performance_test_suite')]

  for test in tests:
    step = test.name
    api.profiles.profile_dir(step)
    # Protected access ok here, as this is normally done by the test object
    # itself.
    api.code_coverage.shard_merge(
        step, test.target_name, additional_merge=getattr(test, '_merge', None))

  api.pgo.process_pgo_data()

  # coverage only
  _ = api.pgo.using_pgo


def GenTests(api):

  yield api.test(
      'merged profdata does not exist',
      api.properties.generic(
          mastername='chromium.perf',
          buildername='mac-builder-perf',
          buildnumber=54),
      api.pgo(use_pgo=True),
      api.platform('mac', 64),
      api.properties(mock_merged_profdata=False),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.No profdata was generated.'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic windows',
      api.properties.generic(
          mastername='chromium.perf',
          buildername='win64-builder-perf',
          buildnumber=54),
      api.pgo(use_pgo=True),
      api.platform('win', 64),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*'),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.gsutil upload artifact to GS'),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.Rename the profdata artifact'),
      api.post_process(post_process.MustRun,
                       'Processing PGO .profraw data.git show'),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.merge all profile files into a single'
          ' .profdata'),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.Finding profile merge errors'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(
          post_process.StepCommandContains,
          'Processing PGO .profraw data.gsutil upload artifact to GS', [
              'gs://chromium-optimization-profiles/pgo_profiles/'
              'chrome-win64-master-1587876258-'
              'ade24b3118b1feaa04cb4406253403f3f72a7f0e.profdata'
          ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'merge errors',
      api.properties.generic(
          mastername='chromium.perf',
          buildername='mac-builder-perf',
          buildnumber=54),
      api.pgo(use_pgo=True),
      api.platform('mac', 64),
      api.properties(mock_merged_profdata=True),
      api.override_step_data(
          'Processing PGO .profraw data.Finding profile merge errors',
          stdout=api.json.output({
              "failed profiles": {
                  "browser_tests": ["/tmp/1/default-123.profraw"]
              },
              "total": 1
          })),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.Failing due to merge errors found '
          'alongside invalid profile data.'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
