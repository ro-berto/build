# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze

DEPS = [
  'bot_update',
  'chromium',
  'chromium_android',
  'chromium_tests',
  'gclient',
  'gpu',
  'isolate',
  'itertools',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'raw_io',
  'step',
  'swarming',
  'test_utils',
  'tryserver',
]


BUILDERS = freeze({
  'tryserver.chromium.linux': {
    'builders': {
      'linux_android_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.linux',
          'buildername': 'Android Builder (dbg)',
          'tester': 'Android Tests (dbg)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_android_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.linux',
          'buildername': 'Android Builder',
          'tester': 'Android Tests',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_dbg_32_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder (dbg)(32)',
          'tester': 'Linux Tests (dbg)(1)(32)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder (dbg)',
          'tester': 'Linux Tests (dbg)(1)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder',
          'tester': 'Linux Tests',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_asan_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.memory',
          'buildername': 'Linux ASan LSan Builder',
          'tester': 'Linux ASan LSan Tests (1)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_compile_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder (dbg)',
        },
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_compile_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder',
        },
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.chromiumos',
          'buildername': 'Linux ChromiumOS Builder (dbg)',
          'tester': 'Linux ChromiumOS Tests (dbg)(1)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_compile_dbg_ng': {
        'add_telemetry_tests': False,
        'based_on_main_waterfall': {
          'mastername': 'chromium.chromiumos',
          'buildername': 'Linux ChromiumOS Builder (dbg)',
        },
        'compile_only': True,
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.chromiumos',
          'buildername': 'Linux ChromiumOS Builder',
          'tester': 'Linux ChromiumOS Tests (1)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_asan_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.memory',
          'buildername': 'Linux Chromium OS ASan LSan Builder',
          'tester': 'Linux Chromium OS ASan LSan Tests (1)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_compile_rel_ng': {
        'add_telemetry_tests': False,
        'based_on_main_waterfall': {
          'mastername': 'chromium.chromiumos',
          'buildername': 'Linux ChromiumOS Builder',
        },
        'compile_only': True,
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_ozone_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.chromiumos',
          'buildername': 'Linux ChromiumOS Ozone Builder',
          'tester': 'Linux ChromiumOS Ozone Tests (1)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_ozone_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.chromiumos',
          'buildername': 'Linux ChromiumOS Ozone Builder (dbg)',
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_compile_dbg_32_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder (dbg)(32)',
        },
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_practice_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.fyi',
          'buildername': 'ChromiumPracticeFullTester',
        },
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
      'mac_chromium_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.mac',
          'buildername': 'Mac Builder (dbg)',
          'tester': 'Mac10.9 Tests (dbg)',
        },
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_chromium_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.mac',
          'buildername': 'Mac Builder',
          'tester': 'Mac10.8 Tests',
        },
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_chromium_10.6_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.mac',
          'buildername': 'Mac Builder',
          'tester': 'Mac10.6 Tests',
        },
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_chromium_compile_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.mac',
          'buildername': 'Mac Builder (dbg)',
        },
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_chromium_compile_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.mac',
          'buildername': 'Mac Builder',
        },
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_chromium_asan_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.memory',
          'buildername': 'Mac ASan 64 Builder',
          'tester': 'Mac ASan 64 Tests (1)',
        },
        'testing': {
          'platform': 'mac',
        },
      },
      'ios_rel_device_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.mac',
          'buildername': 'iOS Device',
        },
        'testing': {
          'platform': 'mac',
        },
      },
      'ios_dbg_simulator_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.mac',
          'buildername': 'iOS Simulator (dbg)',
        },
        'testing': {
          'platform': 'mac',
        },
      },
      'ios_rel_device_ninja_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.mac',
          'buildername': 'iOS Device (ninja)',
        },
        'testing': {
          'platform': 'mac',
        },
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win_chromium_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.win',
          'buildername': 'Win Builder (dbg)',
          'tester': 'Win7 Tests (dbg)(1)',
        },
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.win',
          'buildername': 'Win Builder',
          'tester': 'Win7 Tests (1)',
        },
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_xp_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.win',
          'buildername': 'Win Builder',
          'tester': 'XP Tests (1)',
        },
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_vista_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.win',
          'buildername': 'Win Builder',
          'tester': 'Vista Tests (1)',
        },
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_compile_dbg_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.win',
          'buildername': 'Win Builder (dbg)',
        },
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_compile_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.win',
          'buildername': 'Win Builder',
        },
        # Skip somewhat expensive isolate step where it's not needed.
        'disable_isolate': True,
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_x64_rel_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.win',
          'buildername': 'Win x64 Builder',
          'tester': 'Win 7 Tests x64 (1)',
        },
        'testing': {
          'platform': 'win',
        },
      },
      'win8_chromium_ng': {
        'based_on_main_waterfall': {
          'mastername': 'chromium.win',
          'buildername': 'Win Builder (dbg)',
          'tester': 'Win8 Aura',
        },
        'testing': {
          'platform': 'win',
        },
      },
    },
  },
})

# TODO(sergiyb): This config should be read from an external JSON file
# in a custom step, which can then be mocked in the GenTests.
# TODO(sergiyb): Add Windows dimensions.
CHROMIUM_GPU_DIMENSION_SETS = freeze({
  'tryserver.chromium.linux': {
    'linux_chromium_rel_ng': [
      {
        'gpu': '10de:104a',  # NVIDIA GeForce GT 610
        'os': 'Linux',
      },
    ],
  },
  'tryserver.chromium.mac': {
    'mac_chromium_rel_ng': [
      {
        'gpu': '8086:0116',  # Intel HD Graphics 3000
        'hidpi': '0',
        'os': 'Mac-10.8',
      }, {
        'gpu': '10de:0fe9',  # NVIDIA GeForce GT 750M
        'hidpi': '1',
        'os': 'Mac-10.9',
      },
    ],
  },
})


def tests_in_compile_targets(api, compile_targets, tests):
  """Returns the tests in |tests| that have at least one of their compile
  targets in |compile_targets|."""
  result = []
  for test in tests:
    test_compile_targets = test.compile_targets(api)

    # Always return tests that don't require compile. Otherwise we'd never
    # run them.
    if ((set(compile_targets).intersection(set(test_compile_targets))) or
        not test_compile_targets):
      result.append(test)

  return result


def all_compile_targets(api, tests):
  """Returns the compile_targets for all the Tests in |tests|."""
  return sorted(set(x
                    for test in tests
                    for x in test.compile_targets(api)))


def _GenStepsInternal(api):
  def get_bot_config(mastername, buildername):
    master_dict = BUILDERS.get(mastername, {})
    return master_dict.get('builders', {}).get(buildername)

  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  bot_config = get_bot_config(mastername, buildername)
  api.chromium_tests.configure_swarming('chromium', precommit=True)

  main_waterfall_config = bot_config.get('based_on_main_waterfall')
  # TODO(sergiyb): This is a temporary hack to run GPU tests on tryserver
  # only. This should be removed when we will convert chromium.gpu waterfall
  # to swarming and be able to replicate the tests to tryserver automatically.
  master = api.properties['mastername']
  builder = api.properties['buildername']
  enable_gpu_tests = builder in CHROMIUM_GPU_DIMENSION_SETS.get(master, {})

  extra_chromium_configs = ['trybot_flavor']
  if enable_gpu_tests:
    extra_chromium_configs.append('archive_gpu_tests')

  bot_update_step, master_dict, test_spec = \
      api.chromium_tests.sync_and_configure_build(
          main_waterfall_config['mastername'],
          main_waterfall_config['buildername'],
          override_bot_type='builder_tester',
          chromium_apply_config=extra_chromium_configs)

  tests = list(api.chromium_tests.tests_for_builder(
      main_waterfall_config['mastername'],
      main_waterfall_config['buildername'],
      bot_update_step,
      master_dict,
      override_bot_type='builder_tester'))
  tester = main_waterfall_config.get('tester', '')
  if tester:
    test_config = master_dict.get('builders', {}).get(tester)
    for key, value in test_config.get('swarming_dimensions', {}).iteritems():
      api.swarming.set_default_dimension(key, value)
    tests.extend(api.chromium_tests.tests_for_builder(
        main_waterfall_config['mastername'],
        tester,
        bot_update_step,
        master_dict,
        override_bot_type='builder_tester'))

  if enable_gpu_tests:
    tests.extend(api.gpu.create_tests(
        bot_update_step.presentation.properties['got_revision'],
        bot_update_step.presentation.properties['got_webkit_revision'],
        enable_swarming=True,
        swarming_dimension_sets=CHROMIUM_GPU_DIMENSION_SETS[master][builder]))

  compile_targets, tests_including_triggered = \
      api.chromium_tests.get_compile_targets_and_tests(
          main_waterfall_config['mastername'],
          main_waterfall_config['buildername'],
          master_dict,
          override_bot_type='builder_tester',
          override_tests=tests)

  requires_compile, _, compile_targets = \
      api.chromium_tests.analyze(
          all_compile_targets(api, tests + tests_including_triggered),
          compile_targets,
          'trybot_analyze_config.json')

  if requires_compile:
    tests = tests_in_compile_targets(api, compile_targets, tests)
    tests_including_triggered = tests_in_compile_targets(
        api, compile_targets, tests_including_triggered)

    api.chromium_tests.compile_specific_targets(
        main_waterfall_config['mastername'],
        main_waterfall_config['buildername'],
        bot_update_step,
        master_dict,
        test_spec,
        compile_targets,
        tests_including_triggered,
        override_bot_type='builder_tester',
        disable_isolate=bot_config.get('disable_isolate', False))
  else:
    # Even though the patch doesn't require compile, we'd still like to
    # run tests not depending on compiled targets (that's obviously not
    # covered by the "analyze" step).
    tests = [t for t in tests if not t.compile_targets(api)]

  def deapply_patch_fn(failing_tests):
    api.chromium_tests.deapply_patch(bot_update_step)
    compile_targets = list(api.itertools.chain(
        *[t.compile_targets(api) for t in failing_tests]))
    if compile_targets:
      # Remove duplicate targets.
      compile_targets = sorted(set(compile_targets))
      # Search for *.isolated only if enabled in bot config or if some
      # swarming test is being recompiled.
      bot_config = get_bot_config(mastername, buildername)
      has_failing_swarming_tests = [
          t for t in failing_tests if t.uses_swarming]
      if bot_config.get('use_isolate') or has_failing_swarming_tests:
        api.isolate.clean_isolated_files(api.chromium.output_dir)
      try:
        api.chromium.compile(
            compile_targets, name='compile (without patch)')
      except api.step.StepFailure:
        api.tryserver.set_transient_failure_tryjob_result()
        raise
      if bot_config.get('use_isolate') or has_failing_swarming_tests:
        api.isolate.isolate_tests(api.chromium.output_dir, verbose=True)

  return api.test_utils.determine_new_failures(api, tests, deapply_patch_fn)


def GenSteps(api):
  with api.tryserver.set_failure_hash():
    return _GenStepsInternal(api)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.json.canned_gtest_output

  def props(config='Release', mastername='tryserver.chromium.linux',
            buildername='linux_chromium_rel_ng', extra_swarmed_tests=None,
            **kwargs):
    kwargs.setdefault('revision', None)
    swarm_hashes = api.gpu.dummy_swarm_hashes
    if extra_swarmed_tests:
      for test in extra_swarmed_tests:
        swarm_hashes[test] = '[dummy hash for %s]' % test
    return api.properties.tryserver(
      build_config=config,
      mastername=mastername,
      buildername=buildername,
      swarm_hashes=swarm_hashes,
      **kwargs
    )

  def suppress_analyze():
    """Overrides analyze step data so that all targets get compiled."""
    return api.override_step_data(
        'read filter exclusion spec',
        api.json.output({
            'base': {
                'exclusions': ['f.*'],
            },
            'chromium': {
                'exclusions': [],
            },
        })
    )

  # While not strictly required for coverage, record expectations for each
  # of the configs so we can see when and how they change.
  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                  _sanitize_nonalpha(buildername))
      yield (
        api.test(test_name) +
        api.platform(bot_config['testing']['platform'],
                     bot_config.get(
                         'chromium_config_kwargs', {}).get('TARGET_BITS', 64)) +
        props(mastername=mastername, buildername=buildername)
      )

  yield (
    api.test('invalid_results') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'Linux Tests': {
            'gtest_tests': ['base_unittests'],
        },
    })) +
    suppress_analyze() +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('base_unittests (without patch)',
                           api.json.raw_gtest_output(None, retcode=1))
  )

  yield (
    api.test('compile_failure_without_patch_deapply_fn') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'Linux Tests': {
          'gtest_tests': ['base_unittests'],
        },
      })
    ) +
    suppress_analyze() +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('compile (without patch)', retcode=1)
  )

  for step in ('bot_update', 'gclient runhooks (with patch)'):
    yield (
      api.test(_sanitize_nonalpha(step) + '_failure') +
      props() +
      api.platform.name('linux') +
      api.step_data(step, retcode=1)
    )

  yield (
    api.test('runhooks_failure') +
    props(buildername='win_chromium_rel_ng',
          mastername='tryserver.chromium.win') +
    api.platform.name('win') +
    api.step_data('gclient runhooks (with patch)', retcode=1) +
    api.step_data('gclient runhooks (without patch)', retcode=1)
  )

  yield (
    api.test('runhooks_failure_ng') +
    api.platform('linux', 64) +
    props(mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
    api.step_data('gclient runhooks (with patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_ng') +
    api.platform('linux', 64) +
    props(mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
    suppress_analyze() +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_without_patch_ng') +
    api.platform('linux', 64) +
    props(mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
    suppress_analyze() +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (without patch)', retcode=1)
  )

  yield (
    api.test('check_swarming_version_failure') +
    props() +
    api.platform.name('linux') +
    api.step_data('swarming.py --version', retcode=1) +
    api.override_step_data('read test spec', api.json.output({
        'Linux Tests': {
          'gtest_tests': ['base_unittests'],
        },
      })
      ) +
    suppress_analyze()
  )

  # Successfully compiling, isolating and running two targets on swarming for a
  # commit queue job.
  yield (
    api.test('swarming_basic_cq') +
    props(requester='commit-bot@chromium.org', blamelist='joe@chromium.org',
          blamelist_real=['joe@chromium.org'],
          extra_swarmed_tests=['base_unittests', 'browser_tests']) +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
            'swarming': {
              'can_use_on_swarming_builders': True,
              'shards': 5,
              'platforms': ['linux'],
            },
          },
        ],
      })
    ) +
    suppress_analyze()
  )

  # Successfully compiling, isolating and running two targets on swarming for a
  # manual try job.
  yield (
    api.test('swarming_basic_try_job') +
    props(buildername='linux_chromium_rel_ng', requester='joe@chromium.org',
          extra_swarmed_tests=['base_unittests', 'browser_tests']) +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
            'swarming': {
              'can_use_on_swarming_builders': True,
              'shards': 5,
              'platforms': ['linux'],
            },
          },
        ],
      })
    ) +
    suppress_analyze()
  )

  # One target (browser_tests) failed to produce *.isolated file.
  yield (
    api.test('swarming_missing_isolated') +
    props(requester='commit-bot@chromium.org', blamelist='joe@chromium.org',
          blamelist_real=['joe@chromium.org'],
          extra_swarmed_tests=['base_unittests']) +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
        ],
      })
    ) +
    suppress_analyze()
  )

  yield (
    api.test('no_compile_because_of_analyze') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    )
  )

  # Verifies analyze skips projects other than src.
  yield (
    api.test('dont_analyze_for_non_src_project') +
    props(buildername='linux_chromium_rel_ng') +
    props(patch_project='blink') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    )
  )

  # This should result in a compile.
  yield (
    api.test('compile_because_of_analyze_matching_exclusion') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({})) +
    suppress_analyze()
  )

  # This should result in a compile.
  yield (
    api.test('compile_because_of_analyze') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency', 'targets': [],
                       'build_targets': []}))
  )

  yield (
    api.test('compile_because_of_analyze_with_filtered_tests_no_builder') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
          },
          {
            'test': 'unittests',
          },
        ],
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'targets': ['browser_tests', 'base_unittests'],
                       'build_targets': ['browser_tests', 'base_unittests']}))
  )

  yield (
    api.test('compile_because_of_analyze_with_filtered_tests') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
          },
          {
            'test': 'unittests',
          },
        ],
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'targets': ['browser_tests', 'base_unittests'],
                       'build_targets': ['browser_tests', 'base_unittests']}))
  )

  # Tests compile_target portion of analyze module.
  yield (
    api.test('compile_because_of_analyze_with_filtered_compile_targets') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
          },
          {
            'test': 'unittests',
          },
        ],
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'targets': ['browser_tests', 'base_unittests'],
                       'build_targets': ['chrome', 'browser_tests',
                                         'base_unittests']}))
  )

  # Tests compile_targets portion of analyze with a bot that doesn't include the
  # 'all' target.
  yield (
    api.test(
      'compile_because_of_analyze_with_filtered_compile_targets_exclude_all') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'Linux Tests': {
          'gtest_tests': ['base_unittests'],
        },
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'targets': ['browser_tests', 'base_unittests'],
                       'build_targets': ['base_unittests']}))
  )

  # Tests compile_targets portion of analyze with a bot that doesn't include the
  # 'all' target.
  yield (
    api.test(
      'analyze_finds_invalid_target') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'Linux Tests': {
          'gtest_tests': ['base_unittests'],
        },
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'invalid_targets': ['invalid target', 'another one']}))
  )

  gpu_targets = ['angle_unittests_run', 'chrome', 'chromium_builder_tests',
                 'content_gl_tests_run', 'gl_tests_run',
                 'tab_capture_end2end_tests_run', 'telemetry_gpu_test_run']
  yield (
    api.test('gpu_tests') +
    props(
      mastername='tryserver.chromium.mac',
      buildername='mac_chromium_rel_ng',
    ) +
    api.platform.name('mac') +
    api.override_step_data(
        'pixel_test on Intel GPU on Mac (with patch)',
        api.json.canned_telemetry_gpu_output(passing=False, swarming=True)) +
    api.override_step_data(
        'pixel_test on Intel GPU on Mac (without patch)',
        api.json.canned_telemetry_gpu_output(passing=False, swarming=True)) +
    api.override_step_data('analyze',
                           api.json.output({'status': 'Found dependency',
                                            'targets': gpu_targets,
                                            'build_targets': gpu_targets}))
  )

  yield (
    api.test('telemetry_gpu_no_results') +
    props(
      mastername='tryserver.chromium.mac',
      buildername='mac_chromium_rel_ng',
    ) +
    api.platform.name('mac') +
    api.override_step_data('pixel_test on Intel GPU on Mac (with patch)',
                           api.raw_io.output_dir({'0/results.json': ''})) +
    api.override_step_data('analyze',
                           api.json.output({'status': 'Found dependency',
                                            'targets': gpu_targets,
                                            'build_targets': gpu_targets}))
  )

  yield (
    api.test('use_v8_patch_on_chromium_trybot') +
    props(buildername='win_chromium_rel_ng',
          mastername='tryserver.chromium.win',
          patch_project='v8') +
    api.platform.name('win')
  )
