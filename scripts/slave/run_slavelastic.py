#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Defer to the real one."""

import os
import sys
import subprocess

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
  real_script = os.path.join(
      ROOT_DIR, 'third_party', 'swarm_client', 'trigger_swarm_step.py')
  return subprocess.call([sys.executable, real_script] + sys.argv[2:])


if __name__ == '__main__':
  sys.exit(main())
