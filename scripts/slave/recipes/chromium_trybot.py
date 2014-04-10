# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'itertools',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'raw_io',
  'step',
  'step_history',
  'test_utils',
  'tryserver',
]


# Make it easy to change how different configurations of this recipe
# work without making buildbot-side changes. Each builder will only
# have a tag specifying a config/flavor (adding, removing or changing
# builders requires a buildbot-side change anyway), but we can change
# everything about what that config means in the recipe.
RECIPE_CONFIGS = {
  # Default config.
  None: {
    'chromium_config': 'chromium',
    'compile_only': False,
  },
  'asan': {
    'chromium_config': 'chromium_asan',
    'compile_only': False,
  },
  'chromeos': {
    'chromium_config': 'chromium_chromeos',
    'compile_only': False,
  },
  'chromeos_asan': {
    'chromium_config': 'chromium_chromeos_asan',
    'compile_only': False,
  },
  'chromeos_clang': {
    'chromium_config': 'chromium_chromeos_clang',
    'compile_only': True,
  },
  'clang': {
    'chromium_config': 'chromium_clang',
    'compile_only': True,
  },
  'compile': {
    'chromium_config': 'chromium',
    'compile_only': True,
  },
}


def GenSteps(api):
  class CheckdepsTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'checkdeps'

    @staticmethod
    def compile_targets():
      return []

    @staticmethod
    def run(suffix):
      return api.chromium.checkdeps(suffix, can_fail_build=False)

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      results = api.step_history[self._step_name(suffix)].json.output
      result_set = set()
      for result in results:
        for violation in result['violations']:
          result_set.add((result['dependee_path'], violation['include_path']))
      return ['%s: %s' % (r[0], r[1]) for r in result_set]


  class Deps2GitTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'deps2git'

    @staticmethod
    def compile_targets():
      return []

    @staticmethod
    def run(suffix):
      yield (
        api.chromium.deps2git(suffix, can_fail_build=False),
        api.chromium.deps2submodules()
      )

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output


  class GTestTest(api.test_utils.Test):
    def __init__(self, name):
      api.test_utils.Test.__init__(self)
      self._name = name

    @property
    def name(self):
      return self._name

    def compile_targets(self):
      return [self.name]

    def run(self, suffix):
      def followup_fn(step_result):
        r = step_result.json.gtest_results
        p = step_result.presentation

        if r.valid:
          p.step_text += api.test_utils.format_step_text([
              ['failures:', r.failures]
          ])

      args = []

      if suffix == 'without patch':
        args.append(api.chromium.test_launcher_filter(
                        self.failures('with patch')))

      return api.chromium.runtest(
          self.name,
          args,
          annotate='gtest',
          test_launcher_summary_output=api.json.gtest_results(
              add_json_log=False),
          xvfb=True,
          name=self._step_name(suffix),
          parallel=True,
          can_fail_build=False,
          followup_fn=followup_fn,
          step_test_data=lambda: api.json.test_api.canned_gtest_output(True))

    def has_valid_results(self, suffix):
      step_name = self._step_name(suffix)
      gtest_results = api.step_history[step_name].json.gtest_results
      if not gtest_results.valid:  # pragma: no cover
        return False
      global_tags = gtest_results.raw.get('global_tags', [])
      return 'UNRELIABLE_RESULTS' not in global_tags


    def failures(self, suffix):
      step_name = self._step_name(suffix)
      return api.step_history[step_name].json.gtest_results.failures


  class NaclIntegrationTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'nacl_integration'

    @staticmethod
    def compile_targets():
      return ['chrome']

    def run(self, suffix):
      args = [
        '--mode', api.chromium.c.BUILD_CONFIG,
        '--json_build_results_output_file', api.json.output(),
      ]
      return api.python(
          self._step_name(suffix),
          api.path['checkout'].join('chrome',
                            'test',
                            'nacl_test_injection',
                            'buildbot_nacl_integration.py'),
          args,
          can_fail_build=False,
          step_test_data=lambda: api.m.json.test_api.output([]))

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      failures = api.step_history[self._step_name(suffix)].json.output
      return [f['raw_name'] for f in failures]

  recipe_config_name = api.properties.get('recipe_config')
  if recipe_config_name not in RECIPE_CONFIGS:  # pragma: no cover
    raise ValueError('Unsupported recipe_config "%s"' % recipe_config_name)
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.chromium.set_config(recipe_config['chromium_config'])
  api.chromium.apply_config('trybot_flavor')
  api.gclient.set_config('chromium')
  api.step.auto_resolve_conflicts = True

  yield api.gclient.checkout(
      revert=True, can_fail_build=False, abort_on_failure=False)
  for step in api.step_history.values():
    if step.retcode != 0:
      if api.platform.is_win:
        yield api.chromium.taskkill()
      yield (
        api.path.rmcontents('slave build directory', api.path['slave_build']),
        api.gclient.checkout(revert=False),
      )
      break

  yield (
    api.tryserver.maybe_apply_issue(),
    api.json.read(
      'read test spec',
      api.path['checkout'].join('testing', 'buildbot', 'chromium_trybot.json'),
      step_test_data=lambda: api.json.test_api.output([
        'base_unittests',
        {'test': 'mojo_common_unittests', 'platforms': ['linux', 'mac']},
      ])),
  )

  yield api.chromium.runhooks(abort_on_failure=False, can_fail_build=False)
  if api.step_history.last_step().retcode != 0:
    # Before removing the checkout directory try just using LKCR.
    api.gclient.set_config('chromium_lkcr')

    # Since we're likely to switch to an earlier revision, revert the patch,
    # sync with the new config, and apply issue again.
    yield api.gclient.checkout(revert=True)
    yield api.tryserver.maybe_apply_issue()

    yield api.chromium.runhooks(abort_on_failure=False, can_fail_build=False)
    if api.step_history.last_step().retcode != 0:
      if api.platform.is_win:
        yield api.chromium.taskkill()
      yield (
        api.path.rmcontents('slave build directory', api.path['slave_build']),
        api.gclient.checkout(revert=False),
        api.tryserver.maybe_apply_issue(),
        api.chromium.runhooks(),
      )

  # TODO(dpranke): crbug.com/353690. Remove the gn-specific steps from this
  # recipe and stand up a dedicated GN bot when the GN steps take up enough
  # resources to be worth it. For now, we run GN and generate files into a new
  # Debug_gn / Release_gn dir, and then run a compile in that dir.
  gn_build_config_dir = str(api.chromium.c.BUILD_CONFIG) + '_gn'
  gn_output_arg = '//out/' + gn_build_config_dir
  gn_output_dir = api.path['checkout'].join('out', gn_build_config_dir)
  should_run_gn = api.properties.get('buildername') in ('linux_chromium',
                                                        'linux_chromium_rel')

  gtest_tests = []
  test_spec = api.step_history['read test spec'].json.output
  for test in test_spec:
    test_name = None
    if isinstance(test, unicode):
      test_name = test.encode('utf-8')
    elif isinstance(test, dict):
      if 'platforms' in test:
        if api.platform.name not in test['platforms']:
          continue

      if 'test' not in test:  # pragma: no cover
        raise ValueError('Invalid entry in test spec: %r' % test)

      test_name = test['test'].encode('utf-8')
    else:  # pragma: no cover
      raise ValueError('Unrecognized entry in test spec: %r' % test)

    if test_name and test_name not in gtest_tests:
      gtest_tests.append(test_name)

  tests = []
  tests.append(CheckdepsTest())
  tests.append(Deps2GitTest())
  for test in gtest_tests:
    tests.append(GTestTest(test))
  tests.append(NaclIntegrationTest())

  compile_targets = list(api.itertools.chain(
                             *[t.compile_targets() for t in tests]))
  yield api.chromium.compile(compile_targets,
                             name='compile (with patch)',
                             abort_on_failure=False,
                             can_fail_build=False)
  retry_at_lkcr = api.step_history['compile (with patch)'].retcode != 0

  if not retry_at_lkcr and should_run_gn:
    yield api.chromium.run_gn(gn_output_arg, abort_on_failure=False,
                              can_fail_build=False)
    yield api.chromium.compile_with_ninja('compile (gn with patch)',
                                          gn_output_dir,
                                          abort_on_failure=False,
                                          can_fail_build=False)
    retry_at_lkcr = (api.step_history['gn'].retcode != 0 or
                     api.step_history['compile (gn with patch)'].retcode != 0)

  if retry_at_lkcr:
    # Only use LKCR when compile fails. Note that requested specific revision
    # can still override this.
    api.gclient.set_config('chromium_lkcr')

    # Since we're likely to switch to an earlier revision, revert the patch,
    # sync with the new config, and apply issue again.
    yield api.gclient.checkout(revert=True)
    yield api.tryserver.maybe_apply_issue()

    yield api.chromium.compile(compile_targets,
                               name='compile (with patch, lkcr, clobber)',
                               force_clobber=True,
                               abort_on_failure=False,
                               can_fail_build=False)
    if api.step_history['compile (with patch, lkcr, clobber)'].retcode != 0:
      if api.platform.is_win:
        yield api.chromium.taskkill()
      yield (
        api.path.rmcontents('slave build directory', api.path['slave_build']),
        api.gclient.checkout(revert=False),
        api.tryserver.maybe_apply_issue(),
        api.chromium.runhooks(),
        api.chromium.compile(compile_targets,
                             name='compile (with patch, lkcr, clobber, nuke)',
                             force_clobber=True)
      )

    if should_run_gn:
      yield api.path.makedirs('slave gn build directory', gn_output_dir)
      yield api.path.rmcontents('slave gn build directory', gn_output_dir)
      yield api.chromium.run_gn(gn_output_arg)
      yield api.chromium.compile_with_ninja(
          'compile (gn with patch, lkcr, clobber)', gn_output_dir)

  # Do not run tests if the build is already in a failed state.
  if api.step_history.failed:
    return

  if recipe_config['compile_only']:
    return

  # TODO(dpranke): crbug.com/353690. It would be good to run gn_unittests
  # out of the gn build dir, but we can't use runtest()
  # because of the different output directory; this means
  # we don't get annotations and don't get retry of the tests for free :( .

  # TODO(phajdan.jr): Make it possible to retry telemetry tests (add JSON).
  yield (
    api.chromium.run_telemetry_unittests(),
    api.chromium.run_telemetry_perf_unittests(),
  )

  def deapply_patch_fn(failing_tests):
    yield (
      api.gclient.revert(always_run=True),
      api.chromium.runhooks(always_run=True),
    )
    compile_targets = list(api.itertools.chain(
                               *[t.compile_targets() for t in failing_tests]))
    if compile_targets:
      yield api.chromium.compile(compile_targets,
                                 name='compile (without patch)',
                                 abort_on_failure=False,
                                 can_fail_build=False,
                                 always_run=True)
      if api.step_history['compile (without patch)'].retcode != 0:
        yield api.chromium.compile(compile_targets,
                                   name='compile (without patch, clobber)',
                                   force_clobber=True,
                                   always_run=True)

  yield api.test_utils.determine_new_failures(tests, deapply_patch_fn)


def GenTests(api):
  canned_checkdeps = {
    True: [],
    False: [
      {
        'dependee_path': '/path/to/dependee',
        'violations': [
          { 'include_path': '/path/to/include', },
        ],
      },
    ],
  }
  canned_test = api.json.canned_gtest_output
  def props(config='Release', **kwargs):
    kwargs.setdefault('revision', None)
    return api.properties.tryserver(
      build_config=config,
      **kwargs
    )

  for build_config in ['Release', 'Debug']:
    for plat in ('win', 'mac', 'linux'):
      name = '%s_%s' % (plat, build_config.lower())
      yield (
        api.test(name) +
        props(build_config) +
        api.platform.name(plat)
      )

  # While not strictly required for coverage, record expectations for each
  # of the configs so we can see when and how they change.
  for config in RECIPE_CONFIGS:
    if config:
      yield (
        api.test(config) +
        props(recipe_config=config) +
        api.platform.name('linux')
      )

  # It is important that even when steps related to deapplying the patch
  # fail, we either print the summary for all retried steps or do no
  # retries at all.
  yield (
    api.test('persistent_failure_and_runhooks_2_fail_test') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('base_unittests (without patch)',
                           canned_test(passing=False)) +
    api.step_data('gclient runhooks (2)', retcode=1)
  )

  yield (
    api.test('invalid_json_without_patch') +
    props() +
    api.platform.name('win') +
    api.override_step_data('checkdeps (with patch)',
                           api.json.output(canned_checkdeps[False])) +
    api.override_step_data('checkdeps (without patch)',
                           api.json.output(None))
  )

  for step in ('gclient revert', 'gclient runhooks'):
    yield (
      api.test(step.replace(' ', '_') + '_failure') +
      props() +
      api.platform.name('win') +
      api.step_data(step, retcode=1)
    )

  yield (
    api.test('gclient_revert_failure_linux') +
    props() +
    api.platform.name('linux') +
    api.step_data('gclient runhooks', retcode=1) +
    api.step_data('gclient runhooks (2)', retcode=1) +
    api.step_data('gclient runhooks (3)', retcode=1)
  )

  yield (
    api.test('gclient_revert_failure_win') +
    props() +
    api.platform.name('win') +
    api.step_data('gclient runhooks', retcode=1) +
    api.step_data('gclient runhooks (2)', retcode=1) +
    api.step_data('gclient runhooks (3)', retcode=1)
  )

  yield (
    api.test('gclient_sync_no_data') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('gclient sync', api.json.output(None))
  )

  yield (
    api.test('gclient_revert_nuke') +
    props() +
    api.platform.name('linux') +
    api.step_data('gclient revert', retcode=1)
  )

  yield (
    api.test('compile_failure') +
    props() +
    api.platform.name('win') +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber, nuke)', retcode=1)
  )

  yield (
    api.test('compile_failure_linux') +
    props() +
    api.platform.name('linux') +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber, nuke)', retcode=1)
  )

  yield (
    api.test('deapply_compile_failure_linux') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.step_data('compile (without patch)', retcode=1)
  )

  # TODO(dpranke): crbug.com/353690.
  # Remove this when we make GN a standalone recipe.
  yield (
    api.test('unittest_should_run_gn') +
    api.properties.tryserver(buildername='linux_chromium',
                             build_config='Debug') +
    api.platform.name('linux') +
    api.step_data('compile (gn with patch)')
  )

  yield (
    api.test('unittest_should_run_gn_compile_failure') +
    api.properties.tryserver(buildername='linux_chromium',
                             build_config='Debug') +
    api.platform.name('linux') +
    api.step_data('compile (gn with patch)', retcode=1)
  )
