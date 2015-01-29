#!/usr/bin/python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common utility functions."""

import collections
import copy
import os
import subprocess
import sys
import tempfile

from common import gtest_utils
from slave import slave_utils


# This script is located in build/scripts/slave/ios.
# Update this path if the script is moved.
BUILD_DIR = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  '..',
  '..',
  '..',
))


class CallResult(object):
  """A result of call."""
  @property
  def returncode(self):
    """Returns the return code of the called process."""
    return self._returncode

  @property
  def stdout(self):
    """Returns the lines of output of the called process."""
    return self._stdout

  @property
  def stderr(self):
    """Returns the lines of error output of the called process."""
    return self._stderr

  @staticmethod
  def _get_lines(text):
    """Returns a tuple of nonempty lines of text.

    Args:
      Text: Text.

    Returns:
      A tuple containing all the nonempty lines in the given text.
    """
    return tuple(line for line in text.strip().splitlines() if line)

  def __init__(self, returncode, stdout, stderr):
    """Initializes a new instance of the CallResult class.

    Args:
      returncode: The return code of the called process.
      stdout: The output of the called process.
      stderr: The error output of the called process.
    """
    self._returncode = returncode
    self._stdout = self._get_lines(stdout)
    self._stderr = self._get_lines(stderr)


def call(binary, *args):
  """Invokes the specified shell command; emits stdout and stderr appropriately.

  Args:
    binary: The binary to invoke.
    args: A list of arguments to pass to cmd.

  Returns:
    A CallResult instance.
  """
  cmd = [binary]
  cmd.extend(args)

  print ' '.join(cmd)
  print 'cwd:', os.getcwd()
  print
  sys.stdout.flush()

  proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out, err = proc.communicate()

  sys.stdout.write(out)
  print
  sys.stdout.flush()
  sys.stderr.write(err)
  sys.stderr.flush()
  print
  sys.stdout.flush()

  return CallResult(proc.returncode, out, err)


class GTestResult(object):
  """A result of gtest.

  Properties:
    command: The command argv.
    crashed: Whether or not the test crashed.
    crashed_test: The name of the test during which execution crashed, or
      None if a particular test didn't crash.
    failed_tests: A dict mapping the names of failed tests to a list of
      lines of output from those tests.
    flaked_tests: A dict mapping the names of failed flaky tests to a list
      of lines of output from those tests.
    passed_tests: A list of passed tests.
    return_code: The return code of the command.
    success: Whether or not this run of the command was considered a
      successful GTest execution.
  """
  @property
  def crashed(self):
    return self._crashed

  @property
  def crashed_test(self):
    return self._crashed_test

  @property
  def command(self):
    return self._command

  @property
  def failed_tests(self):
    if self.__finalized:
      return copy.deepcopy(self._failed_tests)
    return self._failed_tests

  @property
  def flaked_tests(self):
    if self.__finalized:
      return copy.deepcopy(self._flaked_tests)
    return self._flaked_tests

  @property
  def passed_tests(self):
    if self.__finalized:
      return copy.deepcopy(self._passed_tests)
    return self._passed_tests

  @property
  def return_code(self):
    return self._return_code

  @property
  def success(self):
    return self._success

  def __init__(self, command):
    if not isinstance(command, collections.Iterable):
      raise ValueError('Expected an iterable of command arguments.', command)

    if not command:
      raise ValueError('Expected a non-empty command.', command)

    self._command = tuple(command)
    self._crashed = False
    self._crashed_test = None
    self._failed_tests = collections.OrderedDict()
    self._flaked_tests = collections.OrderedDict()
    self._passed_tests = []
    self._return_code = None
    self._success = None
    self.__finalized = False

  def finalize(self, return_code, success):
    self._return_code = return_code
    self._success = success

    # If the test was not considered to be a GTest success, but had no
    # failing tests, conclude that it must have crashed.
    if not self._success and not self._failed_tests and not self._flaked_tests:
      self._crashed = True

    # At most one test can crash the entire app in a given parsing.
    for test, log_lines in self._failed_tests.iteritems():
      # A test with no output would have crashed. No output is replaced
      # by the GTestLogParser by a sentence indicating non-completion.
      if 'Did not complete.' in log_lines:
        self._crashed = True
        self._crashed_test = test

    # A test marked as flaky may also have crashed the app.
    for test, log_lines in self._flaked_tests.iteritems():
      if 'Did not complete.' in log_lines:
        self._crashed = True
        self._crashed_test = test

    self.__finalized = True


def gtest(command):
  """Runs the specified command, parsing GTest output.

  Args:
    command: The shell command to execute, as a list of arguments.

  Returns:
    A GTestResult instance.
  """
  result = GTestResult(command)

  print ' '.join(command)
  print 'cwd:', os.getcwd()
  sys.stdout.flush()

  proc = subprocess.Popen(
    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

  parser = gtest_utils.GTestLogParser()

  while True:
    line = proc.stdout.readline()
    if not line:
      break
    line = line.rstrip()
    parser.ProcessLine(line)
    print line
    sys.stdout.flush()

  proc.wait()

  for test in parser.FailedTests(include_flaky=True):
    # Tests are named as TestCase.TestName.
    # A TestName starting with FLAKY_ should not turn the build red.
    if '.' in test and test.split('.', 1)[1].startswith('FLAKY_'):
      result.flaked_tests[test] = parser.FailureDescription(test)
    else:
      result.failed_tests[test] = parser.FailureDescription(test)

  result.passed_tests.extend(parser.PassedTests(include_flaky=True))

  print command[0], 'returned', proc.returncode
  print
  sys.stdout.flush()

  # iossim can return 5 if it exits noncleanly, even if no tests failed.
  # Therefore we cannot rely on this returncode to determine success or failure.
  result.finalize(proc.returncode, parser.CompletedWithoutFailure())
  return result
