# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest

from libs.test_binary.base_test_binary import BaseTestBinary
from testdata import get_test_data


class BaseTestBinaryTest(unittest.TestCase):

  def setUp(self):
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    self.test_binary = BaseTestBinary.from_jsonish(jsonish)

  def test_from_to_jsonish(self):
    self.maxDiff = None
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    test_binary = BaseTestBinary.from_jsonish(jsonish)
    to_jsonish = test_binary.to_jsonish()
    self.assertEqual(to_jsonish, jsonish)

  def test_should_not_implement_in_base_class(self):
    with self.assertRaises(NotImplementedError):
      self.test_binary.run_tests([], 1)
