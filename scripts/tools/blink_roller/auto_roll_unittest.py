#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from auto_roll import SheriffCalendar


class SheriffCalendarTest(unittest.TestCase):

  def test_complete_email(self):
    calendar = SheriffCalendar()
    expected_emails = ['foo@chromium.org', 'bar@google.com', 'baz@chromium.org']
    names = ['foo', 'bar@google.com', 'baz']
    self.assertEqual(map(calendar.complete_email, names), expected_emails)

  def test_emails(self):
    expected_emails = ['foo@bar.com', 'baz@baz.com']
    calendar = SheriffCalendar()
    calendar._emails_from_url = lambda urls: expected_emails
    self.assertEqual(calendar.current_gardener_emails(), expected_emails)
    self.assertEqual(calendar.current_sheriff_emails(), expected_emails)

  def _assert_parse(self, js_string, expected_emails):
    calendar = SheriffCalendar()
    self.assertEqual(
      calendar.names_from_sheriff_js(js_string), expected_emails)

  def test_names_from_sheriff_js(self):
    self._assert_parse('document.write(\'none (channel is sheriff)\')', [])
    self._assert_parse('document.write(\'foo, bar\')', ['foo', 'bar'])


class AutoRollTest(unittest.TestCase):
  pass


if __name__ == '__main__':
  unittest.main()
