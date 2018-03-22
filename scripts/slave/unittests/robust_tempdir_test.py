#!/usr/bin/env vpython
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import unittest

import test_env  # pylint: disable=relative-import

from slave import robust_tempdir


class RobustTempdirTest(unittest.TestCase):
  def test_empty(self):
    with robust_tempdir.RobustTempdir(prefix='robust_tempdir_test'):
      pass

  def test_basic(self):
    with robust_tempdir.RobustTempdir(prefix='robust_tempdir_test') as rt:
      path = rt.tempdir()
      self.assertTrue(os.path.exists(path))

    self.assertFalse(os.path.exists(path))

  def test_leak(self):
    with robust_tempdir.RobustTempdir(
        prefix='robust_tempdir_test', leak=True) as rt:
      path = rt.tempdir()
      self.assertTrue(os.path.exists(path))

    self.assertTrue(os.path.exists(path))
    os.rmdir(path)


if __name__ == '__main__':
  unittest.main()
