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
  parser.add_option('', '--filter-script',
                    help=('Path to a Python script to be used to manipulate '
                          'the contents of the patch. One example could be to '
                          'remove parts of the patch matching certain file '
                          'paths. The script must use stdin for input and '
                          'stdout for output. The script will get the '
                          '--root-dir flag passed on to it. To pass additional '
                          'flags; use: -- --flag1 --flag2'))
  parser.add_option('', '--strip-level', type='int', default=0,
                    help=('The number of path components to be stripped from '
                          'the filenames in the patch. Default: %default.'))

  options, args = parser.parse_args()
  if args and not options.filter_script:
    parser.error('Unused args: %s' % args)

  if not (options.patch_url and options.root_dir):
    parser.error('A patch URL and root directory should be specified.')

  svn_cat = subprocess.Popen(['svn', 'cat', options.patch_url],
                             stdout=subprocess.PIPE)
  patch_input = svn_cat.stdout
  if options.filter_script:
    extra_args = args or []
    filtering = subprocess.Popen([sys.executable, options.filter_script,
                                  '--root-dir', options.root_dir] + extra_args,
                                 stdin=svn_cat.stdout, stdout=subprocess.PIPE,
                                 stderr=sys.stdout)
    patch_input = filtering.stdout
  patch = subprocess.Popen(['patch', '-t', '-p', str(options.strip_level),
                            '-d', options.root_dir],
                           stdin=patch_input)

  _, err = patch.communicate()
  return err or None


if __name__ == '__main__':
  sys.exit(main())
