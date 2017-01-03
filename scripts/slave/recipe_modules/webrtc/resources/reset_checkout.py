#!/usr/bin/env python
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script that runs git reset --hard on a checkout."""

import os
import subprocess
import sys


def main(args):
  if len(args) != 1:
    print >> sys.stderr, ('Please specify a single directory as an argument, '
                          'which points to the checkout src/ dir).')
    return 1

  checkout_src = args[0]
  if not os.path.isdir(checkout_src):
    print 'Cannot find checkout dir at %s. Skipping reset.' % checkout_src
    return 0

  print 'Resetting checkout...'
  subprocess.check_call(['git', 'reset', '--hard'],
                        cwd=checkout_src)
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
