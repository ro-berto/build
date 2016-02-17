#!/usr/bin/env python
"""Tests for significantly_different."""

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
      results = significantly_different.main(
          ['', '[1, 2, 3, 3, 2, 1]', '[1, 2, 2, 2, 5, 0]', '0.05'],
          self.conda_path)
    except significantly_different.ScipyNotInstalledError:
      # This is meant to let presubmit pass on CQ bots :( because they don't
      # have scipy either directly or thorugh anaconda.
      return

    self.assertAlmostEqual(
        0.40073980338363635,
        results['mann_p_value'])

if __name__ == '__main__':
  unittest.main()
