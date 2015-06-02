#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Calls either isolate.py or isolate Go executable in the checkout.
"""

import os
import subprocess
import sys


def try_go(path, args):
  """Tries to run the Go implementation of isolate.

  Returns None if it should fall back to the python implementation.
  """
  luci_go = os.path.join(os.path.dirname(path), 'luci-go')
  if sys.platform == 'win32':
    exe = os.path.join(luci_go, 'win64', 'isolate.exe')
  elif sys.platform == 'darwin':
    exe = os.path.join(luci_go, 'mac64', 'isolate')
  else:
    exe = os.path.join(luci_go, 'linux64', 'isolate')
  if not os.access(exe, os.X_OK):
    return None

  # Try to use Go implementation.
  try:
    version = subprocess.check_output([exe, 'version']).strip()
    version = tuple(map(int, version.split('.')))
  except (subprocess.CalledProcessError, OSError, ValueError):
    return None

  # Key behavior based on version if necessary.
  if version < (0, 1):
    return None

  return subprocess.call([exe] + args)


def main():
  path = sys.argv[1]
  args = sys.argv[2:]
  ret = try_go(path, args)
  if ret is None:
    return subprocess.call(
        [sys.executable, os.path.join(path, 'isolate.py')] + args)
  return ret


if __name__ == '__main__':
  sys.exit(main())
