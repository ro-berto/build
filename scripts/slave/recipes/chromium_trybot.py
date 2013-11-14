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


def GenSteps(api):
  api.chromium.set_config('chromium')
  api.chromium.apply_config('trybot_flavor')
  api.step.auto_resolve_conflicts = True

  yield (
    api.gclient.checkout(),
    api.rietveld.apply_issue(),
    api.chromium.runhooks(),
    api.chromium.compile(targets=GTEST_TESTS),
  )

  with_patch = {}
  for test in GTEST_TESTS:
    yield GTestsStep(api, test, 'with patch')
    with_patch[test] = api.step_history.last_step().json.gtest_results

  gtest_retry_tests = []
  for test in GTEST_TESTS:
    if not with_patch[test].valid or with_patch[test].failures:
      gtest_retry_tests.append(test)

  if not gtest_retry_tests:
    yield api.python.inline('gtest_tests', 'print "ALL IS WELL"')
    return

  yield (
    api.gclient.revert(),
    api.chromium.runhooks(),
    api.chromium.compile(targets=gtest_retry_tests),
  )

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


def GenTests(api):
  canned_test = api.json.canned_gtest_output
  def props(config='Release', git_mode=False):
    return api.properties.tryserver(
      build_config=config,
      GIT_MODE=git_mode,
    )

  for really_failing_test in [None, 'base_unittests', 'net_unittests']:
    for spuriously_failing_test in [None, 'base_unittests', 'net_unittests']:
      for build_config in ['Release', 'Debug']:
        for plat in ('win', 'mac', 'linux'):
          for git_mode in True, False:
            if (really_failing_test and
                spuriously_failing_test and
                really_failing_test == spuriously_failing_test):
              continue
            tag = ('success' if not really_failing_test else
                   'fail_%s' % really_failing_test)
            tag += ('_success' if not spuriously_failing_test else
                    '_fail_%s' % spuriously_failing_test)
            suffix = '_git' if git_mode else ''
            name = '%s_%s_%s%s' % (plat, tag, build_config.lower(), suffix)
            test = (
              api.test(name) +
              props(build_config, git_mode) +
              api.platform.name(plat)
            )
            for gtest_test in GTEST_TESTS:
              passing = gtest_test not in (really_failing_test,
                                           spuriously_failing_test)
              test += api.step_data(gtest_test + ' (with patch)',
                                    canned_test(passing=passing))
            if really_failing_test:
              test += api.step_data(really_failing_test + ' (without patch)',
                                    canned_test(passing=True, minimal=True))
            if spuriously_failing_test:
              test += api.step_data(
                  spuriously_failing_test + ' (without patch)',
                  canned_test(passing=False, minimal=True))

            yield test
