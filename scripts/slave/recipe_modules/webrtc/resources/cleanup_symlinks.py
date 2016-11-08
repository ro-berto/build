#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script that deletes all symlinks created by setup_links.py in a checkout."""

import os
import subprocess
import sys


def main(args):
  if len(args) != 1:
    print >> sys.stderr, 'Please specify a single directory as an argument.'
    return 1

  checkout_dir = args[0]
  if not os.path.isdir(checkout_dir):
    print 'Cannot find any directory at %s. Skipping cleaning.' % checkout_dir
    return 0

  setup_links_file = os.path.join(checkout_dir, 'setup_links.py')
  if not os.path.isfile(setup_links_file):
    print 'Cannot find %s. Incomplete checkout?' % setup_links_file
    return 1
  else:
    print 'Cleaning up symlinks in %s' % checkout_dir
    subprocess.check_call([sys.executable, setup_links_file, '--clean-only'],
                          cwd=checkout_dir)
    return 0



if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
