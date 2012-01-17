#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for gatekeeper testcases."""

import unittest

import test_env  # pylint: disable=W0611
from common import find_depot_tools  # pylint: disable=W0611

from buildbot.status.results import FAILURE
import mock
from twisted.internet import defer

from testing_support import auto_stub

from master import gatekeeper

# Mocks confuse pylint.
# pylint: disable=E1101


class FakePassword(object):
  def __init__(self, _):
    pass

  @staticmethod
  def GetPassword():
    return 'testpw'


def _get_master_status():
  ms = mock.Mock()
  ms.getTitle.return_value = 'Fake master'
  ms.getBuildbotURL.return_value = 'http://somewhere'
  return ms


def _get_gatekeeper():
  mn = gatekeeper.GateKeeper(
      'url',
      fromaddr='from@example.org',
      mode='all',
      builders=['builder1'],
      use_getname=True,
      lookup=None)
  mn.master_status = _get_master_status()
  # Nuke out sending emails.
  mn.sendmail = mock.Mock()
  mn.sendmail.return_value = 'email sent!'
  return mn


def _get_build():
  """Returns a buildbot.status.build.BuildStatus."""
  # buildbot.status.builder.BuilderStatus
  builder = mock.Mock()
  builder.getName.return_value = 'builder1'

  change = mock.Mock()
  change.asHTML.return_value = '<change1>'

  build = mock.Mock()
  build.getBuilder.return_value = builder
  build.getResponsibleUsers.return_value = ['joe']
  build.getChanges.return_value = [change]
  return build


def _get_step():
  """Returns a buildbot.status.buildstep.BuildStepStatus."""
  step = mock.Mock()
  step.getName.return_value = 'step1'
  return step


class GateKeeperTest(auto_stub.TestCase):
  def setUp(self):
    super(GateKeeperTest, self).setUp()
    self.mock(gatekeeper.client, 'getPage', mock.Mock())
    self.mock(gatekeeper.get_password, 'Password', FakePassword)
    self.mock(gatekeeper.build_utils, 'getAllRevisions', mock.Mock())
    self.mock(gatekeeper.build_utils, 'EmailableBuildTable', mock.Mock())
    gatekeeper.build_utils.getAllRevisions.return_value = [23]
    gatekeeper.build_utils.EmailableBuildTable.return_value = 'end of table'

  def test_Creation(self):
    notifier = gatekeeper.GateKeeper(
        fromaddr='buildbot@test',
        mode='failing',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.',
        tree_status_url='http://localhost/')
    self.assertTrue(notifier)

  def test_buildMessage(self):
    # Make sure the code flows up to buildMessage with isInterestingStep mocked
    # out.
    mn = _get_gatekeeper()
    mn.isInterestingStep = mock.Mock()
    mn.isInterestingStep.return_value = True
    mn.buildMessage = mock.Mock()

    build = _get_build()
    step = _get_step()
    mn.stepFinished(build, step, [FAILURE])
    mn.buildMessage.assert_called_with('builder1', build, [FAILURE], 'step1')
    mn.isInterestingStep.assert_called_once_with(build, step, [FAILURE])
    self.assertEquals(0, mn.sendmail.call_count)

  def test_tree_open(self):
    # Make sure the code flows up to buildMessage.
    mn = _get_gatekeeper()
    mn.isInterestingStep = mock.Mock()
    mn.isInterestingStep.return_value = True
    mn.getFinishedMessage = mock.Mock()

    build = _get_build()
    step = _get_step()

    # Tree is open.
    gatekeeper.client.getPage.return_value = defer.succeed('1')

    d = mn.stepFinished(build, step, [FAILURE])
    self.assertTrue(isinstance(d, defer.Deferred))
    mn.isInterestingStep.assert_called_once_with(build, step, [FAILURE])
    gatekeeper.client.getPage.assert_called_once_with('url', agent='buildbot')
    self.assertEquals(1, mn.sendmail.call_count)
    mn.getFinishedMessage.assert_called_once_with(
        'email sent!', 'builder1', build, 'step1')

  def test_tree_closed(self):
    # Make sure the code flows up to buildMessage.
    mn = _get_gatekeeper()
    mn.isInterestingStep = mock.Mock()
    mn.isInterestingStep.return_value = True
    mn.getFinishedMessage = mock.Mock()

    build = _get_build()
    step = _get_step()

    # Tree is closed.
    gatekeeper.client.getPage.return_value = defer.succeed('0')

    d = mn.stepFinished(build, step, [FAILURE])
    self.assertTrue(isinstance(d, defer.Deferred))
    mn.isInterestingStep.assert_called_once_with(build, step, [FAILURE])
    gatekeeper.client.getPage.assert_called_with('url', agent='buildbot')
    self.assertEquals(0, mn.sendmail.call_count)
    self.assertEquals(0, mn.getFinishedMessage.call_count)


if __name__ == '__main__':
  unittest.main()
