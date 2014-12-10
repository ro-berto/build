#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for scripts/tools/buildbot_tool.py"""

import StringIO
import sys
import textwrap
import unittest


# This adjusts sys.path, so it must be imported before the other modules.
import test_env

from common import fake_filesystem
from tools import buildbot_tool


SAMPLE_MASTER_CFG_TEMPLATE = """\
# builders_block
%(builders_block)s

# git_repo_url
%(git_repo_url)s

# master_dirname
%(master_dirname)s

# master_classname
%(master_classname)s

# master_base_class
%(master_base_class)s

# master_port
%(master_port)s

# master_port_alt
%(master_port_alt)s

# slave_port
%(slave_port)s
"""

SAMPLE_SLAVES_CFG_TEMPLATE = """\
%(slaves_block)s
"""

SAMPLE_BUILDERS_PY = """\
{
  "builders": {
    "Test Linux": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "slave_pools": ["main"],
      "slavebuilddir": "test"
    }
  },
  "git_repo_url": "https://chromium.googlesource.com/test/test.git",
  "master_base_class": "Master1",
  "master_port": 20999,
  "master_port_alt": 40999,
  "slave_port": 30999,
  "slave_pools": {
    "main": {
      "slave_data": {
        "bits": 64,
        "os":  "linux",
        "version": "precise"
      },
      "slaves": ["vm9999-m1"]
    }
  }
}
"""


def _trap_output():
  orig_output = (sys.stdout, sys.stderr)
  sys.stdout = StringIO.StringIO()
  sys.stderr = StringIO.StringIO()
  return orig_output


def _restore_output(orig_output):
  out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
  sys.stdout, sys.stderr = orig_output
  return out, err


def _stub_constants(new_values):
  orig = {}
  for k, v in new_values.items():
    orig[k] = getattr(buildbot_tool, k)
    setattr(buildbot_tool, k, v)
  return orig


def _restore_constants(orig_values):
  for k, v in orig_values.items():
    setattr(buildbot_tool, k, v)


class GenTest(unittest.TestCase):
  def test_normal(self):
    files = {
      '/build/templates/master.cfg': SAMPLE_MASTER_CFG_TEMPLATE,
      '/build/templates/slaves.cfg': SAMPLE_SLAVES_CFG_TEMPLATE,
      '/build/masters/master.test/builders.py': SAMPLE_BUILDERS_PY,
    }
    fs = fake_filesystem.FakeFilesystem(files=files.copy())

    orig_output = _trap_output()
    orig_constants = _stub_constants({
      'BASE_DIR': '/build',
      'TEMPLATE_SUBPATH': 'templates',
      'TEMPLATE_DIR': '/build/templates',
    })

    try:
      ret = buildbot_tool.main(['gen', '/build/masters/master.test'], fs)
    finally:
      out, err = _restore_output(orig_output)
      _restore_constants(orig_constants)

    self.assertEqual(ret, 0)
    self.assertEqual(err, '')
    self.assertNotEqual(out, '')
    self.assertEqual(set(fs.files.keys()),
                     set(files.keys() +
                         ['/build/masters/master.test/master.cfg',
                          '/build/masters/master.test/slaves.cfg']))

    self.assertMultiLineEqual(
        fs.read_text_file('/build/masters/master.test/master.cfg'),
        textwrap.dedent("""\
            # builders_block
            c['builders'].append({
              'name': 'Test Linux',
              'factory': m_annotator.BaseFactory('test_recipe'),
              'slavebuilddir': 'test'})


            # git_repo_url
            https://chromium.googlesource.com/test/test.git

            # master_dirname
            master.test

            # master_classname
            Test

            # master_base_class
            Master1

            # master_port
            20999

            # master_port_alt
            40999

            # slave_port
            30999
            """))

    self.assertMultiLineEqual(
        fs.read_text_file('/build/masters/master.test/slaves.cfg'),
        textwrap.dedent("""\
            slaves = [
              {
                'master': 'Test',
                'hostname': 'vm9999-m1',
                'builder': 'Test Linux',
                'os': 'linux',
                'version': 'precise',
                'bits': '64',
              },
            ]
            """))

  def test_not_found(self):
    files = {
      '/build/templates/master.cfg': SAMPLE_MASTER_CFG_TEMPLATE,
      '/build/templates/slaves.cfg': SAMPLE_SLAVES_CFG_TEMPLATE,
    }
    fs = fake_filesystem.FakeFilesystem(files=files.copy())

    orig_output = _trap_output()
    orig_constants = _stub_constants({
      'BASE_DIR': '/build',
      'TEMPLATE_SUBPATH': 'templates',
      'TEMPLATE_DIR': '/build/templates',
    })

    try:
      ret = buildbot_tool.main(['gen', '/build/masters/master.test'], fs)
    finally:
      out, err = _restore_output(orig_output)
      _restore_constants(orig_constants)

    self.assertEqual(ret, 1)
    self.assertEqual(out, '')
    self.assertEqual(err, '/build/masters/master.test not found\n')

  def test_bad_template(self):
    files = {
      '/build/templates/master.cfg': '%(unknown_key)s',
      '/build/masters/master.test/builders.py': SAMPLE_BUILDERS_PY,
    }
    fs = fake_filesystem.FakeFilesystem(files=files.copy())

    orig_output = _trap_output()
    orig_constants = _stub_constants({
      'BASE_DIR': '/build',
      'TEMPLATE_SUBPATH': 'templates',
      'TEMPLATE_DIR': '/build/templates',
    })

    try:
      self.assertRaises(KeyError,
                        buildbot_tool.main,
                        ['gen', '/build/masters/master.test'],
                        fs)
    finally:
      _restore_output(orig_output)
      _restore_constants(orig_constants)


class HelpTest(unittest.TestCase):
  def test_help(self):
    orig_output = _trap_output()
    fs = fake_filesystem.FakeFilesystem()
    try:
      # We do not care what the output is, just that the commands run.
      self.assertRaises(SystemExit, buildbot_tool.main, ['--help'], fs)
      self.assertRaises(SystemExit, buildbot_tool.main, ['help'], fs)
      self.assertRaises(SystemExit, buildbot_tool.main, ['help', 'gen'], fs)
    finally:
      _restore_output(orig_output)


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()
