#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utils for the dart project.
"""

import optparse
import os
import sys

from common import chromium_utils

def clobber():
  print('Clobbereing platform: %s' % sys.platform)
  if sys.platform in ('win32'):
    release_dir = os.path.abspath('Release_ia32')
    print('Removing directory %s' % release_dir)
    chromium_utils.RemoveDirectory(release_dir)
    debug_dir = os.path.abspath('Debug_ia32')
    print('Removing directory %s' % debug_dir)
    chromium_utils.RemoveDirectory(debug_dir)
  elif sys.platform in ('linux2'):
    out_dir = os.path.abspath('out')
    print('Removing directory %s' % out_dir)
    chromium_utils.RemoveDirectory(out_dir)
  elif sys.platform.startswith('darwin'):
    xcode_dir = os.path.abspath('xcodebuild')
    print('Removing directory %s' % xcode_dir)
    chromium_utils.RemoveDirectory(xcode_dir)
  else:
    print("Platform not recognized")
  return 0


def main():
  parser = optparse.OptionParser()
  parser.add_option('',
                    '--clobber',
                    default=False,
                    action='store_true',
                    help='Clobber the builder')
  options, args = parser.parse_args()

  # args unused, use.
  args.append('')

  # Determine what to do based on options passed in.
  if options.clobber:
    return clobber()
  else:
    print("Nothing to do")


if '__main__' == __name__ :
  sys.exit(main())
