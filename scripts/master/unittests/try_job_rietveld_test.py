#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""try_job_rietveld.py testcases."""

import unittest

import test_env  # pylint: disable=W0611

from master import try_job_rietveld


class ValidUserTest(unittest.TestCase):
  def setUp(self):
    # pylint: disable=W0212
    self.vu = try_job_rietveld._ValidUserPoller(None)
    self.vu._MakeSet('\n'.join(['goodone', 'great.one', 'me@gmail.com']))

  def test_common_user_names(self):
    self.assertTrue(self.vu.contains('goodone'))
    self.assertTrue(self.vu.contains('great.one'))
    self.assertTrue(self.vu.contains('me@gmail.com'))

  def test_nonuser_names(self):
    self.assertFalse(self.vu.contains(''))
    self.assertFalse(self.vu.contains('nasty'))
    self.assertFalse(self.vu.contains('chromium.org'))
    self.assertFalse(self.vu.contains('google.com'))
    self.assertFalse(self.vu.contains('cmp+cc'))
    self.assertFalse(self.vu.contains('goodone+drunk'))

  def test_user_names_with_domain(self):
    self.assertTrue(self.vu.contains('goodone@chromium.org'))
    self.assertTrue(self.vu.contains('great.one@google.com'))

  def test_user_names_with_bad_domain(self):
    self.assertFalse(self.vu.contains('great.one@evil.org'))

  def test_nonuser_names_with_domain(self):
    self.assertFalse(self.vu.contains('dirty@gmail.com'))
    self.assertFalse(self.vu.contains('smelly@chromium.org'))
    self.assertFalse(self.vu.contains('@chromium.org'))
    self.assertFalse(self.vu.contains('me@chromium.org'))

  def test_user_names_with_multiple_domains(self):
    self.assertFalse(self.vu.contains('goodone@chromium.org@google.com'))

  def test_nonuser_names_with_multiple_domains(self):
    self.assertFalse(self.vu.contains('me@google.com@chromium.org'))
    self.assertFalse(self.vu.contains('me@chromium.org@google.com'))
    self.assertFalse(self.vu.contains('@chromium.org@google.com'))

  def test_sequentially(self):
    """Make sure the answers don't change when we interleave good  and bad."""
    self.test_common_user_names()
    self.test_nonuser_names()
    self.test_nonuser_names_with_domain()
    self.test_user_names_with_domain()
    self.test_user_names_with_domain()
    self.test_nonuser_names()

if __name__ == '__main__':
  unittest.main()
