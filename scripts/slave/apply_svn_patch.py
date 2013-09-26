#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import optparse
import subprocess
import sys


def main():
  parser = optparse.OptionParser()
  parser.add_option('-p', '--patch-url',
                    help='The SVN URL to download the patch from.')
  parser.add_option('-r', '--root-dir',
                    help='The root dir in which to apply patch.')

  options, args = parser.parse_args()
  if args:
    parser.error('Unused args: %s' % args)
  if not (options.patch_url and options.root_dir):
    parser.error('A patch URL and root directory should be specified.')

  svn_cat = subprocess.Popen(['svn', 'cat', options.patch_url],
                             stdout=subprocess.PIPE)
  patch = subprocess.Popen(['patch', '-t', '-p', '0', '-d', options.root_dir],
                           stdin=svn_cat.stdout)

  _, err = patch.communicate()
  return err or None


if __name__ == '__main__':
  sys.exit(main())
