# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest

from libs.test_binary import create_test_binary_from_jsonish
from libs.result_summary import create_result_summary_from_output_json
from libs.strategies.base_strategy import BaseStrategy
from testdata import get_test_data


class BaseStrategyTest(unittest.TestCase):

  def setUp(self):
    test_binary = create_test_binary_from_jsonish(
        json.loads(get_test_data('gtest_test_binary.json')))
    result_summary = create_result_summary_from_output_json(
        json.loads(get_test_data('gtest_good_output.json')))
    self.strategy = BaseStrategy(test_binary, result_summary,
                                 'MockUnitTests.FailTest')

  def test_run(self):
    with self.assertRaises(NotImplementedError):
      self.strategy.run()
