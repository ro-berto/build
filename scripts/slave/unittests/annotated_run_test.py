#!/usr/bin/env python

# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests that the tools/build annotated_run wrapper actually runs."""

import os
import subprocess
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AnnotatedRunTest(unittest.TestCase):
  def test_example(self):
    script_path = os.path.join(BASE_DIR, 'annotated_run.py')
    exit_code = subprocess.call([
        'python', script_path,
        '--factory-properties={"recipe":"step:example"}'])
    self.assertEqual(exit_code, 0)

if __name__ == '__main__':
  unittest.main()
