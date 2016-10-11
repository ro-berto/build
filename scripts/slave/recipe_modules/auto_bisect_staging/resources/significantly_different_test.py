#!/usr/bin/env python
"""Tests for significantly_different."""

import json
import os
import sys
import unittest

# pylint: disable=relative-import
import significantly_different


class SignificantlyDifferentTest(unittest.TestCase):

  def setUp(self):
    self.conda_path = None
    try:
      import scipy  # pylint: disable=unused-variable
      self.conda_path = sys.executable
    except ImportError:
      if os.path.exists(os.path.expanduser('~/conda-test/bin/python')):
        self.conda_path = os.path.expanduser('~/conda-test/bin/python')

  def test_basic_case(self):
    try:
      sample_A = [1, 2, 3, 3, 2, 1]
      sample_B = [1, 2, 2, 2, 5, 0]
      results = significantly_different.main(
          ['', json.dumps(sample_A), json.dumps(sample_B), '0.05'],
          self.conda_path)
    except significantly_different.ScipyNotInstalledError:
      # This is meant to let presubmit pass on CQ bots :( because they don't
      # have scipy either directly or thorugh anaconda.
      return

    self.assertAlmostEqual(
        0.40073980338363635,
        results['mann_p_value'])
    self.assertEqual(results['first_sample'], sample_A)
    self.assertEqual(results['second_sample'], sample_B)

  def test_single_value(self):
    try:
      sample_A = [1, 1, 1, 1, 1, 1]
      sample_B = [1, 1, 1]
      results = significantly_different.main(
          ['', json.dumps(sample_A), json.dumps(sample_B), '0.05'],
          self.conda_path)
    except significantly_different.ScipyNotInstalledError:
      # This is meant to let presubmit pass on CQ bots :( because they don't
      # have scipy either directly or thorugh anaconda.
      return
    self.assertIsNone(results['mann_p_value'])
    self.assertFalse(results['significantly_different'])
    self.assertEqual(results['first_sample'], sample_A)
    self.assertEqual(results['second_sample'], sample_B)

if __name__ == '__main__':
  unittest.main()
