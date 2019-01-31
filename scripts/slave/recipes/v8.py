# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (
    Filter, DoesNotRun, DropExpectation, MustRun, ResultReasonRE, StepException)
from recipe_engine.recipe_api import Property

DEPS = [
  'archive',
  'chromium',
  'depot_tools/gclient',
  'depot_tools/infra_paths',
  'recipe_engine/buildbucket',
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
  # Additional configurations to enable binary size tracking. The mapping
  # consists of "binary" and "category".
  'binary_size_tracking': Property(default=None, kind=dict),
  # One of Release|Debug.
  'build_config': Property(default=None, kind=str),
  # Switch to clobber build dir before runhooks.
  'clobber': Property(default=False, kind=bool),
  # Switch to clobber build dir before bot_update.
  'clobber_all': Property(default=False, kind=bool),
  # Additional configurations set for archiving builds to GS buckets for
  # clusterfuzz. The mapping consists of "name", "bucket" and optional
  # "bitness".
  'clusterfuzz_archive': Property(default=None, kind=dict),
  # Optional coverage setting. One of gcov|sanitizer.
  'coverage': Property(default=None, kind=str),
  # Mapping of custom dependencies to sync (dependency name as in DEPS file ->
  # deps url).
  'custom_deps': Property(default=None, kind=dict),
  # Optional list of default targets. If not specified the implicit "all" target
  # will be built.
  'default_targets': Property(default=None, kind=list),
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
  # Weather to track and upload build-dependencies stats.
  'track_build_dependencies': Property(default=None, kind=bool),
  # List of tester names to trigger.
  'triggers': Property(default=None, kind=list),
  # Weather to trigger the internal trigger proxy.
  'triggers_proxy': Property(default=False, kind=bool),
  # Weather to use goma for compilation.
  'use_goma': Property(default=True, kind=bool),
}


def RunSteps(api, binary_size_tracking, build_config, clobber, clobber_all,
             clusterfuzz_archive, coverage, custom_deps, default_targets,
             enable_swarming, mb_config_path, set_gclient_var, target_arch,
             target_platform, track_build_dependencies, triggers,
             triggers_proxy, use_goma):
  v8 = api.v8
  v8.load_static_test_configs()
  bot_config = v8.update_bot_config(
      v8.bot_config_by_buildername(use_goma=use_goma),
      binary_size_tracking, build_config, clusterfuzz_archive, coverage,
      enable_swarming, target_arch, target_platform, track_build_dependencies,
      triggers, triggers_proxy,
  )
  v8.apply_bot_config(bot_config)
  v8.set_gclient_custom_var(set_gclient_var)
  v8.set_gclient_custom_deps(custom_deps)
  v8.set_chromium_configs(clobber, default_targets)

  # Opt out of using gyp environment variables.
  api.chromium.c.use_gyp_env = False

  additional_trigger_properties = {}
  test_spec = v8.TEST_SPEC()
  tests = v8.create_tests()

  # Tests from V8-side test specs have precedence.
  tests = v8.dedupe_tests(v8.extra_tests_from_properties(), tests)

  if v8.is_pure_swarming_tester:
    with api.step.nest('initialization'):
      api.swarming_client.checkout()

      # This is to install golang swarming client via CIPD.
      with api.swarming_client.on_path():
        pass

      # Simulate a v8 update on slim swarming testers. The revision
      # property is mandatory. The commit position is required by gatekeeper.
      api.step.active_result.presentation.properties['got_revision'] = (
          api.buildbucket.gitiles_commit.id)
      api.step.active_result.presentation.properties['got_revision_cp'] = (
          api.properties.get('parent_got_revision_cp'))
      v8.set_up_swarming()
  else:
    with api.step.nest('initialization'):
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
        update_step = v8.checkout(
            revision=revision, suffix='with patch base', clobber=clobber_all)
      else:
        update_step = v8.checkout(clobber=clobber_all)

      update_properties = update_step.json.output['properties']

      if update_properties.get('got_swarming_client_revision'):
        additional_trigger_properties['parent_got_swarming_client_revision'] = (
            update_properties['got_swarming_client_revision'])

      v8.set_up_swarming()
      v8.runhooks()

      if v8.generate_gcov_coverage:
        v8.init_gcov_coverage()

      # Dynamically load more test specifications from all discovered test
      # roots.
      test_roots = v8.get_test_roots()
      for test_root in test_roots:
        v8.update_test_configs(v8.load_dynamic_test_configs(test_root))
        test_spec.update(v8.read_test_spec(test_root))
        # Tests from dynamic test roots have precedence.
        tests = v8.dedupe_tests(v8.extra_tests_from_test_spec(test_spec), tests)

    if v8.should_build:
      with api.step.nest('build'):
        v8.compile(test_spec)
      if api.v8.should_collect_post_compile_metrics:
        with api.step.nest('measurements'):
          api.v8.collect_post_compile_metrics()

    if v8.should_upload_build:
      v8.upload_build()

    v8.maybe_create_clusterfuzz_archive(update_step)

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
  yield (
    api.v8.test(
        'client.v8.branches',
        'V8 Foobar',
        'branch_sync_failure',
        git_ref='refs/branch-heads/4.3',
    ) +
    api.step_data('initialization.bot_update', retcode=1)
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
        'v8_foobar_rel_ng',
        'test_filter_builder',
        triggers=['v8_foobar_rel_ng_triggered'],
        testfilter=['mjsunit/regression/*', 'intl/foo', 'intl/bar'],
        extra_flags='--trace_gc --turbo_stats',
    ) +
    api.v8.test_spec_in_checkout(
        'v8_foobar_rel_ng', test_spec, 'v8_foobar_rel_ng_triggered') +
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

  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'infra_failure',
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.override_step_data('Check', api.v8.infra_failure()) +
    api.post_process(StepException, 'Check') +
    api.post_process(ResultReasonRE, 'Failures or flakes in build.') +
    api.post_process(DropExpectation)
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
        'V8 Foobar',
        'with_test_spec',
    ) +
    api.v8.test_spec_in_checkout('V8 Foobar', test_spec) +
    api.post_process(
        Filter()
            .include('initialization.read test spec (v8)')
            .include('build.isolate tests')
            .include_re(r'.*Mjsunit.*')
    )
  )

  # As above but on a builder. The additional test targets should be isolated
  # and the tests should be passed as properties to the triggered testers in
  # the trigger step.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar builder',
        'with_test_spec',
        triggers=['V8 Foobar'],
    ) +
    api.v8.test_spec_in_checkout(
        'V8 Foobar builder', test_spec, 'V8 Foobar') +
    api.post_process(Filter(
        'initialization.read test spec (v8)',
        'build.generate_build_files',
        'build.isolate tests',
        'trigger',
    ))
  )

  # As above but on a tester. The additional tests passed as property from the
  # builder should be executed.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'tester_with_test_spec',
        parent_bot_config=release_bot_config,
        parent_buildername='V8 Foobar builder',
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
    api.v8.check_not_in_any_arg('trigger tests.[trigger] Mjsunit on Android', 'cpu') +
    api.v8.check_not_in_any_arg('trigger tests.[trigger] Mjsunit on Android', 'gpu') +
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
            'v8', 'custom_deps', 'test_checkout', 'infra',
            'testing', 'config.pyl'),
        api.path['builder_cache'].join(
            'v8', 'custom_deps', 'test_checkout', 'infra',
            'testing', 'builders.pyl'),
    ) +
    api.override_step_data(
        'initialization.read test config (test_checkout)',
        api.v8.example_test_config(extra_test_config),
    ) +
    api.override_step_data(
        'initialization.read test spec (test_checkout)',
        api.v8.example_test_spec('V8 Foobar', extra_test_spec),
    ) +
    api.post_process(DoesNotRun, 'build.isolate tests') +
    api.post_process(
        Filter()
            .include(
              'initialization.read test config (test_checkout)')
            .include(
              'initialization.read test spec (test_checkout)')
            .include_re(r'.*Foounit.*')
    )
  )

  # Test using custom_deps, set_gclient_var and mb_config_path property.
  yield (
      api.v8.test('client.v8', 'V8 Foobar - builder', 'set_gclient_var',
                  custom_deps={'v8/foo': 'bar'},
                  mb_config_path='somewhere/else/mb_config.pyl',
                  set_gclient_var='download_gcmole') +
      api.v8.check_in_param(
          'initialization.bot_update',
          '--spec-path', '\'custom_vars\': {\'download_gcmole\': \'True\'}') +
      api.v8.check_in_param(
          'initialization.bot_update',
          '--spec-path', '\'custom_deps\': {\'v8/foo\': \'bar\'}') +
      api.v8.check_in_param(
          'build.generate_build_files',
          '--config-file', 'somewhere/else/mb_config.pyl') +
      api.post_process(DropExpectation)
  )

  # Test using source side properties.
  yield (
      api.v8.test('client.v8', 'V8 Foobar - builder', 'src_side_properties',
                  build_config='Debug',
                  target_arch='arm',
                  target_platform='fuchsia',
                  triggers=['V8 Foobar'],
                  triggers_proxy=True,
      ) +
      api.v8.check_in_param(
          'initialization.bot_update',
          '--spec-path', 'target_cpu = [\'arm\', \'arm64\']') +
      api.v8.check_in_param(
          'initialization.bot_update',
          '--spec-path', 'target_os = [\'fuchsia\']') +
      api.v8.check_in_any_arg('build.generate_build_files', 'Debug') +
      api.v8.check_in_any_arg('build.compile', 'Debug') +
      api.post_process(Filter('trigger'))
  )

  # Test triggering a non-luci builder.
  yield (
      api.v8.test('client.v8', 'V8 Foobar - builder', 'non_luci',
                  build_config='Release',
                  triggers='V8 Foobar') +
      api.runtime(is_luci=False, is_experimental=False) +
      api.post_process(Filter('trigger'))
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
    api.post_process(Filter('build.isolate tests'))
  )

  # Same template as in chromium recipe, but with 64 bits target cpu.
  fake_gn_args_x64 = (
      '\n'
      'Writing """\\\n'
      'goma_dir = "/b/build/slave/cache/goma_client"\n'
      'target_cpu = "x64"\n'
      'use_goma = true\n'
      '""" to _path_/args.gn.\n'
  )

  # Cover running sanitizer coverage.
  yield (
    api.v8.test(
        'tryserver.v8',
        'v8_foobar',
        'sanitizer_coverage',
        build_config='Release',
        coverage='sanitizer',
    ) +
    api.step_data(
        'build.lookup GN args', api.raw_io.stream_output(fake_gn_args_x64)) +
    api.v8.test_spec_in_checkout(
        'v8_foobar',
        '{"tests": [{"name": "v8testing"}]}') +
    api.post_process(Filter(
        'Initialize coverage data',
        'Merge coverage data',
        'build.gsutil upload',
        'Split coverage data',
        'gsutil coverage data',
    ))
  )

  # Cover running gcov coverage.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'gcov_coverage',
        build_config='Release',
        clobber=True,
        coverage='gcov',
        enable_swarming=False,
    ) +
    api.step_data(
        'build.lookup GN args', api.raw_io.stream_output(fake_gn_args_x64)) +
    api.v8.test_spec_in_checkout(
        'V8 Foobar',
        '{"tests": [{"name": "v8testing"}]}') +
    api.post_process(MustRun, 'initialization.clobber') +
    api.post_process(Filter(
        'initialization.docker login',
        'initialization.lcov zero counters',
        'lcov capture',
        'lcov remove',
        'genhtml',
        'gsutil coverage report',
    ))
  )

  # Test using clobber_all property.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'clobber_all',
        clobber_all=True
    ) +
    api.v8.check_in_any_arg('initialization.bot_update', '--clobber') +
    api.post_process(DropExpectation)
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

  # Test configurations for clusterfuzz builders.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'clusterfuzz',
        clobber=True,
        clusterfuzz_archive={
          'name': 'd8_bar',
          'bucket': 'v8_clusterfoo',
          'bitness': 64,
        },
        default_targets=['v8_foobar'],
    ) +
    api.post_process(MustRun, 'initialization.clobber') +
    api.post_process(Filter(
        'build.compile',
        'create staging_dir',
        'filter build_dir',
        'zipping',
        'gsutil upload',
    ))
  )

  # Test configurations for post-compilation build measurements.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'measurements',
        binary_size_tracking={
          'binary': 'd8',
          'category': 'foo64',
        },
        track_build_dependencies=True,
    ) +
    api.post_process(Filter(
        'measurements.track build dependencies (fyi)',
        'measurements.Check binary size',
        'measurements.perf dashboard post',
        'measurements.perf dashboard post (2)',
    ))
  )

  # Test windows-specific build steps.
  yield (
    api.v8.test(
        'client.v8',
        'V8 Foobar',
        'windows',
    ) +
    api.platform('win', 64) +
    api.post_process(MustRun, 'initialization.taskkill') +
    api.post_process(DropExpectation)
  )
