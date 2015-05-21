#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Calls either isolate.py or isolate Go executable in the checkout.
"""

import os
import sys


def main():
  path = sys.argv[1]
  luci_go = os.path.join(os.path.dirname(path), 'luci-go')
  if sys.platform == 'win32':
    exe = os.path.join(luci_go, 'win64', 'isolate.exe')
  elif sys.platform == 'darwin':
    exe = os.path.join(luci_go, 'mac64', 'isolate')
  else:
    exe = os.path.join(luci_go, 'linux64', 'isolate')
  if os.access(exe, os.X_OK):
    # Use Go implementation. We'd prefer to build on-the-fly but the bots do not
    # all have yet the Go toolset.
    return subprocess.call([exe] + sys.argv[2:])

  return subprocess.call(
      [sys.executable, os.path.join(path, 'isolate.py')] + sys.argv[2:])


if __name__ == '__main__':
  sys.exit(main())
