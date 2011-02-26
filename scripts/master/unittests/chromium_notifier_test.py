# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for chromium_notifier testcases."""

import unittest

from master import chromium_notifier


class ChromiumNotifierTest(unittest.TestCase):

  def testChromiumNotifierCreation(self):
    notifier = chromium_notifier.ChromiumNotifier(
        fromaddr='buildbot@test',
        mode='failing',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.')
