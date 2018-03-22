# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to setup the environment to run unit tests.

Modifies PYTHONPATH to automatically include parent, common and pylibs
directories.
"""

import os
import subprocess
import sys
import textwrap

# If we're not running in a VirtualEnv, bootstrap ourselves through "vpython".
#
# This helps systems (e.g., PRESUBMIT) that run this explicitly via Python
# instead of paying attention to the shebang line.
IS_WINDOWS = os.name == 'nt'
if not os.getenv('VIRTUAL_ENV'):
  sys.exit(subprocess.call(['vpython'] + sys.argv,
    shell=IS_WINDOWS))

RUNTESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(RUNTESTS_DIR, 'data')
BASE_DIR = os.path.abspath(
    os.path.join(RUNTESTS_DIR, os.pardir, os.pardir, os.pardir))

# Load our common Infra environment.
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
import common.env
common.env.Install(with_third_party=True)
