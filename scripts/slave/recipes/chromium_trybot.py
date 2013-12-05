# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'raw_io',
  'rietveld',
  'step',
  'step_history',
]


GTEST_TESTS = [
  'base_unittests',
  'net_unittests',
]

NACL_INTEGRATION_TARGETS = [
  'chrome',
]

def followup_fn(step_result):
  r = step_result.json.gtest_results
  p = step_result.presentation

  if r.failures:
    p.step_text += '<br/>failures:<br/>'
    for test_fullname in r.failures:
      p.step_text += test_fullname + '<br/>'


def summarize_failures(new_failures):
  def summarize_failures_inner(step_result):
    p = step_result.presentation

    for executable_name, test_names in new_failures.iteritems():
      if test_names:
        p.step_text += '<br/>%s failures:<br/>' % executable_name
        for test_fullname in test_names:
          p.step_text += test_fullname + '<br/>'
  return summarize_failures_inner


def GTestsStep(api, test, suffix, additional_args=None):
  if additional_args is None:
    additional_args = []

  name = '%s (%s)' % (test, suffix)
  args = [api.json.gtest_results()] + additional_args
  return api.chromium.runtests(test,
                               args,
                               name=name,
                               parallel=True,
                               can_fail_build=False,
                               followup_fn=followup_fn)


def NaclIntegrationStep(api, suffix):
  name = 'nacl_integration (%s)' % suffix
  args = [
    '--mode', api.chromium.c.BUILD_CONFIG,
    '--json_build_results_output_file', api.json.output(),
  ]
  return api.python(
      name,
      api.path.checkout('chrome',
                        'test',
                        'nacl_test_injection',
                        'buildbot_nacl_integration.py'),
      args,
      can_fail_build=False)


def SummarizeTestResults(api, ignored_failures, new_failures):
  return api.python.inline(
    'gtest_tests',
    r"""
    import sys, json
    failures = json.load(open(sys.argv[1], 'rb'))

    success = True

    for executable_name, new_failures in failures['new'].iteritems():
      if new_failures:
        success = False
        print 'New failures (%s):' % executable_name
        print '\n'.join(sorted(new_failures))
    for executable_name, ignored_failures in failures['ignored'].iteritems():
      if ignored_failures:
        print 'Ignored failures (%s):' % executable_name
        print '\n'.join(sorted(ignored_failures))

    sys.exit(0 if success else 1)
    """,
    args=[
      api.json.input({
        'new': new_failures,
        'ignored': ignored_failures
      })
    ],
    followup_fn=summarize_failures(new_failures)
  )


def SummarizeCheckdepsResults(api, with_patch, without_patch):
  def results_to_set(results):
    result_set = set()
    for result in results:
      for violation in result['violations']:
        result_set.add((result['dependee_path'], violation['include_path']))
    return result_set
  ignored_failures = results_to_set(without_patch)
  new_failures = results_to_set(with_patch) - ignored_failures
  return api.python.inline(
    'checkdeps',
    r"""
    import sys, json
    failures = json.load(open(sys.argv[1], 'rb'))

    success = True

    if failures['new']:
      success = False
      print 'New failures:'
      for (dependee, include) in failures['new']:
        print '\t%s -> %s' % (dependee, include)

    if failures['ignored']:
      print 'Ignored failures:'
      for (dependee, include) in failures['ignored']:
        print '\t%s -> %s' % (dependee, include)

    sys.exit(0 if success else 1)
    """,
    args=[
      api.json.input({
        'new': list(new_failures),
        'ignored': list(ignored_failures),
      })
    ],
  )


def SummarizeDeps2GitResults(api, with_patch, without_patch):
  ignored_failures = set(without_patch)
  new_failures = set(with_patch) - ignored_failures
  return api.python.inline(
    'checkdeps',
    r"""
    import sys, json
    failures = json.load(open(sys.argv[1], 'rb'))

    success = True

    if failures['new']:
      success = False
      print 'New failures:'
      for url in failures['new']:
        print url

    if failures['ignored']:
      print 'Ignored failures:'
      for url in failures['ignored']:
        print url

    sys.exit(0 if success else 1)
    """,
    args=[
      api.json.input({
        'new': list(new_failures),
        'ignored': list(ignored_failures),
      })
    ],
  )


def SummarizeNaclIntegrationResults(api, with_patch, without_patch):
  def results_to_set(results):
    return set([result['raw_name'] for result in results])
  ignored_failures = results_to_set(without_patch)
  new_failures = results_to_set(with_patch) - ignored_failures
  return api.python.inline(
    'nacl_integration',
    r"""
    import sys, json
    failures = json.load(open(sys.argv[1], 'rb'))

    success = True

    if failures['new']:
      success = False
      print 'New failures:'
      for url in failures['new']:
        print url

    if failures['ignored']:
      print 'Ignored failures:'
      for url in failures['ignored']:
        print url

    sys.exit(0 if success else 1)
    """,
    args=[
      api.json.input({
        'new': list(new_failures),
        'ignored': list(ignored_failures),
      })
    ],
  )


def GenSteps(api):
  api.chromium.set_config('chromium')
  api.chromium.apply_config('trybot_flavor')
  api.step.auto_resolve_conflicts = True

  yield (
    api.gclient.checkout(revert=True),
    api.rietveld.apply_issue(),
    api.chromium.runhooks(),
    api.chromium.compile(targets=(GTEST_TESTS + NACL_INTEGRATION_TARGETS)),
  )

  # Do not run tests if the build is already in a failed state.
  if api.step_history.failed:
    return

  yield (
    api.chromium.checkdeps('with patch', can_fail_build=False),
    api.chromium.deps2git('with patch', can_fail_build=False),
    api.chromium.deps2submodules(),
  )

  with_patch = {}
  for test in GTEST_TESTS:
    yield GTestsStep(api, test, 'with patch')
    with_patch[test] = api.step_history.last_step().json.gtest_results

  gtest_retry_tests = []
  for test in GTEST_TESTS:
    if not with_patch[test].valid or with_patch[test].failures:
      gtest_retry_tests.append(test)

  yield NaclIntegrationStep(api, 'with patch')

  other_retry_tests = []

  if api.step_history['checkdeps (with patch)'].json.output == []:
    yield api.python.inline('checkdeps', 'print "ALL IS WELL"')
  else:
    other_retry_tests.append('checkdeps')

  if api.step_history['deps2git (with patch)'].json.output == []:
    yield api.python.inline('deps2git', 'print "ALL IS WELL"')
  else:
    other_retry_tests.append('deps2git')

  if not gtest_retry_tests:
    yield api.python.inline('gtest_tests', 'print "ALL IS WELL"')

  if api.step_history['nacl_integration (with patch)'].json.output == []:
    yield api.python.inline('nacl_integration', 'print "ALL IS WELL"')
  else:
    other_retry_tests.append('nacl_integration')

  if not gtest_retry_tests and not other_retry_tests:
    return

  yield (
    api.gclient.revert(),
    api.chromium.runhooks(),
  )

  if 'checkdeps' in other_retry_tests:
    yield api.chromium.checkdeps('without patch', can_fail_build=False)
    yield SummarizeCheckdepsResults(
      api,
      with_patch=api.step_history['checkdeps (with patch)'].json.output,
      without_patch=api.step_history['checkdeps (without patch)'].json.output
    )

  if 'deps2git' in other_retry_tests:
    yield api.chromium.deps2git('without patch', can_fail_build=False)
    yield SummarizeDeps2GitResults(
      api,
      with_patch=api.step_history['deps2git (with patch)'].json.output,
      without_patch=api.step_history['deps2git (without patch)'].json.output
    )

  if gtest_retry_tests:
    yield api.chromium.compile(targets=gtest_retry_tests)

    without_patch = {}
    for test in gtest_retry_tests:
      additional_args = [
          '--gtest_filter=%s' % ':'.join(with_patch[test].failures),
      ]
      yield GTestsStep(api,
                       test,
                       'without patch',
                       additional_args=additional_args)
      without_patch[test] = api.step_history.last_step().json.gtest_results

    ignored_failures = {}
    new_failures = {}
    for test in gtest_retry_tests:
      ignored_failures[test] = list(without_patch[test].failures)
      new_failures[test] = list(
          set(with_patch[test].failures) - set(ignored_failures[test]))

    yield SummarizeTestResults(api, ignored_failures, new_failures)

  if 'nacl_integration' in other_retry_tests:
    yield api.chromium.compile(targets=NACL_INTEGRATION_TARGETS)
    yield NaclIntegrationStep(api, 'without patch')

    yield SummarizeNaclIntegrationResults(
      api,
      with_patch=api.step_history[
          'nacl_integration (with patch)'].json.output,
      without_patch=api.step_history[
          'nacl_integration (without patch)'].json.output
    )


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
