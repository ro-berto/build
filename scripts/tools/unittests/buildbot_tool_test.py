#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for scripts/tools/buildbot_tool.py"""

import StringIO
import sys
import textwrap
import unittest

import test_env

from common import fake_filesystem
from tools import buildbot_tool


FAKE_MASTER_CFG_TEMPLATE = """\
# master_classname
%(master_classname)s

# buildbot_url
%(buildbot_url)s
"""

FAKE_BUILDERS_PYL = """\
{
  "git_repo_url": "git://example.com/example.git",
  "master_base_class": "Master1",
  "master_port": 10999,
  "master_port_alt": 20999,
  "master_type": "waterfall",
  "bot_port": 30999,
  "templates": ["templates"],
  "builders": {
    "fake builder": {
      "os": "linux",
      "recipe": "some_recipe",
      "version": "trusty",
      "bot": "vm1",
    },
  },
}
"""

GEN_MASTER_CFG = textwrap.dedent("""\
    # master_classname
    Test

    # buildbot_url
    https://build.chromium.org/p/test/
    """)


class FakeTool(buildbot_tool.Tool):
  def __init__(self, files):
    super(FakeTool, self).__init__()
    self.fs = fake_filesystem.FakeFilesystem(files)
    self.stdout = StringIO.StringIO()
    self.stderr = StringIO.StringIO()
    self.build_dir = '/build'
    self.build_internal_dir = '/build_internal'


class GenTest(unittest.TestCase):
  def test_one_master(self):
    files = {
      '/build/scripts/tools/buildbot_tool_templates/master.cfg':
          FAKE_MASTER_CFG_TEMPLATE,
      '/build/masters/master.test/builders.pyl': FAKE_BUILDERS_PYL,
    }
    tool = FakeTool(files)

    # Check that no files have been written.
    ret = tool.main(['check', '/build/masters/master.test'])
    self.assertEqual(ret, 1)

    # Check that we generate the files correctly.
    ret = tool.main(['gen', '/build/masters/master.test'])
    self.assertEqual(ret, 0)
    self.assertNotEqual(tool.stdout.getvalue(), '')
    self.assertEqual(tool.stderr.getvalue(), '')
    self.assertEqual(
        set(tool.fs.files.keys()),
        set(files.keys() + ['/build/masters/master.test/master.cfg']))
    self.assertMultiLineEqual(
        tool.fs.read_text_file('/build/masters/master.test/master.cfg'),
        GEN_MASTER_CFG)

    # Check that now everything is up to date.
    ret = tool.main(['check', '/build/masters/master.test'])
    self.assertEqual(ret, 0)

  def test_gen_all_masters(self):
    files = {
      '/build/scripts/tools/buildbot_tool_templates/master.cfg':
          FAKE_MASTER_CFG_TEMPLATE,
      '/build/masters/master.test/builders.pyl': FAKE_BUILDERS_PYL,
      '/build_internal/masters/master.internal/builders.pyl': FAKE_BUILDERS_PYL,
    }
    tool = FakeTool(files)
    fs = tool.fs
    ret = tool.main(['gen'])
    self.assertEqual(ret, 0)
    self.assertNotEqual(tool.stdout.getvalue(), '')
    self.assertEqual(tool.stderr.getvalue(), '')
    self.assertEqual(
        set(fs.files.keys()),
        set(files.keys() + [
            '/build/masters/master.test/master.cfg',
            '/build_internal/masters/master.internal/master.cfg']))
    self.assertMultiLineEqual(
        fs.read_text_file('/build/masters/master.test/master.cfg'),
        GEN_MASTER_CFG)
    self.assertMultiLineEqual(
        fs.read_text_file('/build_internal/masters/master.internal/master.cfg'),
        GEN_MASTER_CFG.replace('p/test', 'p/internal').replace(
            'Test', 'Internal'))

    ret = tool.main(['check'])
    self.assertEqual(ret, 0)

  def test_not_found(self):
    files = {
      '/build/masters/master.test/builders.pyl': None,
    }
    tool = FakeTool(files)
    ret = tool.main(['gen', '/build/masters/master.test'])
    self.assertEqual(ret, 1)
    self.assertEqual(tool.stdout.getvalue(), '')
    self.assertEqual(tool.stderr.getvalue(),
                     '/build/masters/master.test/builders.pyl not found\n')

  def test_no_masters(self):
    files = {}
    tool = FakeTool(files)
    ret = tool.main(['gen'])
    self.assertEqual(ret, 1)
    self.assertEqual(tool.stdout.getvalue(), '')
    self.assertEqual(tool.stderr.getvalue(), 'No builders.pyl files found.\n')

  def test_bad_template(self):
    files = {
      '/build/scripts/tools/buildbot_tool_templates/master.cfg':
        '%(unknown_key)s',
      '/build/masters/master.test/builders.pyl': FAKE_BUILDERS_PYL,
    }
    tool = FakeTool(files)
    self.assertRaises(KeyError, tool.main,
                      ['gen', '/build/masters/master.test'])


class HelpTest(unittest.TestCase):
  def test_help(self):
    # We do not care what the output is, just that the commands run.
    # We have to capture the output because argparse failures are written
    # directly to sys.stdout.
    tool = FakeTool({})
    orig_stdout = sys.stdout
    sys.stdout = StringIO.StringIO()
    try:
      self.assertRaises(SystemExit, tool.main, ['--help'])
      self.assertRaises(SystemExit, tool.main, ['help'])
      self.assertRaises(SystemExit, tool.main, ['help', 'gen'])
    finally:
      sys.stdout = orig_stdout


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()
