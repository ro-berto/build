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
  'rietveld',
  'step',
  'step_history',
  'test_utils',
]


GTEST_TESTS = [
  # Small and medium tests. Sort alphabetically.
  'base_unittests',
  'cacheinvalidation_unittests',
  'cc_unittests',
  'chromedriver2_unittests',
  'components_unittests',
  'content_unittests',
  'crypto_unittests',
  'google_apis_unittests',
  'gpu_unittests',
  'ipc_tests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sql_unittests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',

  # Large tests. Sort alphabetically.
  'browser_tests',
  'content_browsertests',
  'interactive_ui_tests',
  'sync_integration_tests',
]


def GenSteps(api):
  class CheckdepsTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'checkdeps'

    @staticmethod
    def compile_targets():
      return []

    @staticmethod
    def run(suffix):
      return api.chromium.checkdeps(suffix, can_fail_build=False)

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

        p.step_text += api.test_utils.format_step_text([
            ['failures:', r.failures]
        ])

      args = [api.json.gtest_results()]

      if suffix == 'without patch':
        args.append('--gtest_filter=%s' % ':'.join(self.failures('with patch')))

      return api.chromium.runtests(self.name,
                                   args,
                                   xvfb=True,
                                   name=self._step_name(suffix),
                                   parallel=True,
                                   can_fail_build=False,
                                   followup_fn=followup_fn)

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
          api.path.checkout('chrome',
                            'test',
                            'nacl_test_injection',
                            'buildbot_nacl_integration.py'),
          args,
          can_fail_build=False)

    def failures(self, suffix):
      failures = api.step_history[self._step_name(suffix)].json.output
      return [f['raw_name'] for f in failures]


  api.chromium.set_config('chromium')
  api.chromium.apply_config('trybot_flavor')
  api.step.auto_resolve_conflicts = True

  tests = []
  tests.append(CheckdepsTest())
  tests.append(Deps2GitTest())
  for name in GTEST_TESTS:
    tests.append(GTestTest(name))
  tests.append(NaclIntegrationTest())

  yield (
    api.gclient.checkout(revert=True),
    api.rietveld.apply_issue(),
    api.chromium.runhooks(),
    api.chromium.compile(
        targets=list(
            api.itertools.chain(*[t.compile_targets() for t in tests]))),
  )

  # Do not run tests if the build is already in a failed state.
  if api.step_history.failed:
    return

  def deapply_patch_fn(failing_tests):
    yield (
      api.gclient.revert(),
      api.chromium.runhooks(),
    )
    compile_targets = api.itertools.chain(
        *[t.compile_targets() for t in failing_tests])
    if compile_targets:
      yield api.chromium.compile(targets=list(compile_targets))

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
  canned_deps2git = {
    True: [],
    False: ['https://chromium.googlesource.com/external/v8.git'],
  }
  canned_nacl = {
    True: [],
    False: [
      {
        'test_name': 'test_foo',
        'raw_name': 'test_foo',
        'errstr': 'baz',
      }
    ],
  }
  canned_test = api.json.canned_gtest_output
  def props(config='Release', git_mode=False):
    return api.properties.tryserver(
      build_config=config,
      GIT_MODE=git_mode,
    )

  for build_config in ['Release', 'Debug']:
    for plat in ('win', 'mac', 'linux'):
      for git_mode in True, False:
        suffix = '_git' if git_mode else ''
        name = '%s_%s%s' % (plat, build_config.lower(), suffix)
        test = (
          api.test(name) +
          props(build_config, git_mode) +
          api.platform.name(plat)
        )

        test += api.step_data('checkdeps (with patch)',
                              api.json.output(canned_checkdeps[True]))
        test += api.step_data('deps2git (with patch)',
                              api.json.output(canned_deps2git[True]))
        test += api.step_data('nacl_integration (with patch)',
                              api.json.output(canned_nacl[True]))
        for gtest_test in GTEST_TESTS:
          test += api.step_data(gtest_test + ' (with patch)',
                                canned_test(passing=True))
        yield test

  TEST_FAILURES = [
    (None, None),
    (None, 'base_unittests'),
    (None, 'net_unittests'),
    ('base_unittests', None),
    ('net_unittests', None),
    ('base_unittests', 'net_unittests'),
    ('base_unittests', 'nacl_integration'),
    (None, 'checkdeps'),
    ('checkdeps', None),
    ('checkdeps', 'base_unittests'),
    ('base_unittests', 'deps2git'),
  ]
  for (really_failing_test, spuriously_failing_test) in TEST_FAILURES:
    name = ('success' if not really_failing_test else
            'fail_%s' % really_failing_test)
    name += ('_success' if not spuriously_failing_test else
             '_fail_%s' % spuriously_failing_test)
    test = (
      api.test(name) +
      props() +
      api.platform.name('linux')
    )

    passing = 'checkdeps' not in (really_failing_test,
                                  spuriously_failing_test)
    test += api.step_data('checkdeps (with patch)',
                          api.json.output(canned_checkdeps[passing]))
    if not passing:
      test += api.step_data(
          'checkdeps (without patch)',
          api.json.output(
              canned_checkdeps[really_failing_test=='checkdeps']))

    passing = 'deps2git' not in (really_failing_test,
                                 spuriously_failing_test)
    test += api.step_data('deps2git (with patch)',
                          api.json.output(canned_deps2git[passing]))
    if not passing:
      test += api.step_data(
          'deps2git (without patch)',
          api.json.output(
              canned_deps2git[really_failing_test=='deps2git']))

    passing = 'nacl_integration' not in (really_failing_test,
                                         spuriously_failing_test)
    test += api.step_data('nacl_integration (with patch)',
                          api.json.output(canned_nacl[passing]))
    if not passing:
      test += api.step_data(
          'nacl_integration (without patch)',
          api.json.output(canned_nacl[really_failing_test=='nacl_integration']))

    for gtest_test in GTEST_TESTS:
      passing = gtest_test not in (really_failing_test,
                                   spuriously_failing_test)
      test += api.step_data(gtest_test + ' (with patch)',
                            canned_test(passing=passing))
    if really_failing_test and really_failing_test in GTEST_TESTS:
      test += api.step_data(really_failing_test + ' (without patch)',
                            canned_test(passing=True, minimal=True))
    if spuriously_failing_test and spuriously_failing_test in GTEST_TESTS:
      test += api.step_data(
          spuriously_failing_test + ' (without patch)',
          canned_test(passing=False, minimal=True))

    yield test

  for step in ('gclient revert', 'gclient runhooks', 'compile'):
    yield (
      api.test(step.replace(' ', '_') + '_failure') +
      props() +
      api.platform.name('win') +
      api.step_data(step, retcode=1)
    )
