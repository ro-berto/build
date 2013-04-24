#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Do a revert if a checkout exists."""

import os
import sys

from common import chromium_utils


def main():
  if len(sys.argv) != 3:
    print 'usage: gclient_safe_revert.py build_directory gclient_location'
    return 2

  buildpath = sys.argv[1]
  gclient = sys.argv[2]

  if not os.path.exists(buildpath):
    print 'Path %s doesn\'t exist, not running gclient.' % buildpath
    return 0

  if not os.path.isdir(buildpath):
    print 'Path %s isn\'t a directory, not running gclient.' % buildpath
    return 0

  gclient_config = os.path.join(buildpath, '.gclient')
  if not os.path.exists(gclient_config):
    print ('%s doesn\'t exist, not a gclient-controlled checkout.' %
              gclient_config)
    return 0

  cmd = [sys.executable, gclient, 'revert', '--nohooks']
  return chromium_utils.RunCommand(cmd, cwd=buildpath)


if '__main__' == __name__:
  sys.exit(main())
