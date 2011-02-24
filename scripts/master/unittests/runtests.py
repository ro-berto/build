#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to run Chrome build specific testcases in the current folder.

Modifies PYTHONPATH to automatically include parent, common and pylibs
directories.
Usage:
  runtests.py -f (<filename>|all) [-t testcasename]
"""

import os
import sys

RUNTESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(RUNTESTS_DIR, 'data')

sys.path.insert(0, os.path.join(RUNTESTS_DIR, '..', '..', '..', 'third_party',
                                'buildbot_7_12'))
sys.path.insert(0, os.path.join(RUNTESTS_DIR, '..', '..'))
sys.path.insert(0, os.path.join(RUNTESTS_DIR, '..', '..', '..', 'site_config'))

import optparse
import types
import unittest


parser = optparse.OptionParser()
parser.add_option('-f', '--file',
                  type='string',
                  action='store',
                  help="""Specify test file name. 'all' runs everything.""")

parser.add_option('-t', '--testcase',
                  type='string',
                  action='store',
                  help="""Specify testcase name.""")

opts, args = parser.parse_args()

if not opts.file:
  print """Please specify testcase file using '-f all|testfile' option."""
  sys.exit(-1)

if opts.testcase:
  test_name_prefix = opts.testcase
else:
  test_name_prefix = 'test'

def IsTestFile(entry):
  if opts.file == 'all':
    return entry.endswith('_test.py')
  else:
    return entry == opts.file

def IsTestCase(obj):
  return isinstance(obj, types.TypeType) and issubclass(obj, unittest.TestCase)

def main():
  suite = unittest.TestSuite()
  testmodules = []
  for entry in os.listdir(os.path.abspath(os.path.dirname(__file__))):
    if IsTestFile(entry):
      # remove .py to convert filename to module name
      testmodules.append(entry[0:-3])

  for testmodule in testmodules:
    m = __import__(testmodule)
    for module_attribute in m.__dict__.values():
      if IsTestCase(module_attribute):
        suite.addTest(unittest.makeSuite(module_attribute,
                                         prefix=test_name_prefix))

  unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
  main()
