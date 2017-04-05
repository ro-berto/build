#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script to run layout tests on the buildbots.

TODO(qyearsley): Remove all usage of this script, see crbug.com/695700.
"""

import argparse
import os
import sys

from common import chromium_utils
from slave import build_directory
from slave import slave_utils


def main():
  assert sys.platform != 'win32', 'This script should not be run on Windows.'

  build_dir = os.path.abspath(build_directory.GetBuildOutputDirectory())
  blink_scripts_dir = chromium_utils.FindUpward(
      build_dir, 'third_party', 'WebKit', 'Tools', 'Scripts')
  run_blink_tests = os.path.join(blink_scripts_dir, 'run-webkit-tests')

  # Forward all command line arguments on to run-webkit-tests.
  command = ['python', run_blink_tests] + sys.argv[1:]
  return chromium_utils.RunCommand(command)


if '__main__' == __name__:
  sys.exit(main())
