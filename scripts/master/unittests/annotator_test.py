#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for annotated command testcases."""

import test_env  # pylint: disable=W0611
import unittest
import mock      # using third_party mock for now

from twisted.internet import defer
from buildbot.status import builder
from master import chromium_step

# Mocks confuse pylint.
# pylint: disable=E1101
# pylint: disable=R0201


class FakeCommand(mock.Mock):
  def addLog(self, ignored):
    return mock.Mock()

  def getLogs(self):
    return [mock.Mock()]


class FakeBuildStep(mock.Mock):
  def __init__(self, name):
    self.name = name
    self.text = None
    self.receivedStatus = []
    self.urls = []
    mock.Mock.__init__(self)

  def addURL(self, label, url):
    self.urls.append((label, url))

  def stepStarted(self):
    return mock.Mock()

  def addLog(self, ignored):
    return mock.Mock()

  def getLogs(self):
    return [mock.Mock()]

  def setText(self, text):
    self.text = text

  def setText2(self, text):
    self.text = text

  def stepFinished(self, status):
    self.receivedStatus.append(status)


class FakeLog(object):
  def __init__(self, name):
    self.text = ''
    self.name = name
    self.chunkSize = 1024

  def addStdout(self, data):
    self.text += data

  def getName(self):
    return self.name

  def addHeader(self, msg):
    pass

  def finish(self):
    pass


class FakeBuildstepStatus(mock.Mock):
  def __init__(self):
    self.steps = [FakeBuildStep('init')]
    self.receivedStatus = []
    self.logs = {}
    mock.Mock.__init__(self)

  def getBuild(self):
    return self

  def addStepWithName(self, step_name):
    newstep = FakeBuildStep(step_name)
    self.steps.append(newstep)
    return newstep

  def addLog(self, log):
    l = FakeLog(log)
    self.logs[log] = l
    return l

  def getLogs(self):
    return self.logs.values()

  def getLog(self, log):
    if log in self.logs:
      return self.logs[log]
    else:
      return None

  def stepFinished(self, status):
    self.receivedStatus.append(status)


class AnnotatorCommandsTest(unittest.TestCase):
  def setUp(self):
    self.step = chromium_step.AnnotatedCommand(name='annotated_steps',
                                               description='annotated_steps',
                                               command=FakeCommand())

    self.step_status = FakeBuildstepStatus()
    self.step.setStepStatus(self.step_status)
    self.handleOutputLine = self.step.script_observer.handleOutputLine

  def testAddAnnotatedSteps(self):
    self.handleOutputLine('@@@BUILD_STEP step@@@')
    self.handleOutputLine('@@@BUILD_STEP step2@@@')
    self.handleOutputLine('@@@BUILD_STEP done@@@')
    self.step.script_observer.handleReturnCode(0)

    stepnames = [x['step'].name for x in self.step.script_observer.sections]
    statuses = [x['status'] for x in self.step.script_observer.sections]

    self.assertEquals(stepnames, ['init', 'step', 'step2', 'done'])
    self.assertEquals(statuses, 4 * [builder.SUCCESS])
    self.assertEquals(self.step.script_observer.annotate_status,
                      builder.SUCCESS)

  def testBuildFailure(self):
    self.handleOutputLine('@@@STEP_FAILURE@@@')
    self.handleOutputLine('@@@BUILD_STEP step@@@')
    self.step.script_observer.handleReturnCode(0)

    statuses = [x['status'] for x in self.step.script_observer.sections]

    self.assertEquals(statuses, [builder.FAILURE, builder.SUCCESS])
    self.assertEquals(self.step.script_observer.annotate_status,
                      builder.FAILURE)

  def testBuildException(self):
    self.handleOutputLine('@@@STEP_EXCEPTION@@@')
    self.handleOutputLine('@@@BUILD_STEP step@@@')

    statuses = [x['status'] for x in self.step.script_observer.sections]

    self.assertEquals(statuses, [builder.EXCEPTION, builder.SUCCESS])
    self.assertEquals(self.step.script_observer.annotate_status,
                      builder.EXCEPTION)

  def testStepLink(self):
    self.handleOutputLine('@@@STEP_LINK@label@http://localhost/@@@')
    testurls = [('label', 'http://localhost/')]

    annotatedLinks = [x['links'] for x in self.step.script_observer.sections]
    stepLinks = [x['step'].urls for x in self.step.script_observer.sections]

    self.assertEquals(annotatedLinks, [testurls])
    self.assertEquals(stepLinks, [testurls])

  def testStepWarning(self):
    self.handleOutputLine('@@@STEP_WARNINGS@@@')
    self.handleOutputLine('@@@BUILD_STEP step@@@')

    statuses = [x['status'] for x in self.step.script_observer.sections]

    self.assertEquals(statuses, [builder.WARNINGS, builder.SUCCESS])
    self.assertEquals(self.step.script_observer.annotate_status,
                      builder.WARNINGS)

  def testStepText(self):

    self.handleOutputLine('@@@STEP_TEXT@example_text@@@')
    self.handleOutputLine('@@@BUILD_STEP step2@@@')
    self.handleOutputLine('@@@STEP_TEXT@example_text2@@@')
    self.handleOutputLine('@@@BUILD_STEP step3@@@')
    self.handleOutputLine('@@@STEP_TEXT@example_text3@@@')

    texts = [x['step_text'] for x in self.step.script_observer.sections]

    self.assertEquals(texts, [['example_text'], ['example_text2'],
                              ['example_text3']])

  def testStepClear(self):
    self.handleOutputLine('@@@STEP_TEXT@example_text@@@')
    self.handleOutputLine('@@@BUILD_STEP step2@@@')
    self.handleOutputLine('@@@STEP_TEXT@example_text2@@@')
    self.handleOutputLine('@@@STEP_CLEAR@@@')

    texts = [x['step_text'] for x in self.step.script_observer.sections]

    self.assertEquals(texts, [['example_text'], []])

  def testStepSummaryText(self):
    self.handleOutputLine('@@@STEP_SUMMARY_TEXT@example_text@@@')
    self.handleOutputLine('@@@BUILD_STEP step2@@@')
    self.handleOutputLine('@@@STEP_SUMMARY_TEXT@example_text2@@@')
    self.handleOutputLine('@@@BUILD_STEP step3@@@')
    self.handleOutputLine('@@@STEP_SUMMARY_TEXT@example_text3@@@')

    texts = [x['step_summary_text'] for x in self.step.script_observer.sections]

    self.assertEquals(texts, [['example_text'], ['example_text2'],
                              ['example_text3']])

  def testStepSummaryClear(self):
    self.handleOutputLine('@@@STEP_SUMMARY_TEXT@example_text@@@')
    self.handleOutputLine('@@@BUILD_STEP step2@@@')
    self.handleOutputLine('@@@STEP_SUMMARY_TEXT@example_text2@@@')
    self.handleOutputLine('@@@STEP_SUMMARY_CLEAR@@@')

    texts = [x['step_summary_text'] for x in self.step.script_observer.sections]

    self.assertEquals(texts, [['example_text'], []])

  def testHaltOnFailure(self):
    self.step.deferred = defer.Deferred()
    self.handleOutputLine('@@@HALT_ON_FAILURE@@@')

    catchFailure = lambda r: self.assertEquals(self.step_status.receivedStatus,
                                               [builder.FAILURE])
    self.step.deferred.addBoth(catchFailure)
    self.handleOutputLine('@@@STEP_FAILURE@@@')

    self.assertEquals(self.step.script_observer.annotate_status,
                      builder.FAILURE)

  def testReturnCode(self):
    self.step.script_observer.handleReturnCode(1)

    self.assertEquals(self.step.script_observer.annotate_status,
                      builder.FAILURE)

  def testHonorZeroReturnCode(self):
    self.handleOutputLine('@@@HONOR_ZERO_RETURN_CODE@@@')
    self.handleOutputLine('@@@STEP_FAILURE@@@')
    self.step.script_observer.handleReturnCode(0)

    self.assertEquals(self.step.script_observer.annotate_status,
                      builder.SUCCESS)

  def testLogLine(self):
    self.handleOutputLine('@@@STEP_LOG_LINE@test_log@this is line one@@@')
    self.handleOutputLine('@@@STEP_LOG_LINE@test_log@this is line two@@@')
    self.handleOutputLine('@@@STEP_LOG_END@test_log@@@')

    logs = self.step_status.getLogs()
    self.assertEquals(len(logs), 2)
    self.assertEquals(logs[1].getName(), 'test_log')
    self.assertEquals(self.step_status.getLog('test_log').text,
                      'this is line one\nthis is line two')


if __name__ == '__main__':
  unittest.main()
