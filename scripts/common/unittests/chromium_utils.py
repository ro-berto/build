#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in chromium_utils.py."""

import os
import sys
import tempfile
import unittest

import test_env  # pylint: disable=W0611

from common import chromium_utils


class FakeParser(object):
  def __init__(self):
    self.lines = []

  def ProcessLine(self, line):
    self.lines.append(line)


class FakeFilterObj(object):
  def __init__(self):
    self.lines = []

  def FilterLine(self, line):
    self.lines.append(line)

  # this is called when there is data without a trailing newline
  def FilterDone(self, line):
    self.lines.append(line)


def synthesizeCmd(args):
  basecmd = [sys.executable, '-c']
  basecmd.extend(args)
  return basecmd


class TestRunCommand(unittest.TestCase):

  def testRunCommandPlain(self):
    mycmd = synthesizeCmd(['exit()'])
    self.assertEqual(0, chromium_utils.RunCommand(mycmd, print_cmd=False))

  def testRunCommandParser(self):
    mycmd = synthesizeCmd(['print "1\\n2"'])
    parser = FakeParser()
    retval = chromium_utils.RunCommand(mycmd, print_cmd=False,
                                       parser_func=parser.ProcessLine)
    self.assertEqual(0, retval)
    self.assertEqual(['1', '2', ''], parser.lines)

  def testRunCommandFilter(self):
    mycmd = synthesizeCmd(['print "1\\n2"'])
    filter_obj = FakeFilterObj()
    retval = chromium_utils.RunCommand(mycmd, print_cmd=False,
                                       filter_obj=filter_obj)
    self.assertEqual(0, retval)
    self.assertEqual(['1\n', '2\n'], filter_obj.lines)

  def testRunCommandFilterEndline(self):
    mycmd = synthesizeCmd(['import sys; sys.stdout.write("test")'])
    filter_obj = FakeFilterObj()
    retval = chromium_utils.RunCommand(mycmd, print_cmd=False,
                                       filter_obj=filter_obj)
    self.assertEqual(0, retval)
    self.assertEqual(['test'], filter_obj.lines)

  def testRunCommandPipesParser(self):
    firstcmd = synthesizeCmd(['print "1\\n2"'])

    oneliner = "import sys; [sys.stdout.write(l.strip()+'1\\n') for l in "
    oneliner += "sys.stdin.readlines()]"
    secondcmd = synthesizeCmd([oneliner])
    parser = FakeParser()
    retval = chromium_utils.RunCommand(firstcmd, print_cmd=False,
                                       pipes=[secondcmd],
                                       parser_func=parser.ProcessLine)
    self.assertEqual(0, retval)
    self.assertEqual(['11', '21', ''], parser.lines)

  def testRunCommandPipesFilter(self):
    firstcmd = synthesizeCmd(['print "1\\n2"'])

    oneliner = "import sys; [sys.stdout.write(l.strip()+'1\\n') for l in "
    oneliner += "sys.stdin.readlines()]"
    secondcmd = synthesizeCmd([oneliner])
    filter_obj = FakeFilterObj()
    retval = chromium_utils.RunCommand(firstcmd, print_cmd=False,
                                       pipes=[secondcmd],
                                       filter_obj=filter_obj)
    self.assertEqual(0, retval)
    self.assertEqual(['11\n', '21\n'], filter_obj.lines)

  def testRunCommandPipesFailure(self):
    firstcmd = synthesizeCmd(['print "1"'])

    secondcmd = synthesizeCmd(["exit(1)"])
    filter_obj = FakeFilterObj()
    retval = chromium_utils.RunCommand(firstcmd, print_cmd=False,
                                       pipes=[secondcmd],
                                       filter_obj=filter_obj)
    self.assertEqual(1, retval)


SAMPLE_BUILDERS_PY = """\
{
  "builders": {
    "Test Linux": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "bot_pools": ["main"],
      "botbuilddir": "test"
    }
  },
  "git_repo_url": "https://chromium.googlesource.com/test/test.git",
  "master_base_class": "_FakeBaseMaster",
  "master_classname": "_FakeMaster",
  "master_port": 20999,
  "master_port_alt": 40999,
  "bot_port": 30999,
  "bot_pools": {
    "main": {
      "bot_data": {
        "bits": 64,
        "os":  "linux",
        "version": "precise"
      },
      "bots": ["vm9999-m1"],
    },
  },
  "templates": ["templates"],
}
"""


class GetBotsFromBuilders(unittest.TestCase):
  def test_normal(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_BUILDERS_PY)
      fp.close()

      bots = chromium_utils.GetBotsFromBuildersFile(fp.name)
      self.assertEqual([{
          'hostname': 'vm9999-m1',
          'builder': ['Test Linux'],
          'master': '_FakeMaster',
          'os': 'linux',
          'version': 'precise',
          'bits': 64,
      }], bots)
    finally:
      os.remove(fp.name)

  def test_range(self):
    # This tests that bash-style range expansion works for builder names.
    # The interval should be fully closed, i.e., x..y includes both x and y.
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_BUILDERS_PY.replace('vm9999-m1', 'vm{1..3}-m1'))
      fp.close()
      bots = chromium_utils.GetBotsFromBuildersFile(fp.name)
      self.assertEqual([
        {
          'hostname': 'vm1-m1',
          'builder': ['Test Linux'],
          'master': '_FakeMaster',
          'os': 'linux',
          'version': 'precise',
          'bits': 64,
        },
        {
          'hostname': 'vm2-m1',
          'builder': ['Test Linux'],
          'master': '_FakeMaster',
          'os': 'linux',
          'version': 'precise',
          'bits': 64,
        },
        {
          'hostname': 'vm3-m1',
          'builder': ['Test Linux'],
          'master': '_FakeMaster',
          'os': 'linux',
          'version': 'precise',
          'bits': 64,
        }], bots)
    finally:
      os.remove(fp.name)


  def test_hostname_syntax_and_expansion(self):
    expand = chromium_utils.ExpandBotsEntry
    self.assertEqual(['vm1'], expand('vm1'))
    self.assertEqual(['vm1-c1', 'vm12-c1'], expand('vm{1,12}-c1'))
    self.assertEqual(['vm11-c1', 'vm12-c1'], expand('vm{11..12}-c1'))

    # These have mismatched braces.
    self.assertRaises(ValueError, expand, 'vm{')
    self.assertRaises(ValueError, expand, 'vm{{')
    self.assertRaises(ValueError, expand, 'vm}{')
    self.assertRaises(ValueError, expand, 'vm{{}')

    # Only one set of braces is allowed.
    self.assertRaises(ValueError, expand, 'vm{1,2}{3,4}')

    # An empty set of braces is not allowed.
    self.assertRaises(ValueError, expand, 'vm{}')

    # Nested braces are not allowed.
    self.assertRaises(ValueError, expand, 'vm{{{}}}')

    # The start must be smaller than the end.
    self.assertRaises(ValueError, expand, 'vm{3..2}')

    # Mixing both ranges and lists is not allowed.
    self.assertRaises(ValueError, expand, 'vm{2..3,4}')

    # Spaces are not allowed.
    self.assertRaises(ValueError, expand, 'vm{2 ,4}')



if __name__ == '__main__':
  unittest.main()
