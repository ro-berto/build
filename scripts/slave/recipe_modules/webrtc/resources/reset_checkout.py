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
                          'which points to the checkout root (dir above src/).')
    return 1

  checkout_root = args[0]
  if not os.path.isdir(checkout_root):
    print 'Cannot find any directory at %s. Skipping reset.' % checkout_root
    return 0

  checkout_src = os.path.join(checkout_root, 'src')
  if not os.path.exists(checkout_src):
    print ('Cannot find a src/ dir in the checkout at %s. '
           'Skipping reset.' % checkout_src)
    return 0

  print 'Resetting checkout...'
  subprocess.check_call(['git', 'reset', '--hard'],
                        cwd=checkout_src)
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
