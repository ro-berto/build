#!/usr/bin/python
# Copyright (c) 2006-2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run the v8 tests.

  For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import shutil
import sys


import chromium_utils

def main(options, args):
  simultaneous = '-j3'
  if (options.platform == 'win'):
    simultaneous = ''

  if (options.testname == 'leak'):
    cmd = ['python', 'tools/test.py', '--no-build', '--mode',
           'debug', '--progress', 'verbose', '--timeout', '180',
           '--time', '-Snapshot=on', '--special-command',
           '"@ --nopreallocate-message-memory"',
           '--valgrind', 'mjsunit/leakcheck',
           'mjsunit/regress/regress-1134697', 'mjsunit/number-tostring-small']
  elif (options.testname == 'presubmit'):
    cmd = ['python', 'tools/presubmit.py']
  elif (options.testname):
    cmd = ['python', 'tools/test.py',
           simultaneous, options.testname,
           '--progress=verbose',
           '--no-build',
           '--arch=' + options.arch,
           '--mode=' + options.target]
  elif(options.simulator):
    cmd = ['python', 'tools/test.py',
           simultaneous,
           '--simulator', options.simulator,
           '--progress=verbose',
           '--no-build',
           '--arch=' + options.arch,
           '--mode=' + options.target]
  else:
    cmd = ['python', 'tools/test.py',
           simultaneous,
           '--timeout=180',
           '--progress=verbose',
           '--no-build',
           '--arch=' + options.arch,
           '--mode=' + options.target]
  return chromium_utils.RunCommand(cmd)


if '__main__' == __name__:
  if sys.platform in ('win32', 'cygwin'):
    default_platform = 'win'
  elif sys.platform.startswith('darwin'):
    default_platform = 'mac'
  elif sys.platform == 'linux2':
    default_platform = 'linux'
  else:
    default_platform = None

  option_parser = optparse.OptionParser()

  option_parser.add_option('', '--simulator',
                           default=None,
                           help='The simulator to run'
                                '[default: %default]')
  option_parser.add_option('', '--testname',
                           default=None,
                           help='The test to run'
                                '[default: %default]')
  option_parser.add_option('', '--target',
                           default='debug',
                           help='build target (Debug, Release) '
                                '[default: %default]')
  option_parser.add_option('', '--arch',
                           default='ia32',
                           help='Architecture (ia32, x64, arm) '
                                '[default: ia32]')
  option_parser.add_option('', '--build-dir',
                           default='bleeding_edge/obj',
                           metavar='DIR',
                           help='directory in which build was run '
                                '[default: %default]')
  option_parser.add_option('', '--platform',
                           default=default_platform,
                           help='specify platform [default: %%default]')

  options, args = option_parser.parse_args()

  sys.exit(main(options, args))

if __name__ == '__main__':
  sys.exit(main())
