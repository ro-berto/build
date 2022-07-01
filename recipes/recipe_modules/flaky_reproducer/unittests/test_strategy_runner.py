# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import os
import unittest
import strategy_runner

from unittest.mock import patch, mock_open
from testdata import get_test_data


class StrategyRunnerTest(unittest.TestCase):

  def setUp(self):
    # @patch('builtins.open', ...)
    mock_open_data = {
        'gtest_test_binary.json': get_test_data('gtest_test_binary.json'),
        'gtest_good_output.json': get_test_data('gtest_good_output.json'),
    }

    # pylint: disable=redefined-builtin
    def mock_open_method(file, *args, **kwargs):
      filename = os.path.basename(file)
      return mock_open(read_data=mock_open_data.get(filename, 'data'))()

    open_patcher = patch('builtins.open', new=mock_open_method)
    self.addClassCleanup(open_patcher.stop)
    open_patcher.start()

  @patch.object(
      strategy_runner, 'strategies', new={
          'repeat': None,
          'batch': None
      })
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_parse_args(self, mock_stderr):
    args = strategy_runner.parse_args(
        ['repeat', '--test-binary=foo', '--result-summary=bar', 'foo.bar'])
    self.assertEqual(args.strategy, 'repeat')

    with self.assertRaises(SystemExit):
      strategy_runner.parse_args(['unknown'])
    self.assertRegexpMatches(mock_stderr.getvalue(), r'invalid choice')

    with self.assertRaises(SystemExit):
      strategy_runner.parse_args(['batch'])
    self.assertRegexpMatches(mock_stderr.getvalue(), r'arguments are required')

  @patch.object(strategy_runner.strategies['repeat'], 'run')
  def test_main(self, mock_strategy_run):
    strategy_runner.main([
        'repeat', '--test-binary=gtest_test_binary.json',
        '--result-summary=gtest_good_output.json', 'MockUnitTests.FailTest'
    ])
    mock_strategy_run.assert_called()

  @patch.object(strategy_runner.strategies['repeat'], 'run')
  def test_main_test_not_found(self, mock_strategy_run):
    with self.assertRaises(LookupError):
      strategy_runner.main([
          'repeat', '--test-binary=gtest_test_binary.json',
          '--result-summary=gtest_good_output.json', 'NotExists.Test'
      ])
