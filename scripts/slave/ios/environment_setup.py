#!/usr/bin/python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Import path setup for PRESUBMIT to be able to run the tests found here."""

import os
import sys


# This script is located in build/scripts/slave/ios.
# Update this path if the script is moved.
BUILD_DIR = os.path.abspath(os.path.join(
  os.path.dirname(__file__),
  '..',
  '..',
  '..',
))

sys.path.insert(0, os.path.join(BUILD_DIR, 'scripts', 'tools'))

import runit

runit.add_build_paths(sys.path)
