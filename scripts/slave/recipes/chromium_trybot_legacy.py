# Copyright 2015 The Chromium Authors. All rights reserved.
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
      'linux_arm': {
        'GYP_DEFINES': {
          'arm_float_abi': 'hard',
          'test_isolation_mode': 'archive',
        },
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': True,
        'exclude_compile_all': True,
        'testing': {
          'platform': 'linux',
          'test_spec_file': 'chromium_arm.json',
        },
        'use_isolate': True,
      },
      'linux_chromium_trusty_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_trusty_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_trusty32_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_trusty32_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win_chromium_x64_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win8_chromium_dbg': {
        'add_telemetry_tests': False,
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
          'test_spec_file': 'chromium_win8_trybot.json',
        },
        'swarming_dimensions': {
          'os': 'Windows-8-SP0',
        },
      },
      'win8_chromium_rel': {
        'add_telemetry_tests': False,
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
          'test_spec_file': 'chromium_win8_trybot.json',
        },
        'swarming_dimensions': {
          'os': 'Windows-8-SP0',
        },
      },
    },
  },
})


def get_test_names(tests):
  """Returns the names of each of the tests in |tests|."""
  return [test.name for test in tests]


def filter_tests(possible_tests, needed_tests):
  """Returns a list of all the tests in |possible_tests| whose name is in
  |needed_tests|."""
  result = []
  for test in possible_tests:
    if test.name in needed_tests:
      result.append(test)
  return result


def tests_in_compile_targets(api, compile_targets, tests):
  """Returns the tests in |tests| that have at least one of their compile
  targets in |compile_targets|."""
  # The target all builds everything.
  if 'all' in compile_targets:
    return tests

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


def find_test_named(test_name, tests):
  """Returns a list with all tests whose name matches |test_name|."""
  return [test for test in tests if test.name == test_name]


def _RunStepsInternal(api):
  def parse_test_spec(test_spec, should_use_test):
    """Returns a list of tests to run and additional targets to compile.

    Uses 'should_use_test' callback to figure out what tests should be skipped.

    Returns tuple (compile_targets, gtest_tests) where
      gtest_tests is a list of GTestTest
    """
    compile_targets = []
    gtest_tests_spec = []
    if isinstance(test_spec, dict):
      compile_targets = test_spec.get('compile_targets', [])
      gtest_tests_spec = test_spec.get('gtest_tests', [])
    else:
      # TODO(phajdan.jr): Convert test step data and remove this.
      gtest_tests_spec = test_spec

    gtest_tests = []
    for test in gtest_tests_spec:
      test_name = None
      test_dict = None

      # Read test_dict for the test, it defines where test can run.
      if isinstance(test, unicode):
        test_name = test.encode('utf-8')
        test_dict = {}
      elif isinstance(test, dict):
        if 'test' not in test:  # pragma: no cover
          raise ValueError('Invalid entry in test spec: %r' % test)
        test_name = test['test'].encode('utf-8')
        test_dict = test
      else:  # pragma: no cover
        raise ValueError('Unrecognized entry in test spec: %r' % test)

      # Should skip it completely?
      if not test_name or not should_use_test(test_dict):
        continue

      test_args = test_dict.get('args')
      if isinstance(test_args, basestring):
        test_args = [test_args]

      test = api.chromium_tests.steps.GTestTest(test_name, test_args)
      assert not test.uses_swarming

      gtest_tests.append(test)

    return compile_targets, gtest_tests

  def get_bot_config(mastername, buildername):
    master_dict = BUILDERS.get(mastername, {})
    return master_dict.get('builders', {}).get(buildername)

  def get_test_spec(mastername, buildername, name='read test spec',
                    step_test_data=None):
    bot_config = get_bot_config(mastername, buildername)

    test_spec_file = bot_config['testing'].get('test_spec_file',
                                               'chromium_trybot.json')
    test_spec_path = api.path.join('testing', 'buildbot', test_spec_file)
    if not step_test_data:
      step_test_data = lambda: api.json.test_api.output([
        'base_unittests',
        {
          'test': 'mojo_common_unittests',
          'platforms': ['linux', 'mac'],
        },
        {
          'test': 'sandbox_linux_unittests',
          'platforms': ['linux'],
          'chromium_configs': [
            'chromium_chromeos',
            'chromium_chromeos_clang',
            'chromium_chromeos_ozone',
          ],
          'args': ['--test-launcher-print-test-stdio=always'],
        },
        {
          'test': 'browser_tests',
          'exclude_builders': [
              'tryserver.chromium.linux:linux_chromium_trusty_rel',
          ],
        },
      ])
    step_result = api.json.read(
        name,
        api.path['checkout'].join(test_spec_path),
        step_test_data=step_test_data
    )
    step_result.presentation.step_text = 'path: %s' % test_spec_path
    return step_result.json.output

  def compile_and_return_tests(mastername, buildername):
    bot_config = get_bot_config(mastername, buildername)
    assert bot_config, (
        'Unrecognized builder name %r for master %r.' % (
            buildername, mastername))

    # Make sure tests and the recipe specify correct and matching platform.
    assert api.platform.name == bot_config.get('testing', {}).get('platform')

    api.chromium.set_config(bot_config['chromium_config'],
                            **bot_config.get('chromium_config_kwargs', {}))
    # Settings GYP_DEFINES explicitly because chromium config constructor does
    # not support that.
    api.chromium.c.gyp_env.GYP_DEFINES.update(bot_config.get('GYP_DEFINES', {}))
    if bot_config['compile_only']:
      api.chromium.c.gyp_env.GYP_DEFINES['fastbuild'] = 2
    api.chromium.apply_config('trybot_flavor')
    api.gclient.set_config('chromium')

    bot_update_step = api.bot_update.ensure_checkout(force=True)

    test_spec = get_test_spec(mastername, buildername)

    def should_use_test(test):
      """Given a test dict from test spec returns True or False."""
      if 'platforms' in test:
        if api.platform.name not in test['platforms']:
          return False
      if 'chromium_configs' in test:
        if bot_config['chromium_config'] not in test['chromium_configs']:
          return False
      if 'exclude_builders' in test:
        if '%s:%s' % (mastername, buildername) in test['exclude_builders']:
          return False
      return True

    # Parse test spec file into list of Test instances.
    compile_targets, gtest_tests = parse_test_spec(
        test_spec,
        should_use_test)
    compile_targets.extend(bot_config.get('compile_targets', []))
    # TODO(phajdan.jr): Also compile 'all' on win, http://crbug.com/368831 .
    # Disabled for now because it takes too long and/or fails on Windows.
    if not api.platform.is_win and not bot_config.get('exclude_compile_all'):
      compile_targets = ['all'] + compile_targets

    scripts_compile_targets = \
        api.chromium_tests.get_compile_targets_for_scripts().json.output

    # Tests that are only run if their compile_targets are going to be built.
    conditional_tests = []
    if bot_config.get('add_nacl_integration_tests', True):
      conditional_tests += [
          api.chromium_tests.steps.ScriptTest(
              'nacl_integration', 'nacl_integration.py',
              scripts_compile_targets),
      ]
    if bot_config.get('add_telemetry_tests', True):
      conditional_tests += [
          api.chromium_tests.steps.ScriptTest(
              'telemetry_unittests', 'telemetry_unittests.py',
              scripts_compile_targets),
          api.chromium_tests.steps.ScriptTest(
              'telemetry_perf_unittests', 'telemetry_perf_unittests.py',
              scripts_compile_targets),
      ]

    # See if the patch needs to compile on the current platform.
    if isinstance(test_spec, dict):
      analyze_config_file = bot_config['testing'].get('analyze_config_file',
                                         'trybot_analyze_config.json')
      requires_compile, matching_exes, compile_targets = \
          api.chromium_tests.analyze(
              api.tryserver.get_files_affected_by_patch(),
              get_test_names(gtest_tests) +
                  all_compile_targets(api, conditional_tests),
              compile_targets,
              analyze_config_file)

      if not requires_compile:
        return [], bot_update_step

      gtest_tests = filter_tests(gtest_tests, matching_exes)

    tests = []

    conditional_tests = tests_in_compile_targets(
        api, compile_targets, conditional_tests)
    tests.extend(find_test_named('telemetry_unittests', conditional_tests))
    tests.extend(find_test_named('telemetry_perf_unittests', conditional_tests))
    tests.extend(gtest_tests)
    tests.extend(find_test_named('nacl_integration', conditional_tests))

    if api.platform.is_win:
      tests.append(api.chromium_tests.steps.MiniInstallerTest())

    # Swarming uses Isolate to transfer files to swarming bots.
    # set_isolate_environment modifies GYP_DEFINES to enable test isolation.
    if bot_config.get('use_isolate'):
      api.isolate.set_isolate_environment(api.chromium.c)

    try:
      api.chromium.runhooks(name='runhooks (with patch)')
    except api.step.StepFailure:
      # As part of deapplying patch we call runhooks without the patch.
      api.chromium_tests.deapply_patch(bot_update_step)
      raise

    if bot_config.get('use_isolate'):
      api.isolate.clean_isolated_files(api.chromium.output_dir)

    compile_targets.extend(api.itertools.chain(
        *[t.compile_targets(api) for t in tests]))
    # Remove duplicate targets.
    compile_targets = sorted(set(compile_targets))
    try:
      api.chromium.compile(compile_targets, name='compile (with patch)')
    except api.step.StepFailure:
      api.chromium_tests.deapply_patch(bot_update_step)
      api.chromium.compile(
          compile_targets, name='compile (without patch)')
      raise

    if bot_config.get('use_isolate'):
      # Remove the build metadata from the binaries.
      api.isolate.remove_build_metadata()
      # Isolate all prepared targets, will look for *.isolated.gen.json files.
      api.isolate.isolate_tests(api.chromium.output_dir, verbose=True)

    if bot_config['compile_only']:
      tests = []

    return tests, bot_update_step

  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  api.chromium_tests.configure_swarming('chromium', precommit=True)

  tests, bot_update_step = compile_and_return_tests(
      mastername, buildername)

  def deapply_patch_fn(failing_tests):
    api.chromium_tests.deapply_patch(bot_update_step)
    compile_targets = sorted(list(set(api.itertools.chain(
        *[t.compile_targets(api) for t in failing_tests]))))
    if compile_targets:
      api.chromium.compile(
          compile_targets, name='compile (without patch)')

  return api.test_utils.determine_new_failures(api, tests, deapply_patch_fn)


def RunSteps(api):
  with api.tryserver.set_failure_hash():
    return _RunStepsInternal(api)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.test_utils.canned_gtest_output

  def props(config='Release', mastername='tryserver.chromium.linux',
            buildername='linux_chromium_trusty_rel', extra_swarmed_tests=None,
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
    api.test('compile_failure_without_patch_with_test') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': ['base_unittests'],
      })
    ) +
    suppress_analyze() +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('compile (without patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_without_patch_with_test_swarming') +
    props(extra_swarmed_tests=['base_unittests']) +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {
              'can_use_on_swarming_builders': True,
            },
          },
        ],
      })
    ) +
    suppress_analyze() +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('compile (without patch)', retcode=1)
  )

  yield (
    api.test('base_unittests_failure_swarming') +
    props(extra_swarmed_tests=['base_unittests']) +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {
              'can_use_on_swarming_builders': True,
            },
          },
        ],
      })
    ) +
    suppress_analyze() +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False))
  )

  for step in ('bot_update', 'gclient runhooks (with patch)'):
    yield (
      api.test(_sanitize_nonalpha(step) + '_failure') +
      props(buildername='linux_chromium_trusty_rel',
            mastername='tryserver.chromium.linux') +
      api.platform.name('linux') +
      api.step_data(step, retcode=1)
    )

  yield (
    api.test('runhooks_failure') +
    props(buildername='win8_chromium_rel',
          mastername='tryserver.chromium.win') +
    api.platform.name('win') +
    api.step_data('gclient runhooks (with patch)', retcode=1) +
    api.step_data('gclient runhooks (without patch)', retcode=1)
  )

  yield (
    api.test('compile_failure') +
    props(buildername='linux_chromium_trusty_rel',
          mastername='tryserver.chromium.linux') +
    api.platform.name('linux') +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_without_patch') +
    props(buildername='linux_chromium_trusty_rel',
          mastername='tryserver.chromium.linux') +
    api.platform.name('linux') +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (without patch)', retcode=1)
  )

  yield (
    api.test('arm') +
    props(buildername='linux_arm', requester='commit-bot@chromium.org',
          blamelist='joe@chromium.org', blamelist_real=['joe@chromium.org']) +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
        'compile_targets': ['browser_tests_run'],
        'gtest_tests': [
          {
            'test': 'browser_tests',
            'args': '--gtest-filter: *NaCl*.*',
          }, {
            'test': 'base_tests',
            'args': ['--gtest-filter: *NaCl*.*'],
          },
        ],
      })
    )
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
    props(buildername='linux_chromium_trusty_rel', requester='joe@chromium.org',
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
    props(buildername='linux_chromium_trusty_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    )
  )

  # Verifies analyze doesn't skip projects other than src.
  yield (
    api.test('analyze_for_non_src_project') +
    props(buildername='linux_chromium_trusty_rel') +
    props(patch_project='blink') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    )
  )

  # This should result in a compile.
  yield (
    api.test('compile_because_of_analyze_matching_exclusion') +
    props(buildername='linux_chromium_trusty_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      'gtest_tests': ['base_unittests'],
    })) +
    suppress_analyze()
  )

  # This should result in a compile.
  yield (
    api.test('compile_because_of_analyze') +
    props(buildername='linux_chromium_trusty_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency', 'targets': ['foo'],
                       'build_targets': ['foo']}))
  )

  yield (
    api.test('compile_because_of_analyze_with_filtered_tests_no_builder') +
    props(buildername='linux_chromium_trusty_rel') +
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
    props(buildername='linux_chromium_trusty_rel') +
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
    props(buildername='linux_chromium_trusty_rel') +
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
    props(buildername='linux_chromium_trusty_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'compile_targets': ['base_unittests'],
        'gtest_tests': [
          {
            'test': 'browser_tests',
            'args': '--gtest-filter: *NaCl*.*',
          }, {
            'test': 'base_tests',
            'args': ['--gtest-filter: *NaCl*.*'],
          },
        ],
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
    props(buildername='linux_chromium_trusty_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'compile_targets': ['base_unittests'],
        'gtest_tests': [
          {
            'test': 'browser_tests',
            'args': '--gtest-filter: *NaCl*.*',
          }, {
            'test': 'base_tests',
            'args': ['--gtest-filter: *NaCl*.*'],
          },
        ],
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'invalid_targets': ['invalid target', 'another one']}))
  )
