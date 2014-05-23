#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import imp
import json
import os
from subprocess import Popen, PIPE
import sys
import tempfile
import threading
import unittest

BUILD_DIR = os.path.realpath(os.path.join(
    os.path.dirname(__file__), '..'))
BOT_UPDATE_PATH = os.path.join(BUILD_DIR, 'scripts', 'slave', 'bot_update.py')
SLAVE_DIR = os.path.join(BUILD_DIR, 'slave')

chromium_utils = imp.load_source(
    'chromium_utils',
    os.path.join(BUILD_DIR, 'scripts', 'common', 'chromium_utils.py'))


class BotUpdateTest(unittest.TestCase):
  # TODO(szager): Maybe replace this with a local temporary gerrit instance.
  GIT_HOST = 'https://t3st-chr0m3.googlesource.com'

  def setUp(self):
    prefix = self.id().lstrip('__main__.')
    testname = prefix.split('.')[-1]
    self.workdir = tempfile.mkdtemp(dir=SLAVE_DIR, prefix=prefix)
    self.builddir = os.path.join(self.workdir, 'build')
    os.mkdir(self.builddir)
    self.bu_cmd = [
        sys.executable, BOT_UPDATE_PATH, '--force',
        '--output_json', os.path.join(self.builddir, 'out.json'),
        '--master', '%s_master' % testname,
        '--builder_name', '%s_builder' % testname,
        '--slave_name', '%s_slave' % testname ]

  def tearDown(self):
    chromium_utils.RemoveDirectory(self.workdir)

  @staticmethod
  def _subproc_thread_main(cmd, cwd):
    thr = threading.current_thread()
    thr.p = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=cwd)
    (stdout, stderr) = thr.p.communicate()
    thr.stdout = stdout
    thr.stderr = stderr

  def _subproc(self, cmd, cwd, timeout=15):
    thr = threading.Thread(
        target=self._subproc_thread_main, args=(cmd, cwd))
    thr.daemon = True
    thr.start()
    thr.join(timeout)
    if thr.isAlive():
      thr.p.terminate()
      self.fail('A subprocess timed out after %d seconds' % timeout)
    return (thr.p.returncode, thr.stdout, thr.stderr)

  @staticmethod
  def _dump_subproc(cmd, cwd, status, stdout, stderr):
    sep = ('#' * 80) + '\n'
    print sep, 'Subprocess failed with status %d.\n' % status
    print cmd, '\n\n... in %s\n' % cwd
    print sep, '# stdout\n', sep, stdout, '\n'
    print sep, '# stderr\n', sep, stderr, '\n', sep

  @staticmethod
  def _get_files(d):
    result = []
    for dirpath, dirnames, filenames in os.walk(d):
      for f in filenames:
        result.append(
            os.path.join(dirpath.replace(d, '').lstrip('/'), f))
      try:
        dirnames.remove('.git')
      except ValueError:
        pass
    return result

  def test_001_simple(self):
    solution = { 'name': 'top',
                 'url': '%s/BotUpdateTest/test_001_top.git' % self.GIT_HOST,
                 'deps_file': 'DEPS' }
    gclient_spec = 'solutions=[%r]' % solution
    self.bu_cmd.extend([
        '--post-flag-day',
        '--specs', gclient_spec,
        '--revision', '91ea82d7125be47db12ccb973a2c6574eca0f342'])
    status, stdout, stderr = self._subproc(self.bu_cmd, self.builddir)
    if status != 0:
      self._dump_subproc(self.bu_cmd, self.builddir, status, stdout, stderr)
    self.assertEqual(status, 0)
    expected_files = [
        'DEPS',
        'file.txt',
        'ext/dep1/file.txt',
        'ext/dep2/file.txt',
    ]
    topdir = os.path.join(self.builddir, 'top')
    self.assertItemsEqual(expected_files, self._get_files(topdir))
    expected_json = {
        'root': 'top',
        'properties': {},
        'did_run': True,
        'patch_root': None
    }
    with open(os.path.join(self.builddir, 'out.json')) as fh:
      actual_json = json.load(fh)
    self.assertDictContainsSubset(expected_json, actual_json)


if __name__ == '__main__':
  unittest.main()
