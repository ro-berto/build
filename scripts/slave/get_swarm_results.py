#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(maruel): Remove once the masters are restarted to use the version in
# swarming/

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
  cmd = [
    sys.executable,
    os.path.join(BASE_DIR, 'swarming', 'get_swarm_results_shim.py')
  ] + sys.argv[1:]
  return subprocess.call(cmd)


if __name__ == '__main__':
  sys.exit(main())
