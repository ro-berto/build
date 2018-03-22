# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to setup the environment to run integration tests.

Modifies PYTHONPATH to automatically include parent, common and pylibs
directories.
"""

import os
import sys

RUNTESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(RUNTESTS_DIR, '..', '..', '..'))
import common.env
common.env.Install(with_third_party=False)
