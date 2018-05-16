#!/usr/bin/env python
# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A thin wrapper script to redirect stdout of any command to a file.

Usage:
  ./redirect_stdout_to_file.py output_filename command [args...]
"""

import subprocess
import sys

def main():
  if len(sys.argv) < 3:
    print "Usage:"
    print "./redirect_stdout_to_file.py output_filename command [args...]"
    return 1

  filename = sys.argv[1]
  command = sys.argv[2:]

  with open(filename, 'w') as output_file:
    return subprocess.call(command, stdout=output_file)


if '__main__' == __name__:
  sys.exit(main())
