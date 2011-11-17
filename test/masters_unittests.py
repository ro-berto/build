#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Runs the master unit tests.
"""

import os
import subprocess
import sys


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTESTS_PATH = os.path.abspath(os.path.join(
    TESTS_DIR, '..', 'scripts', 'master', 'unittests', 'runtests.py'))


def main():
  p = subprocess.Popen([RUNTESTS_PATH, '-f', 'all'])
  p.wait()
  return p.returncode


if __name__ == '__main__':
  sys.exit(main())
