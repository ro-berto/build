#!/usr/bin/env vpython
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in chromium_utils.py."""

import os
import sys
import tempfile
import unittest

import test_env

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


class TestSortableUploadPathForSortKey(unittest.TestCase):

  def testWithoutBranchName(self):
    self.assertEqual(
        chromium_utils.GetSortableUploadPathForSortKey('refs/heads/master', 1),
        '1'
    )
    self.assertEqual(
        chromium_utils.GetSortableUploadPathForSortKey('refs/heads/main', 1),
        '1'
    )

  def testWitBranchName(self):
    self.assertEqual(
        chromium_utils.GetSortableUploadPathForSortKey(
            'refs/heads/mainlike', 1
        ), 'refs_heads_mainlike-1'
    )
    self.assertEqual(
        chromium_utils.GetSortableUploadPathForSortKey(
            'refs/heads/branch-heads', 1
        ), 'refs_heads_branch-heads-1'
    )


if __name__ == '__main__':
  unittest.main()
