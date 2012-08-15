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
  def __init__(self):
    self.rc = builder.SUCCESS
    mock.Mock.__init__(self)


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
  def __init__(self, name, build):
    self.name = name
    self.urls = {}
    self.build = build
    self.text = None
    self.step = None
    self.logs = []
    mock.Mock.__init__(self)

  def stepStarted(self):
    return mock.Mock()

  def setText(self, text):
    self.text = text

  def setText2(self, text):
    self.text = text

  def getBuild(self):
    return self.build

  def getURLs(self):
    return self.urls.copy()

  def addURL(self, label, url):
    self.urls[label] = url

  def addLog(self, log):
    l = FakeLog(log)
    self.logs.append(l)
    return l

  def getLogs(self):
    return self.logs

  def getLog(self, log):
    candidates = [x for x in self.logs if x.name == log]
    if candidates:
      return candidates[0]
    else:
      return None

  def stepFinished(self, status):
    self.getBuild().receivedStatus.append(status)


class FakeBuildStatus(mock.Mock):
  def __init__(self):
    self.steps = []
    self.receivedStatus = []
    self.logs = []
    mock.Mock.__init__(self)

  def addStepWithName(self, step_name):
    newstep = FakeBuildstepStatus(step_name, self)
    self.steps.append(newstep)
    return newstep


class AnnotatorCommandsTest(unittest.TestCase):
  def setUp(self):
    self.buildstatus = FakeBuildStatus()
    self.command = FakeCommand()
    self.step = chromium_step.AnnotatedCommand(name='annotated_steps',
                                               description='annotated_steps',
                                               command=self.command)
    self.step_status = self.buildstatus.addStepWithName('annotated_steps')
    self.step.setStepStatus(self.step_status)
    self.handleOutputLine = self.step.script_observer.handleOutputLine

  def testAddAnnotatedSteps(self):
    self.handleOutputLine('@@@BUILD_STEP step@@@')
    self.handleOutputLine('@@@BUILD_STEP step2@@@')
    self.handleOutputLine('@@@BUILD_STEP done@@@')
    self.step.script_observer.handleReturnCode(0)

    stepnames = [x['step'].name for x in self.step.script_observer.sections]
    statuses = [x['status'] for x in self.step.script_observer.sections]

    self.assertEquals(stepnames, ['annotated_steps', 'step', 'step2', 'done'])
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
    testurl_hash = {'label': 'http://localhost/'}

    annotatedLinks = [x['links'] for x in self.step.script_observer.sections]
    stepLinks = [x['step'].getURLs() for x in
                 self.step.script_observer.sections]

    self.assertEquals(annotatedLinks, [testurls])
    self.assertEquals(stepLinks, [testurl_hash])

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

    catchFailure = lambda r: self.assertEquals(
        self.step_status.getBuild().receivedStatus, [builder.FAILURE])
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

  def testForNoPreambleAfter1Step(self):
    self.handleOutputLine('this line is part of the preamble')
    self.step.commandComplete(self.command)
    logs = self.step_status.getLogs()
    # buildbot will append 'stdio' for the first non-annotated section
    # but it won't show up in self.step_status.getLogs()
    self.assertEquals(len(logs), 0)

  def testForPreambleAfter2Steps(self):
    self.handleOutputLine('this line is part of the preamble')
    self.handleOutputLine('@@@BUILD_STEP step2@@@')
    self.step.commandComplete(self.command)
    logs = [l for x in self.buildstatus.steps for l in x.getLogs()]
    # annotator adds a stdio for each buildstep added
    self.assertEquals([x.getName() for x in logs], ['preamble', 'stdio'])

  def testForPreambleAfter3Steps(self):
    self.handleOutputLine('this line is part of the preamble')
    self.handleOutputLine('@@@BUILD_STEP step2@@@')
    self.handleOutputLine('@@@BUILD_STEP step3@@@')
    self.step.commandComplete(self.command)
    logs = [l for x in self.buildstatus.steps for l in x.getLogs()]
    self.assertEquals([x.getName() for x in logs], ['preamble', 'stdio',
                                                    'stdio'])

if __name__ == '__main__':
  unittest.main()
