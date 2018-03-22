# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to setup the environment to run unit tests.

Modifies PYTHONPATH to automatically include parent, common and pylibs
directories.
"""

import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(TESTS_DIR, 'data')

sys.path.insert(0, os.path.join(TESTS_DIR, '../scripts'))
import common.env
common.env.Install(with_third_party=True)
