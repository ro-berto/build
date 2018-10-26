# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (
    Filter, DoesNotRun, DropExpectation, MustRun)
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
  # One of Release|Debug.
  'build_config': Property(default=None, kind=str),
  # Mapping of custom dependencies to sync (dependency name as in DEPS file ->
  # deps url).
  'custom_deps': Property(default=None, kind=dict),
  # Switch to enable/disable swarming.
  'enable_swarming': Property(default=None, kind=bool),
  # Optional path to a different MB config. The path must be relative to the
  # V8 checkout and using forward slashes.
  'mb_config_path': Property(default=None, kind=str),
  # Name of a gclient custom_var to set to 'True'.
  'set_gclient_var': Property(default=None, kind=str),
  # One of intel|arm|mips.
  'target_arch': Property(default=None, kind=str),
  # One of android|fuchsia|linux|mac|win.
  'target_platform': Property(default=None, kind=str),
  # List of tester names to trigger.
  'triggers': Property(default=None, kind=list),
  # Weather to use goma for compilation.
  'use_goma': Property(default=True, kind=bool),
}


def RunSteps(api, build_config, custom_deps, enable_swarming, mb_config_path,
             set_gclient_var, target_arch, target_platform, triggers,
             use_goma):
  v8 = api.v8
  v8.load_static_test_configs()
  bot_config = v8.update_bot_config(
      v8.bot_config_by_buildername(use_goma=use_goma),
      build_config, enable_swarming, target_arch, target_platform, triggers
  )
  v8.apply_bot_config(bot_config)
  v8.set_gclient_custom_var(set_gclient_var)
  v8.set_gclient_custom_deps(custom_deps)

  # Opt out of using gyp environment variables.
  api.chromium.c.use_gyp_env = False

  additional_trigger_properties = {}
  test_spec = v8.TEST_SPEC()
  tests = v8.create_tests()

  # Tests from V8-side test specs have precedence.
  tests = v8.dedupe_tests(v8.extra_tests_from_properties(), tests)

  if v8.is_pure_swarming_tester:
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

    # Dynamically load more test specifications from all discovered test roots.
    test_roots = v8.get_test_roots()
    for test_root in test_roots:
      v8.update_test_configs(v8.load_dynamic_test_configs(test_root))
      test_spec.update(v8.read_test_spec(test_root))
      # Tests from dynamic test roots have precedence.
      tests = v8.dedupe_tests(v8.extra_tests_from_test_spec(test_spec), tests)

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

  # Minimal bot config for a release builder. Used to simulate test data for
  # triggered testers.
  release_bot_config = {
    'testing': {
      'properties': {
        'build_config': 'Release',
      },
      'platform': 'linux',
    },
  }

  # Minimal v8-side test spec for simulating most recipe features.
  test_spec = """
    {
      "tests": [
        {"name": "v8testing"},
        {"name": "test262_variants", "test_args": ["--extra-flags=--flag"]},
      ],
    }
  """.strip()

  # Simulate a tryjob for setting up different swarming default tags.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_foobar_rel_ng_triggered',
        'triggered_by_cq',
        parent_buildername='v8_foobar_rel_ng',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
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
        'v8_foobar_rel_ng_triggered',
        'test_filter',
        parent_buildername='v8_foobar_rel_ng',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
        testfilter=['mjsunit/regression/*', 'intl/foo', 'intl/bar'],
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
        testfilter=['mjsunit/regression/*', 'intl/foo', 'intl/bar'],
        extra_flags='--trace_gc --turbo_stats',
    ) +
    api.post_process(Filter('trigger'))
  )

  # Test using extra flags with a bot that already uses some extra flags as
  # positional argument.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_foobar_rel_ng_triggered',
        'positional_extra_flags',
        parent_buildername='v8_foobar_rel_ng',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
        extra_flags=['--trace_gc', '--turbo_stats'],
    )
  )

  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_foobar_rel_ng_triggered',
        'failures',
        parent_buildername='v8_foobar_rel_ng',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
    ) +
    api.override_step_data(
        'Check', api.v8.output_json(has_failures=True))
  )

  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_foobar_rel_ng_triggered',
        'flakes',
        parent_buildername='v8_foobar_rel_ng',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
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
          'V8 Foobar',
          'test_failures%s%s' % (results_suffix, flakes_suffix),
      ) +
      api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
      api.override_step_data(
          'Check', api.v8.output_json(
              has_failures=True, wrong_results=wrong_results, flakes=flakes)) +
      api.post_process(Filter().include_re(r'.*Check.*'))
    )

  yield TestFailures(wrong_results=False, flakes=False)
  yield TestFailures(wrong_results=False, flakes=True)
  yield (
      TestFailures(wrong_results=True, flakes=False) +
      api.expect_exception('AssertionError') +
      api.post_process(DropExpectation)
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'swarming_collect_failure',
        parent_buildername='V8 Foobar - builder',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
    ) +
    api.step_data('Check', retcode=1)
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'empty_json',
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.override_step_data('Check', api.json.output([])) +
    api.expect_exception('AssertionError') +
    api.post_process(DropExpectation)
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'one_failure',
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.override_step_data('Check', api.v8.one_failure())
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'one_failure_build_env_not_supported',
        parent_buildername='V8 Foobar - builder',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
    ) +
    api.override_step_data('Check', api.v8.one_failure()) +
    api.properties(parent_build_environment=None)
  )

  # Test flako command line with interesting data.
  debug_bot_config = {
    'testing': {
      'properties': {
        'build_config': 'Debug',
      },
      'platform': 'win',
    },
  }
  flake_test_spec = """
    {
      "swarming_dimensions": {
        "os": "Windows-7-SP1",
        "cpu": "x86-64",
      },
      "tests": [
        {"name": "test262_variants", "test_args": ["--extra-flags=--flag"]},
      ],
    }
  """.strip()
  yield (
      api.v8.test(
          'client.v8',
          'V8 Foobar',
          'flako',
          parent_buildername='V8 Foobar - builder',
          parent_bot_config=debug_bot_config,
          parent_test_spec=flake_test_spec,
      ) +
      api.override_step_data(
          'Test262', api.v8.output_json(has_failures=True, flakes=True)) +
      api.post_process(Filter('Test262 (flakes)'))
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'generic_swarming_task',
        parent_buildername='V8 Foobar - builder',
        parent_bot_config=release_bot_config,
        parent_test_spec='{"tests": [{"name": "jsfunfuzz"}]}',
    )
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'fuzz_archive',
        parent_buildername='V8 Foobar - builder',
        parent_bot_config=release_bot_config,
        parent_test_spec='{"tests": [{"name": "jsfunfuzz"}]}',
    ) +
    api.step_data('Fuzz', retcode=1)
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'gcmole',
        parent_buildername='V8 Foobar - builder',
        parent_bot_config=release_bot_config,
        parent_test_spec='{"tests": [{"name": "gcmole"}]}',
    )
  )

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'initializers',
        parent_buildername='V8 Foobar - builder',
        parent_bot_config=release_bot_config,
        parent_test_spec='{"tests": [{"name": "v8initializers"}]}',
    )
  )

  # Bisect over range a1, a2, a3. Assume a2 is the culprit. Steps:
  # Bisect a0 -> no failures.
  # Bisect a2 -> failures.
  # Bisect a1 -> no failures.
  # Report culprit a2.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'bisect',
        enable_swarming=False,
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.v8.fail('Check') +
    api.v8.fail('Bisect a2.Retry') +
    api.time.step(120)
  )

  # The same as above, but overriding changes.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'bisect_override_changes',
        enable_swarming=False,
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.properties(
        override_changes=[
          {'revision': 'a1', 'when': 1},
          {'revision': 'a2', 'when': 2},
          {'revision': 'a3', 'when': 3},
        ],
    ) +
    api.v8.fail('Check') +
    api.v8.fail('Bisect a2.Retry') +
    api.time.step(120)
  )

  # Disable bisection, because the failing test is too long compared to the
  # overall test time.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'bisect_tests_too_long',
        enable_swarming=False,
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.v8.fail('Check') +
    api.time.step(7)
  )

  # Bisect over range a1, a2, a3. Assume a2 is the culprit.
  # Same as above with a swarming builder_tester.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'bisect_swarming',
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
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
        'V8 Foobar',
        'bisect_tester_swarming',
        parent_buildername='V8 Foobar - builder',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
    ) +
    api.v8.fail('Check') +
    api.time.step(120)
  )

  # Disable bisection due to a recurring failure. Steps:
  # Bisect a0 -> failures.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'bisect_recurring_failure',
        enable_swarming=False,
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.v8.fail('Check') +
    api.v8.fail('Bisect a0.Retry') +
    api.time.step(120)
  )

  # Disable bisection due to less than two changes.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'bisect_one_change',
        enable_swarming=False,
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.v8.fail('Check') +
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
        'v8_foobar_rel_ng_triggered',
        'slow_tests',
        parent_buildername='v8_foobar_rel_ng',
        parent_bot_config=release_bot_config,
        parent_test_spec=test_spec,
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
        'v8_foobar_rel_ng',
        'with_cache',
        blamelist=['dude@chromium.org'],
        build_config='Release',
        path_config='generic',
        requester='commit-bot@chromium.org',
        triggers=['v8_foobar_rel_ng_triggered'],
    )
  )

  # Test using build_id (replaces buildnumber in LUCI world).
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_foobar_rel_ng',
        'with_build_id',
        build_config='Release',
        build_id='buildbucket/cr-buildbucket.appspot.com/1234567890',
        triggers=['v8_foobar_rel_ng_triggered'],
    )
  )

  # Test reading a pyl test-spec from the V8 repository. The additional test
  # targets should be isolated and the tests should be executed.
  test_spec = """
    {
      "swarming_dimensions": {
        "pool": "noodle",
        "gpu": "quantum",
      },
      "swarming_task_attrs": {
        "priority": 25,
        "hard_timeout": 7200,
      },
      "tests": [
        {
          "name": "mjsunit",
          "variant": "sweet",
          "shards": 2,
        },
        {
          "name": "mjsunit",
          "variant": "sour",
          "suffix": "everything",
          "test_args": ["--extra-flags", "--flag1 --flag2"],
          # This tests that the default pool dimension above is overridden.
          "swarming_dimensions": {"pool": "override"},
          # This tests that the default priority above is overridden.
          "swarming_task_attrs": {"priority": 100},
        },
      ],
    }
  """.strip()
  yield (
    api.v8.test(
        'client.v8',
        'V8 Mac64',
        'with_test_spec',
    ) +
    api.v8.test_spec_in_checkout('V8 Mac64', test_spec) +
    api.post_process(
        Filter()
            .include('read test spec (v8)')
            .include('isolate tests')
            .include_re(r'.*Mjsunit.*')
    )
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
    api.v8.test_spec_in_checkout(
        'V8 Linux - nosnap builder', test_spec, 'V8 Linux - nosnap') +
    api.post_process(Filter(
        'read test spec (v8)',
        'generate_build_files',
        'isolate tests',
        'trigger',
    ))
  )

  # As above but on a tester. The additional tests passed as property from the
  # builder should be executed.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Linux - nosnap',
        'with_test_spec',
        parent_test_spec=test_spec,
    ) +
    api.post_process(Filter().include_re(r'.*Mjsunit.*'))
  )

  # Test that cpu and gpu dimensinos are reset when triggering Android bots.
  android_test_spec = """
    {
      "swarming_dimensions": {
        "os": "Android",
      },
      "tests": [
        {
          "name": "mjsunit",
        },
      ],
    }
  """.strip()
  yield (
    api.v8.test(
        'client.v8',
        'Android bot',
        parent_build_config='Release',
        parent_test_spec=android_test_spec,
        swarm_hashes={'mjsunit': 'hash'},
    ) +
    api.v8.check_not_in_any_arg('[trigger] Mjsunit on Android', 'cpu') +
    api.v8.check_not_in_any_arg('[trigger] Mjsunit on Android', 'gpu') +
    api.post_process(DropExpectation)
  )

  # Test reading pyl test configs and build configs from a separate checkout.
  extra_test_config = """
    {
      'foounit': {
        'name': 'Foounit',
        'tests': ['foounit'],
      },
    }
  """.strip()
  extra_test_spec = """
    {
      "tests": [
        {
          "name": "foounit",
        },
      ],
    }
  """.strip()
  yield (
    api.v8.test(
        'somewhere.v8',
        'V8 Foobar',
        'with_test_config',
        enable_swarming=False,
    ) +
    api.v8.example_test_roots('test_checkout') +
    api.path.exists(
        api.path['builder_cache'].join(
            'V8_Foobar', 'v8', 'custom_deps', 'test_checkout', 'infra',
            'testing', 'config.pyl'),
        api.path['builder_cache'].join(
            'V8_Foobar', 'v8', 'custom_deps', 'test_checkout', 'infra',
            'testing', 'builders.pyl'),
    ) +
    api.override_step_data(
        'read test config (test_checkout)',
        api.v8.example_test_config(extra_test_config),
    ) +
    api.override_step_data(
        'read test spec (test_checkout)',
        api.v8.example_test_spec('V8 Foobar', extra_test_spec),
    ) +
    api.post_process(DoesNotRun, 'isolate tests') +
    api.post_process(
        Filter()
            .include('read test config (test_checkout)')
            .include('read test spec (test_checkout)')
            .include_re(r'.*Foounit.*')
    )
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
      api.v8.test(
          'client.v8',
          'V8 Foobar',
          'experimental',
          parent_buildername='V8 Foobar - builder',
          parent_bot_config=release_bot_config,
          parent_test_spec='{"tests": [{"name": "v8testing"}]}',
      ) +
      api.runtime(is_luci=True, is_experimental=True) +
      api.post_process(Filter('[trigger] Check'))
  )

  # Test triggering CI child builders on LUCI.
  yield (
      api.v8.test('client.v8', 'V8 Linux - builder', 'trigger_on_luci') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.post_process(Filter('trigger'))
  )

  # Test using custom_deps, set_gclient_var and mb_config_path property.
  yield (
      api.v8.test('client.v8', 'V8 Linux - builder', 'set_gclient_var',
                  custom_deps={'v8/foo': 'bar'},
                  mb_config_path='somewhere/else/mb_config.pyl',
                  set_gclient_var='download_gcmole') +
      api.v8.check_in_param(
          'bot_update',
          '--spec-path', '\'custom_vars\': {\'download_gcmole\': \'True\'}') +
      api.v8.check_in_param(
          'bot_update',
          '--spec-path', '\'custom_deps\': {\'v8/foo\': \'bar\'}') +
      api.v8.check_in_param(
          'generate_build_files',
          '--config-file', 'somewhere/else/mb_config.pyl') +
      api.post_process(DropExpectation)
  )

  # Test using source side properties. The properties we set make no sense at
  # all. We merely test that they will override the properties specified on
  # the infra side.
  yield (
      api.v8.test('client.v8', 'V8 Linux - builder', 'src_side_properties',
                  build_config='Debug',
                  target_arch='arm',
                  target_platform='fuchsia') +
      api.v8.check_in_param(
          'bot_update', '--spec-path', 'target_cpu = [\'arm\', \'arm64\']') +
      api.v8.check_in_param(
          'bot_update', '--spec-path', 'target_os = [\'fuchsia\']') +
      api.v8.check_in_any_arg('generate_build_files', 'Debug') +
      api.v8.check_in_any_arg('compile', 'Debug') +
      api.v8.check_triggers('V8 Linux', 'V8 Linux - presubmit') +
      api.post_process(DropExpectation)
  )

  # Test uploading coverage reports is done to experimental bucket.
  yield (
      api.v8.test('client.v8', 'V8 Linux64 - gcov coverage', 'experimental') +
      api.runtime(is_luci=True, is_experimental=True) +
      api.post_process(Filter('gsutil coverage report'))
  )

  # Test for covering a hack in swarming/api.py for crbug.com/842234.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'no_cpython_on_mips',
        parent_buildername='V8 Foobar - builder',
        parent_bot_config=release_bot_config,
        parent_test_spec='{"tests": [{"name": "mjsunit"}], '
                         '"swarming_dimensions": {"cpu": "mips-32"}}',
    ) +
    api.post_process(DropExpectation)
  )

  # Cover test config entries with specific isolate targets.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'specific_isolated_file',
    ) +
    api.v8.test_spec_in_checkout(
        'V8 Foobar',
        '{"tests": [{"name": "numfuzz"}]}') +
    api.post_process(Filter('isolate tests'))
  )

  # Cover running presubmit on a builder.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'presubmit',
    ) +
    api.v8.test_spec_in_checkout(
        'V8 Foobar',
        '{"tests": [{"name": "presubmit"}]}') +
    api.post_process(MustRun, 'Presubmit') +
    api.post_process(DropExpectation)
  )

  # Cover running sanitizer coverage.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_linux64_sanitizer_coverage_rel',
        'sanitizer_coverage',
    ) +
    api.v8.test_spec_in_checkout(
        'v8_linux64_sanitizer_coverage_rel',
        '{"tests": [{"name": "v8testing"}]}') +
    api.post_process(Filter(
        'Initialize coverage data',
        'Merge coverage data',
        'gsutil upload (2)',
        'Split coverage data',
        'gsutil coverage data',
    ))
  )

  # Test switching goma on and off. Goma steps are asserted in the v8 test api.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'goma',
        use_goma=True,
    ) +
    api.post_process(DropExpectation)
  )
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'no_goma',
        use_goma=False,
    ) +
    api.post_process(DropExpectation)
  )
