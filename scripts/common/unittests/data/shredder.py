#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Program designed for RunCommand unit tests.

Reads lines from stdin and randomly outputs them to stdout or stderr.
"""

import random
import sys


def main(argv):
  stdin = sys.stdin
  if len(argv) > 1:
    stdin = open(argv[1], 'r')
  for line in stdin:
    if bool(random.getrandbits(1)):
      print line,
    else:
      print >> sys.stderr, line,

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
