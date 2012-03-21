#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env  # pylint: disable=W0611
import unittest

from buildbot.status.builder import FAILURE, SUCCESS

from master.chromium_notifier import ChromiumNotifier
from master.perf_count_notifier import PerfCountNotifier


TEST_STATUS_TEXT = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_REGRESS: time/t '
    '(89.07%) PERF_IMPROVE: fps/video (5.40%) </div>')

TEST_STATUS_TEXT_COUNTER = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_IMPROVE: time/t '
    '(44.07%) PERF_REGRESS: fps/video (3.0%) </div>')

TEST_STATUS_TEXT_2 = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_REGRESS: time/t2 '
    '(89.07%) PERF_IMPROVE: fps/video2 (5.40%) </div>')

TEST_STATUS_TEXT_EXCEPTION = ('media_tests_av_perf exception')


class PerfCountNotifierTest(unittest.TestCase):

  def setUp(self):
    self.email_sent = False
    self.notifier = PerfCountNotifier(
        fromaddr='buildbot@test',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.',
        step_names='test_tests',
        minimum_count=3)
    self.old_getName = None
    self.mockDefaultFunctions()

  def tearDown(self):
    self.resetMockDefaultFunctions()

  def mockDefaultFunctions(self):
    self.old_getName = ChromiumNotifier.getName
    ChromiumNotifier.getName = self.getNameMock

  def resetMockDefaultFunctions(self):
    ChromiumNotifier.getName = self.old_getName

  def getNameMock(self, step_status):
    """Mocks the getName which returns the build_status step name."""
    return self.notifier.step_names[0]

  def testSuccessIsNotInteresting(self):
    """Test success step is not interesting."""
    build_status = None
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [SUCCESS]
    for _ in range(self.notifier.minimum_count):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))

  def testIsInterestingAfterMinimumResults(self):
    """Test step is interesting only after minimum consecutive results."""
    build_status = None
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingResetByCounterResults(self):
    """Test step is not interesting if a counter result appears."""
    build_status = None
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    # Reset the counters by having counter results.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_COUNTER)
    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))
    # Now check that we need to count back from the start.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingResetBySuccess(self):
    """Test step count reset after a successful pass."""
    build_status = None
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    # Reset the counters by having a success step.
    results = [SUCCESS]
    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))
    # Now check that we need to count back from the start.
    results = [1]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingException(self):
    """Test step is interesting when step has exception."""
    build_status = None
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_EXCEPTION)
    results = [FAILURE]
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testNotificationOnce(self):
    """Test isInsteresting happens only once."""
    build_status = None
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))
    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))
    # Force expiration of notifications
    self.notifier.notifications.expiration_time = -1
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingResetByOtherResults(self):
    """Test isInsteresting resets after different results appear."""
    build_status = None
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    # Reset the counters by having other results.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_2)
    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))
    # Now check that we need to count back from the start.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

class BuildStepStatusMock:
  def __init__(self, text):
    self.text = text

  def getText(self):
    return [self.text]


if __name__ == '__main__':
  unittest.main()