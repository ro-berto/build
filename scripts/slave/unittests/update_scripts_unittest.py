#!/usr/bin/env vpython
"""Tests for update_scripts.

Note that this is very incomplete test coverage."""

import os
import unittest
import sys

import test_env  # pylint: disable=W0403,W0611

import mock
from slave import update_scripts

class FakeStream(object):
  def __init__(self):
    self.links = ()

  def step_link(self, name, url):
    self.links += ((name, url),)

class AddRevisionLinksTest(unittest.TestCase):
  @mock.patch('slave.update_scripts._run_command')
  def testSame(self, run_cmd):
    run_cmd.return_value = (0, 'old')
    s = FakeStream()
    update_scripts.add_revision_links(s, {
      'build': 'old',
    })

    self.assertEqual(s.links, (
      ('build: old',
       'https://chromium.googlesource.com/chromium/tools/build/+/old'),
    ))

  @mock.patch('sys.stderr')
  @mock.patch('slave.update_scripts._run_command')
  def testError(self, run_cmd, stderr):
    written = []
    def write_mock(line):
      written.append(line)
    stderr.write = write_mock

    run_cmd.return_value = (1, 'error wut')
    s = FakeStream()
    update_scripts.add_revision_links(s, {
      'build': 'old',
    })

    self.assertEqual(s.links, ())
    self.assertEqual(written, [
        'error while getting revision info for project \'build\''
        ' (return code was 1):\nerror wut'])

  @mock.patch('slave.update_scripts._run_command')
  def testDiff(self, run_cmd):
    run_cmd.return_value = (0, 'new')
    s = FakeStream()
    update_scripts.add_revision_links(s, {
      'build': 'old',
    })

    self.assertEqual(s.links, (
        ('build: old..new',
       'https://chromium.googlesource.com/chromium/tools/build/+log/old..new'),
    ))

  @mock.patch('slave.update_scripts._run_command')
  def testInfraCheckout(self, run_cmd):
    """Tests what happens if you have a build and depot_tools checkout"""
    values = [(0, 'newbuild'), (0, 'newdt')]
    def run_cmd_mock(*args, **kwargs):
      return values.pop(0)
    run_cmd.side_effect = run_cmd_mock
    s = FakeStream()

    update_scripts.add_revision_links(s, {
      'build': 'oldbuild',
      'depot_tools': 'olddt',
    })

    self.assertEqual(s.links, (
      ('build: oldbuild..newbuild',
       'https://chromium.googlesource.com/chromium/tools/'
       'build/+log/oldbuild..newbuild'),
      ('depot_tools: olddt..newdt',
       'https://chromium.googlesource.com/chromium/tools/'
       'depot_tools/+log/olddt..newdt'),
    ))

if __name__ == '__main__':
  unittest.main()
