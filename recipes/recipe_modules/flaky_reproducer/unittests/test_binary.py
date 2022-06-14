# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from multiprocessing.sharedctypes import Value
import os
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(THIS_DIR, os.pardir)))
from libs.test_binary.base_test_binary import BaseTestBinary


class BaseTestBinaryTest(unittest.TestCase):

  def setUp(self):
    self.test_binary = BaseTestBinary()

  def test_should_not_implement_in_base_class(self):
    with self.assertRaises(NotImplementedError):
      self.test_binary.run_tests([], 1)
