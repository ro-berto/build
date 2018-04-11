# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter, DoesNotRun, DropExpectation
from recipe_engine.recipe_api import Property

DEPS = [
  'archive',
  'chromium',
  'depot_tools/gclient',
  'depot_tools/infra_paths',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'recipe_engine/url',
  'swarming_client',
  'recipe_engine/time',
  'depot_tools/tryserver',
  'v8',
]

PROPERTIES = {
  # Name of a gclient custom_var to set to 'True'.
  'set_gclient_var': Property(default=None, kind=str),
}

def RunSteps(api, set_gclient_var):
  v8 = api.v8
  v8.apply_bot_config(v8.BUILDERS)
  v8.set_gclient_custom_var(set_gclient_var)

  # Opt out of using gyp environment variables.
  api.chromium.c.use_gyp_env = False

  additional_trigger_properties = {}
  test_spec = {}
  tests = v8.create_tests()
  tests += v8.extra_tests_from_properties()

  if v8.is_pure_swarming_tester(tests):
    api.swarming_client.checkout()

    # Simulate a v8 update on slim swarming testers. The revision
    # property is mandatory. The commit position is required by gatekeeper.
    api.step.active_result.presentation.properties['got_revision'] = (
        api.properties['revision'])
    api.step.active_result.presentation.properties['got_revision_cp'] = (
        api.properties.get('parent_got_revision_cp'))
    v8.set_up_swarming()
  else:
    # Make sure we don't run a non-pure swarming tester on a subdir slave.
    # Subdir slaves have the name pattern 'slaveN-c3#M'.
    assert '#' not in api.properties.get('bot_id', ''), (
        'Can only use pure swarming testers on subdir slaves.')

    if api.platform.is_win:
      api.chromium.taskkill()

    if v8.generate_sanitizer_coverage:
      # When collecting code coverage, we need to sync to the revision that
      # fits to the patch for the line numbers to match.
      revision = v8.calculate_patch_base_gerrit()
      update_step = v8.checkout(revision=revision, suffix='with patch base')
    else:
      update_step = v8.checkout()

    update_properties = update_step.json.output['properties']

    if update_properties.get('got_swarming_client_revision'):
      additional_trigger_properties['parent_got_swarming_client_revision'] = (
          update_properties['got_swarming_client_revision'])

    v8.set_up_swarming()
    v8.runhooks()

    if v8.generate_gcov_coverage:
      v8.init_gcov_coverage()

    test_spec = v8.read_test_spec()
    tests += v8.extra_tests_from_test_spec(test_spec)

    if v8.should_build:
      v8.compile(test_spec)

    if v8.should_upload_build:
      v8.upload_build()

    v8.maybe_create_clusterfuzz_archive(update_step)

    if v8.should_download_build:
      v8.download_build()

  if v8.should_test:
    test_results = v8.runtests(tests)
    v8.maybe_bisect(test_results)

    if not api.tryserver.is_tryserver and test_results.is_negative:
      # Let the overall build fail for failures and flakes.
      raise api.step.StepFailure('Failures or flakes in build.')

    if api.tryserver.is_tryserver and test_results.has_failures:
      # Let tryjobs fail for failures only.
      raise api.step.StepFailure('Failures in tryjob.')

  if v8.generate_gcov_coverage:
    v8.upload_gcov_coverage_report()

  v8.maybe_trigger(test_spec=test_spec, **additional_trigger_properties)


def GenTests(api):
  for mastername, _, buildername, _ in api.v8.iter_builders('v8'):
    yield api.v8.test(mastername, buildername)

  yield (
    api.v8.test(
        'client.v8.branches',
        'V8 Linux - beta branch',
        'branch_sync_failure',
    ) +
    api.step_data('bot_update', retcode=1)
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux',
        'swarming_collect_failure',
    ) +
    api.step_data('Check', retcode=1)
  )

  # Simulate a tryjob triggered by the CQ for setting up different swarming
  # default tags.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng_triggered',
        'triggered_by_cq',
        requester='commit-bot@chromium.org',
        patch_project='v8',
        blamelist=['dude@chromium.org'],
    )
  )

  # Simulate a tryjob triggered by the tryserver for setting up different
  # swarming default tags.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng_triggered',
        'triggered_by_ts',
        requester='dude@chromium.org',
        patch_project='v8',
        blamelist=['dude@chromium.org'],
    )
  )

  # Test usage of test filters. They're used when the buildbucket
  # job gets a property 'testfilter', which is expected to be a json list of
  # test-filter strings.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng_triggered',
        'test_filter',
    ) +
    api.properties(
        testfilter=['mjsunit/regression/*', 'test262/foo', 'test262/bar'],
        extra_flags='--trace_gc --turbo_stats',
    )
  )

  # Test extra properties on a builder bot to ensure it triggers the tester
  # with the right properties.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_win64_rel_ng',
        'test_filter_builder',
    ) +
    api.properties(
        testfilter=['mjsunit/regression/*', 'test262/foo', 'test262/bar'],
        extra_flags='--trace_gc --turbo_stats',
    ) +
    api.post_process(Filter('trigger'))
  )

  # Test using extra flags with a bot that already uses some extra flags as
  # positional argument.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng_triggered',
        'positional_extra_flags',
    ) +
    api.properties(
        extra_flags=['--trace_gc', '--turbo_stats'],
    )
  )

  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng_triggered',
        'failures',
    ) +
    api.override_step_data(
        'Check', api.v8.output_json(has_failures=True))
  )

  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng_triggered',
        'flakes',
    ) +
    api.override_step_data(
        'Check', api.v8.output_json(has_failures=True, flakes=True))
  )

  def TestFailures(wrong_results, flakes):
    results_suffix = "_wrong_results" if wrong_results else ""
    flakes_suffix = "_flakes" if flakes else ""
    return (
      api.v8.test(
          'client.v8',
          'V8 Linux64 - internal snapshot',
          'test_failures%s%s' % (results_suffix, flakes_suffix),
      ) +
      api.override_step_data(
          'Check', api.v8.output_json(
              has_failures=True, wrong_results=wrong_results, flakes=flakes))
    )

  yield TestFailures(wrong_results=False, flakes=False)
  yield TestFailures(wrong_results=False, flakes=True)
  yield (
      TestFailures(wrong_results=True, flakes=False) +
      api.expect_exception('AssertionError')
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux64 - internal snapshot',
        'empty_json',
    ) +
    api.override_step_data('Check', api.json.output([])) +
    api.expect_exception('AssertionError')
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux64 - internal snapshot',
        'one_failure',
    ) +
    api.override_step_data('Check', api.v8.one_failure())
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux64',
        'one_failure_build_env_not_supported',
    ) +
    api.override_step_data('Check', api.v8.one_failure()) +
    api.properties(parent_build_environment=None)
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Fuzzer',
        'fuzz_archive',
    ) +
    api.step_data('Fuzz', retcode=1)
  )

  # Bisect over range a1, a2, a3. Assume a2 is the culprit. Steps:
  # Bisect a0 -> no failures.
  # Bisect a2 -> failures.
  # Bisect a1 -> no failures.
  # Report culprit a2.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - predictable',
        'bisect',
    ) +
    api.v8.fail('Check - d8') +
    api.v8.fail('Bisect a2.Retry') +
    api.time.step(120)
  )

  # The same as above, but overriding changes.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - predictable',
        'bisect_override_changes',
    ) +
    api.properties(
        override_changes=[
          {'revision': 'a1'},
          {'revision': 'a2'},
          {'revision': 'a3'},
        ],
    ) +
    api.v8.fail('Check - d8') +
    api.v8.fail('Bisect a2.Retry') +
    api.time.step(120)
  )

  # Disable bisection, because the failing test is too long compared to the
  # overall test time.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - predictable',
        'bisect_tests_too_long',
    ) +
    api.v8.fail('Check - d8') +
    api.time.step(7)
  )

  # Bisect over range a1, a2, a3. Assume a2 is the culprit.
  # Same as above with a swarming builder_tester.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - shared',
        'bisect_swarming',
    ) +
    api.v8.fail('Check') +
    api.v8.fail('Bisect a2.Retry') +
    api.time.step(120)
  )

  # Bisect over range a1, a2, a3. Assume a3 is the culprit. This is a tester
  # and the build for a2 is not available. Steps:
  # Bisect a0 -> no failures.
  # Bisect a1 -> no failures.
  # Report a2 and a3 as possible culprits.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux64',
        'bisect_tester_swarming',
    ) +
    api.v8.fail('Check') +
    api.time.step(120)
  )

  # Same as above with a slim swarming tester.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux64 - custom snapshot - debug',
        'slim_bisect_tester_swarming',
    ) +
    api.v8.fail('Mjsunit') +
    api.override_step_data(
        'Bisect a0.gsutil download isolated json',
        api.json.output({'mjsunit': '[dummy hash for bisection]'}),
    ) +
    api.override_step_data(
        'Bisect a1.gsutil download isolated json',
        api.json.output({'mjsunit': '[dummy hash for bisection]'}),
    ) +
    api.time.step(120)
  )

  # Same as above with a windows bot. Regression test making sure that
  # the swarming hashes are searched in a windows bucket.
  f = Filter()
  f = f.include_re(r'.*check build.*')
  yield (
    api.v8.test(
        'client.v8',
        'V8 Win32',
        'bisect',
    ) +
    api.v8.fail('Check') +
    api.post_process(f) +
    api.time.step(120)
  )

  # Disable bisection due to a recurring failure. Steps:
  # Bisect a0 -> failures.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - predictable',
        'bisect_recurring_failure',
    ) +
    api.v8.fail('Check - d8') +
    api.v8.fail('Bisect a0.Retry') +
    api.time.step(120)
  )

  # Disable bisection due to less than two changes.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - predictable',
        'bisect_one_change',
    ) +
    api.v8.fail('Check - d8') +
    api.url.json(
        'Bisect.Fetch changes', api.v8.example_one_buildbot_change()) +
    api.override_step_data(
        'Bisect.Get change range',
        api.v8.example_bisection_range_one_change(),
    ) +
    api.time.step(120)
  )

  # Explicitly highlight slow tests not marked as slow.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng_triggered',
        'slow_tests',
        requester='commit-bot@chromium.org',
        patch_project='v8',
        blamelist=['dude@chromium.org'],
    ) +
    api.override_step_data(
        'Check', api.v8.output_json(unmarked_slow_test=True))
  )

  # Test tryjob with named cache.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng',
        'with_cache',
        requester='commit-bot@chromium.org',
        blamelist=['dude@chromium.org'],
        path_config='generic',
    )
  )

  # Test using build_id (replaces buildnumber in LUCI world).
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux_rel_ng',
        'with_build_id',
        build_id='buildbucket/cr-buildbucket.appspot.com/1234567890',
    )
  )

  # Test reading a pyl test-spec from the V8 repository. The additional test
  # targets should be isolated and the tests should be executed.
  f = Filter()
  f = f.include('read test spec')
  f = f.include('isolate tests')
  f = f.include_re(r'.*Mjsunit.*')
  yield (
    api.v8.test(
        'client.v8',
        'V8 Mac64',
        'with_test_spec',
    ) +
    api.path.exists(api.path['checkout'].join(
        'infra', 'testing', 'client.v8.pyl')) +
    api.override_step_data(
        'read test spec',
        api.v8.example_test_spec(
            'V8 Mac64',
            '[{"name": "mjsunit", "variant": "sweet", "shards": 2}]',
        ),
    ) +
    api.post_process(f)
  )

  # As above but on a builder. The additional test targets should be isolated
  # and the tests should be passed as properties to the triggered testers in
  # the trigger step.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - nosnap builder',
        'with_test_spec',
    ) +
    api.path.exists(api.path['checkout'].join(
        'infra', 'testing', 'client.v8.pyl')) +
    api.override_step_data(
        'read test spec',
        api.v8.example_test_spec(
            'V8 Linux - nosnap',
            '[{"name": "mjsunit", "variant": "sweet", "shards": 2}]',
        ),
    ) +
    api.post_process(Filter(
        'read test spec',
        'generate_build_files',
        'isolate tests',
        'trigger',
    ))
  )

  # As above but on a tester. The additional tests passed as property from the
  # builder should be executed.
  f = Filter()
  f = f.include_re(r'.*Mjsunit.*')
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - nosnap',
        'with_test_spec',
        parent_test_spec=[["mjsunit", 2, "sweet"]],
    ) +
    api.post_process(f)
  )

  # Test that uploading/downloading binaries happens to/from experimental GS
  # folder when running in LUCI experimental mode and that internal proxy
  # builder is not triggered.
  yield (
      api.v8.test('client.v8', 'V8 Linux - builder', 'experimental') +
      api.runtime(is_luci=False, is_experimental=True) +
      api.post_process(DoesNotRun, 'trigger (2)') +
      api.post_process(Filter(
        'gsutil upload', 'package build', 'perf dashboard post'))
  )

  yield (
      api.v8.test('client.v8', 'V8 Linux - presubmit', 'experimental') +
      api.runtime(is_luci=True, is_experimental=True) +
      api.post_process(Filter('extract build'))
  )

  # Test that swarming tasks scheduled from experimental builders have low prio.
  yield (
      api.v8.test('client.v8', 'V8 Linux', 'experimental') +
      api.runtime(is_luci=True, is_experimental=True) +
      api.post_process(Filter('[trigger] Check'))
  )

  # Test triggering CI child builders on LUCI.
  yield (
      api.v8.test('client.v8', 'V8 Linux - builder', 'trigger_on_luci') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.post_process(Filter('trigger'))
  )

  # Test using set_gclient_var property.
  yield (
      api.v8.test('client.v8', 'V8 Linux - builder', 'set_gclient_var',
                  set_gclient_var='download_gcmole') +
      api.v8.check_in_param(
          'bot_update',
          '--spec-path', '\'custom_vars\': {\'download_gcmole\': \'True\'}') +
      api.post_process(DropExpectation)
  )