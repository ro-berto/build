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
import optparse
import types
import unittest

RUNTESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(RUNTESTS_DIR, 'data')
BASE_DIR = os.path.abspath(os.path.join(RUNTESTS_DIR, '..', '..', '..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'third_party'))
sys.path.insert(0, os.path.join(BASE_DIR, 'third_party', 'twisted_8_1'))
sys.path.insert(0, os.path.join(BASE_DIR, 'third_party', 'buildbot_7_12'))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
sys.path.insert(0, os.path.join(BASE_DIR, 'site_config'))


def IsTestFile(options, entry):
  if options.file == 'all':
    return entry.endswith('_test.py')
  else:
    return entry == options.file


def IsTestCase(obj):
  return (isinstance(obj, types.TypeType) and
      issubclass(obj, unittest.TestCase))


def run_tests(options, test_name_prefix):
  suite = unittest.TestSuite()
  testmodules = []
  for entry in os.listdir(os.path.abspath(os.path.dirname(__file__))):
    if IsTestFile(options, entry):
      # remove .py to convert filename to module name
      testmodules.append(entry[0:-3])

  for testmodule in testmodules:
    m = __import__(testmodule)
    for module_attribute in m.__dict__.values():
      if IsTestCase(module_attribute):
        suite.addTest(unittest.makeSuite(module_attribute,
                                         prefix=test_name_prefix))
  unittest.TextTestRunner().run(suite)


def main():
  parser = optparse.OptionParser()
  parser.add_option('-f', '--file',
                    type='string',
                    action='store',
                    default='all',
                    help="Specify test file name. 'all' runs everything.")
  parser.add_option('-t', '--testcase',
                    type='string',
                    action='store',
                    help="Specify testcase name.")
  options, args = parser.parse_args()
  if args:
    parser.error('No unsupported args please')
  if not options.file:
    parser.error("Please specify testcase file using '-f all|testfile' option.")
  if options.testcase:
    test_name_prefix = options.testcase
  else:
    test_name_prefix = 'test'
  return run_tests(options, test_name_prefix)


if __name__ == '__main__':
  sys.exit(main())
