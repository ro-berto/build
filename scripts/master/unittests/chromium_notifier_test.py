#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for chromium_notifier testcases."""

import unittest

import test_env  # pylint: disable=W0611

from master import chromium_notifier


class ChromiumNotifierTest(unittest.TestCase):

  class fakeStep():
    def __init__(self, name, text=None):
      self.name = name
      self.text = text

    def getName(self):
      return self.name

    def getText(self):
      return self.text


  def testChromiumNotifierCreation(self):
    notifier = chromium_notifier.ChromiumNotifier(
        fromaddr='buildbot@test',
        mode='failing',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.')
    self.assertTrue(notifier)

  def testChromiumNotifierDecoration(self):
    notifier = chromium_notifier.ChromiumNotifier(
        fromaddr='buildbot@test',
        mode='failing',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.')
    self.assertEquals(notifier.getGenericName("foo"), "foo")
    self.assertEquals(notifier.getGenericName("foo "), "foo")
    self.assertEquals(notifier.getGenericName(" foo"), "foo")
    self.assertEquals(notifier.getGenericName("foo [bar]"), "foo")
    self.assertEquals(notifier.getGenericName(" foo [bar]"), "foo")
    self.assertEquals(notifier.getGenericName("f [u] [bar]"), "f [u]")
    self.assertEquals(notifier.getGenericName("foo[bar]"), "foo")
    self.assertEquals(notifier.getGenericName("[foobar]"), "[foobar]")
    self.assertEquals(notifier.getGenericName(" [foobar]"), "[foobar]")
    self.assertEquals(notifier.getGenericName(" [foobar] "), "[foobar]")
    self.assertEquals(notifier.getGenericName("[foobar] [foo]"), "[foobar]")
    self.assertEquals(notifier.getGenericName("apple ]["), "apple ][")
    self.assertEquals(notifier.getGenericName("ipad ][][]["), "ipad ][][][")
    self.assertEquals(notifier.getGenericName("ipad [][]"), "ipad []")
    self.assertEquals(notifier.getGenericName("box []"), "box")


if __name__ == '__main__':
  unittest.main()
