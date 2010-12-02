#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A buildbot command for running and interpreting GTest tests."""

import re
from buildbot.steps import shell
from buildbot.status import builder
from buildbot.process import buildstep

class TestObserver(buildstep.LogLineObserver):
  """This class knows how to understand GTest test output."""
  # TestAbbrFromTestID needs to be a member function.
  # pylint: disable=R0201

  def __init__(self):
    buildstep.LogLineObserver.__init__(self)

    # State tracking for log parsing
    self._current_test = ''
    self._failure_description = []

    # Line number currently being processed.
    self._line_number = 0

    # List of parsing errors, as human-readable strings.
    self.internal_error_lines = []

    # Tests are stored here as 'test.name': (status, [description]).
    # The status should be one of ('started', 'OK', 'failed', 'timeout'). The
    # description is a list of lines detailing the test's error, as reported
    # in the log.
    self._test_status = {}

    # This may be either text or a number. It will be used in the phrase
    # '%s disabled' or '%s flaky' on the waterfall display.
    self.disabled_tests = 0
    self.flaky_tests = 0

    # Regular expressions for parsing GTest logs. Test names look like
    #   SomeTestCase.SomeTest
    #   SomeName/SomeTestCase.SomeTest/1
    # This regexp also matches SomeName.SomeTest/1, which should be harmless.
    test_name_regexp = r'((\w+/)?\w+\.\w+(/\d+)?)'
    self._test_start   = re.compile('\[\s+RUN\s+\] ' + test_name_regexp)
    self._test_ok      = re.compile('\[\s+OK\s+\] ' + test_name_regexp)
    self._test_fail    = re.compile('\[\s+FAILED\s+\] ' + test_name_regexp)
    self._test_timeout = re.compile(
        'Test timeout \([0-9]+ ms\) exceeded for ' + test_name_regexp)
    self._disabled     = re.compile('  YOU HAVE (\d+) DISABLED TEST')
    self._flaky        = re.compile('  YOU HAVE (\d+) FLAKY TEST')

    self._builder_name_re = re.compile('\[Running on builder: "([^"]*)"')
    self.builder_name = ''

  def _StatusOfTest(self, test):
    """Returns the status code for the given test, or 'not known'."""
    test_status = self._test_status.get(test, ('not known', []))
    return test_status[0]

  def _TestsByStatus(self, status, include_fails, include_flaky):
    """Returns list of tests with the given status.

    Args:
      include_fails: If False, tests containing 'FAILS_' anywhere in their
          names will be excluded from the list.
      include_flaky: If False, tests containing 'FLAKY_' anywhere in their
          names will be excluded from the list.
    """
    test_list = [x[0] for x in self._test_status.items()
                 if self._StatusOfTest(x[0]) == status]

    if not include_fails:
      test_list = [x for x in test_list if x.find('FAILS_') == -1]
    if not include_flaky:
      test_list = [x for x in test_list if x.find('FLAKY_') == -1]

    return test_list

  def _RecordError(self, line, reason):
    """Record a log line that produced a parsing error.

    Args:
      line: text of the line at which the error occurred
      reason: a string describing the error
    """
    self.internal_error_lines.append("%s: %s [%s]" %
                                     (self._line_number, line.strip(), reason))

  def RunningTests(self):
    """Returns list of tests that appear to be currently running."""
    return self._TestsByStatus('started', True, True)

  def FailedTests(self, include_fails=False, include_flaky=False):
    """Returns list of tests that failed, timed out, or didn't finish
    (crashed).

    This list will be incorrect until the complete log has been processed,
    because it will show currently running tests as having failed.

    Args:
      include_fails: If true, all failing tests with FAILS_ in their names will
          be included. Otherwise, they will only be included if they crashed.
      include_flaky: If true, all failing tests with FLAKY_ in their names will
          be included. Otherwise, they will only be included if they crashed.

    """
    return (self._TestsByStatus('failed', include_fails, include_flaky) +
            self._TestsByStatus('timeout', include_fails, include_flaky) +
            self.RunningTests())

  def FailureDescription(self, test):
    """Returns a list containing the failure description for the given test.

    If the test didn't fail or timeout, returns [].
    """
    test_status = self._test_status.get(test, ('', []))
    return ["%s: " % test] + test_status[1]

  def outLineReceived(self, line):
    """This is called once with each line of the test log."""

    # Track line number for error messages.
    self._line_number += 1

    if not self.builder_name:
      results = self._builder_name_re.search(line)
      if results:
        self.builder_name = results.group(1)

    # Is it a line reporting disabled tests?
    results = self._disabled.search(line)
    if results:
      try:
        disabled = int(results.group(1))
      except ValueError:
        disabled = 0
      if disabled > 0 and isinstance(self.disabled_tests, int):
        self.disabled_tests += disabled
      else:
        # If we can't parse the line, at least give a heads-up. This is a
        # safety net for a case that shouldn't happen but isn't a fatal error.
        self.disabled_tests = 'some'
      return

    # Is it a line reporting flaky tests?
    results = self._flaky.search(line)
    if results:
      try:
        flaky = int(results.group(1))
      except ValueError:
        flaky = 0
      if flaky > 0 and isinstance(self.flaky_tests, int):
        self.flaky_tests = flaky
      else:
        # If we can't parse the line, at least give a heads-up. This is a
        # safety net for a case that shouldn't happen but isn't a fatal error.
        self.flaky_tests = 'some'
      return

    # Is it the start of a test?
    results = self._test_start.search(line)
    if results:
      test_name = results.group(1)
      if test_name in self._test_status:
        self._RecordError(line, 'test started more than once')
      self._test_status[test_name] = ('started', ['Did not complete.'])
      self._current_test = test_name
      self._failure_description = []
      return

    # Is it a test success line?
    results = self._test_ok.search(line)
    if results:
      test_name = results.group(1)
      status = self._StatusOfTest(test_name)
      if status != 'started':
        self._RecordError(line, 'success while in status %s' % status)
      self._test_status[test_name] = ('OK', [])
      self._failure_description = []
      self._current_test = ''
      return

    # Is it a test failure line?
    results = self._test_fail.search(line)
    if results:
      test_name = results.group(1)
      status = self._StatusOfTest(test_name)
      if status not in ('started', 'failed', 'timeout'):
        self._RecordError(line, 'failure while in status %s' % status)
      # Don't overwrite the failure description when a failing test is listed a
      # second time in the summary, or if it was already recorded as timing
      # out.
      if status not in ('failed', 'timeout'):
        self._test_status[test_name] = ('failed', self._failure_description)
      self._failure_description = []
      self._current_test = ''
      return

    # Is it a test timeout line?
    results = self._test_timeout.search(line)
    if results:
      test_name = results.group(1)
      status = self._StatusOfTest(test_name)
      if status not in ('started', 'failed'):
        self._RecordError(line, 'timeout while in status %s' % status)
      self._test_status[test_name] = ('timeout',
        self._failure_description + ['Killed (timed out).'])
      self._failure_description = []
      self._current_test = ''
      return

    # Random line: if we're in a test, collect it for the failure description.
    # Tests may run simultaneously, so this might be off, but it's worth a try.
    if self._current_test:
      self._failure_description.append(line)


class GTestCommand(shell.ShellCommand):
  """Buildbot command that knows how to display GTest output."""
  # TestAbbrFromTestID needs to be a member function.
  # pylint: disable=R0201

  _GTEST_DASHBOARD_BASE = ("http://test-results.appspot.com"
    "/dashboards/flakiness_dashboard.html")

  def __init__(self, **kwargs):
    shell.ShellCommand.__init__(self, **kwargs)
    self.test_observer = TestObserver()
    self.addLogObserver('stdio', self.test_observer)

  def evaluateCommand(self, cmd):
    shell_result = shell.ShellCommand.evaluateCommand(self, cmd)
    if shell_result is builder.SUCCESS:
      if (len(self.test_observer.internal_error_lines) > 0 or
          len(self.test_observer.FailedTests()) > 0):
        return builder.WARNINGS
    return shell_result

  def getText(self, cmd, results):
    basic_info = self.describe(True)
    disabled = self.test_observer.disabled_tests
    if disabled:
      basic_info.append('%s disabled' % str(disabled))

    flaky = self.test_observer.flaky_tests
    if flaky:
      basic_info.append('%s flaky' % str(flaky))

    if self.test_observer.internal_error_lines:
      # Generate a log file containing the list of errors.
      self.addCompleteLog('log parsing error(s)',
          '\n'.join(self.test_observer.internal_error_lines))

    failed_test_count = len(self.test_observer.FailedTests())

    if failed_test_count == 0:
      if results == builder.SUCCESS:
        return basic_info
      elif results == builder.WARNINGS:
        return basic_info + ['warnings']

    if self.test_observer.RunningTests():
      basic_info += ['did not complete']

    if failed_test_count:
      failure_text = ['failed %d' % failed_test_count]
      if self.test_observer.builder_name:
        # Include the link to the flakiness dashboard
        failure_text.append('<div class="BuildResultInfo">')
        # TODO(ojan): Once we pass --master-name to the gtest builders,
        # s/referringBuilder/master like in webkit_test_command.py.
        failure_text.append('<a href="%s#referringBuilder=%s&testType=%s'
                            '&tests=%s">' % (
            self._GTEST_DASHBOARD_BASE, self.test_observer.builder_name,
            self.describe(True)[0],
            ','.join(self.test_observer.FailedTests())))
        failure_text.append('Flakiness dashboard')
        failure_text.append('</a>')
        failure_text.append('</div>')
    else:
      failure_text = ['crashed or hung']
    return basic_info + failure_text

  def TestAbbrFromTestID(self, testid):
    """Split the test's individual name from GTest's full identifier.
    The name is assumed to be everything after the final '.', if any.
    """
    return testid.split('.')[-1]

  def createSummary(self, log):
    observer = self.test_observer
    for failure in sorted(observer.FailedTests()):
      # GTest test identifiers are of the form TestCase.TestName. We display
      # the test names only.  Unfortunately, addCompleteLog uses the name as
      # both link text and part of the text file name, so we can't incude
      # HTML tags such as <abbr> in it.
      self.addCompleteLog(self.TestAbbrFromTestID(failure),
                          '\n'.join(observer.FailureDescription(failure)))


class GTestFullCommand(GTestCommand):
  def TestAbbrFromTestID(self, testid):
    """
    Return the full TestCase.TestName ID.
    """
    return testid
