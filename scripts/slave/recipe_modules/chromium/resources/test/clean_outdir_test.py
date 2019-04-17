#!/usr/bin/env python
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for clean_outdir."""

from __future__ import print_function

import mock
import os
import sys
import time
import unittest
from datetime import datetime
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import clean_outdir


class CleanOutdirTest(unittest.TestCase):


  def setUp(self):
    # Setup the mock time to carry out the test
    self.curr_t = datetime.strptime('31st Dec 1999, 23:59:59',
                                    '%dst %b %Y, %H:%M:%S')

  @mock.patch('clean_outdir.os.walk')
  def test_get_files_recursive_1(self, os_walk):
    """Test Case: Empty directory"""
    feed_ip = [('/', [], [])]
    expected_op = set()
    os_walk.return_value = feed_ip

    self.assertSetEqual(expected_op, set(clean_outdir.get_files_recursive('/')))

  @mock.patch('clean_outdir.os.walk')
  def test_get_files_recursive_2(self, os_walk):
    """Test Case: Directory tree, max depth = 3"""
    feed_ip =   [ ('/', ['a', 'b'], ['1', '2']),
                  ('/a', [], ['3', '4']),
                  ('/b', ['c', 'd'], ['5', '6']),
                  ('/b/c', [], ['7', '8']),
                  ('/b/d', ['e'], ['9','10']),
                  ('/b/d/e', [], [])]
    expected_op = set(['/1', '/2', '/a/3', '/a/4', '/b/5', '/b/6', '/b/c/7',
                       '/b/c/8', '/b/d/9', '/b/d/10'])
    os_walk.return_value = feed_ip
    self.assertSetEqual(expected_op, set(clean_outdir.get_files_recursive('/')))

  @mock.patch('clean_outdir.get_files_recursive')
  def test_get_old_files_in_dir_1(self, get_files_recursive):
    """Test Case: Empty directory"""
    feed_ip = []
    expected_op = set()
    get_files_recursive.return_value = feed_ip
    return_val = set(clean_outdir.get_old_files_in_dir('/', timedelta(days=7)))
    self.assertSetEqual(expected_op, return_val)

  @mock.patch('clean_outdir.get_time_now')
  @mock.patch('clean_outdir.os.path.islink')
  @mock.patch('clean_outdir.os.path.getmtime')
  @mock.patch('clean_outdir.get_files_recursive')
  def test_get_old_files_in_dir_2(self, get_files_recursive,
                                  os_path_getmtime,
                                  os_path_islink,
                                  get_time_now):
    """Test Case: Directory without any 'old' files"""
    curr_t = self.curr_t

    feed_ip = ['/1', '/2', '/a/3', '/a/4', '/b/5', '/b/6', '/b/c/7', '/b/c/8',
               '/b/d/9', '/b/d/10']

    time_matrix = {'/1': curr_t, '/2': curr_t, '/a/3': curr_t, '/a/4': curr_t,
                   '/b/5': curr_t, '/b/6': curr_t, '/b/c/7': curr_t,
                   '/b/c/8': curr_t, '/b/d/9': curr_t, '/b/d/10': curr_t}

    expected_op = set()

    def _patch_os_path_getmtime(path):
      return time.mktime(time_matrix[path].timetuple())

    get_time_now.return_value = curr_t
    os_path_getmtime.side_effect = _patch_os_path_getmtime
    os_path_islink.return_value = False
    get_files_recursive.return_value = feed_ip

    res = set(clean_outdir.get_old_files_in_dir('/', timedelta(days=7)))
    self.assertSetEqual(expected_op, res)

  @mock.patch('clean_outdir.get_time_now')
  @mock.patch('clean_outdir.os.path.islink')
  @mock.patch('clean_outdir.os.path.getmtime')
  @mock.patch('clean_outdir.get_files_recursive')
  def test_get_old_files_in_dir_3(self, get_files_recursive,
                                  os_path_getmtime,
                                  os_path_islink,
                                  get_time_now):
    """Test Case: Directory where all files are old"""
    feed_ip = ['/1', '/2', '/a/3', '/a/4', '/b/5', '/b/6', '/b/c/7', '/b/c/8',
               '/b/d/9', '/b/d/10']

    curr_t = self.curr_t
    time_diff = timedelta(days=8)
    old_t = curr_t - time_diff

    time_matrix = {'/1': old_t, '/2': old_t, '/a/3': old_t, '/a/4': old_t,
                   '/b/5': old_t, '/b/6': old_t, '/b/c/7': old_t,
                   '/b/c/8': old_t, '/b/d/9': old_t, '/b/d/10': old_t}

    expected_op = set([('/1', time_diff), ('/2', time_diff),
                       ('/a/3', time_diff), ('/a/4', time_diff),
                       ('/b/5', time_diff), ('/b/6', time_diff),
                       ('/b/c/7', time_diff), ('/b/c/8', time_diff),
                       ('/b/d/9', time_diff), ('/b/d/10', time_diff)])

    def _patch_os_path_getmtime(path):
      return time.mktime(time_matrix[path].timetuple())

    get_time_now.return_value = curr_t
    os_path_getmtime.side_effect = _patch_os_path_getmtime
    os_path_islink.return_value = False
    get_files_recursive.return_value = feed_ip

    res = set(clean_outdir.get_old_files_in_dir('/', timedelta(days=7)))
    self.assertSetEqual(expected_op, res)


  @mock.patch('clean_outdir.get_time_now')
  @mock.patch('clean_outdir.os.path.islink')
  @mock.patch('clean_outdir.os.path.getmtime')
  @mock.patch('clean_outdir.get_files_recursive')
  def test_get_old_files_in_dir_4(self, get_files_recursive,
                                  os_path_getmtime,
                                  os_path_islink,
                                  get_time_now):
    """Test Case: Directory containing both old and new files"""
    feed_ip = ['/1', '/2', '/a/3', '/a/4', '/b/5', '/b/6', '/b/c/7', '/b/c/8',
               '/b/d/9', '/b/d/10']
    curr_t = self.curr_t
    time_diff = timedelta(days=8)
    old_t = curr_t - time_diff

    time_matrix = {'/1': old_t, '/2': curr_t, '/a/3': curr_t, '/a/4': old_t,
                   '/b/5': curr_t, '/b/6': old_t, '/b/c/7': old_t,
                   '/b/c/8': old_t, '/b/d/9': curr_t, '/b/d/10': old_t}

    expected_op = set([('/1', time_diff), ('/a/4', time_diff),
                       ('/b/6', time_diff), ('/b/c/7', time_diff),
                       ('/b/c/8', time_diff), ('/b/d/10', time_diff)])

    def _patch_os_path_getmtime(path):
      return time.mktime(time_matrix[path].timetuple())

    get_time_now.return_value = curr_t
    os_path_getmtime.side_effect = _patch_os_path_getmtime
    os_path_islink.return_value = False
    get_files_recursive.return_value = feed_ip

    res = set(clean_outdir.get_old_files_in_dir('/', timedelta(days=7)))
    self.assertSetEqual(expected_op, res)

  @mock.patch('clean_outdir.get_time_now')
  @mock.patch('clean_outdir.os.path.islink')
  @mock.patch('clean_outdir.os.path.getmtime')
  @mock.patch('clean_outdir.get_files_recursive')
  def test_get_old_files_in_dir_5(self, get_files_recursive,
                                  os_path_getmtime,
                                  os_path_islink,
                                  get_time_now):
    """Test Case: Ignoring sym links in a directory"""
    feed_ip = ['/1', '/2', '/a/3', '/a/4', '/b/5', '/b/6', '/b/c/7', '/b/c/8',
               '/b/d/9', '/b/d/10']

    curr_t = self.curr_t
    time_diff = timedelta(days=8)
    old_t = curr_t - time_diff

    time_matrix = {'/1':  old_t, '/2':  old_t, '/a/3':  old_t, '/a/4':  old_t,
                   '/b/5':  old_t, '/b/6':  old_t, '/b/c/7':  old_t,
                   '/b/c/8':  old_t, '/b/d/9':  old_t, '/b/d/10':  old_t}

    linked_files = set(['/1', '/a/3', '/b/6', '/b/c/7', '/b/d/10'])
    expected_op = set([('/2', time_diff), ('/a/4', time_diff),
                       ('/b/5', time_diff), ('/b/d/9', time_diff),
                       ('/b/c/8', time_diff)])

    def _patch_os_path_islink(path):
      return path in linked_files

    def _patch_os_path_getmtime(path):
      return time.mktime(time_matrix[path].timetuple())

    get_time_now.return_value = curr_t
    os_path_getmtime.side_effect = _patch_os_path_getmtime
    os_path_islink.side_effect = _patch_os_path_islink
    get_files_recursive.return_value = feed_ip

    res = set(clean_outdir.get_old_files_in_dir('/', timedelta(days=7)))
    self.assertSetEqual(expected_op, res)

  def test_main_1(self):
    """Test Case: Negative time difference"""
    sys_argv = ['clean_outdir.py', '--days-old', '-10', '/tmp/clean_outdir']
    self.assertEqual(-1, clean_outdir.main(sys_argv))

  @mock.patch('clean_outdir.os.path.exists')
  def test_main_2(self, os_path_exists):
    """Test Case: Non existent out directory"""
    sys_argv = ['clean_outdir.py', '/tmp/clean_outdir']
    os_path_exists.return_value = False
    self.assertEqual(-1, clean_outdir.main(sys_argv))

  @mock.patch('clean_outdir.os.remove')
  @mock.patch('clean_outdir.os.path.exists')
  @mock.patch('clean_outdir.get_old_files_in_dir')
  def test_main_3(self, get_old_files_in_dir,
                  os_path_exists,
                  os_remove):
    """Test Case: Empty directory"""
    sys_argv = ['clean_outdir.py', '--days-old', '10', '/tmp/clean_outdir']
    feed_ip = []
    remove_calls_log = set()

    def _patch_os_remove(fname):
      remove_calls_log.add(fname)

    get_old_files_in_dir.return_value = feed_ip
    os_path_exists.return_value = True
    os_remove.side_effect = _patch_os_remove
    clean_outdir.main(sys_argv)
    self.assertSetEqual(remove_calls_log, set())

  @mock.patch('clean_outdir.os.remove')
  @mock.patch('clean_outdir.os.path.exists')
  @mock.patch('clean_outdir.get_old_files_in_dir')
  def test_main_4(self, get_old_files_in_dir, os_path_exists, os_remove):
    """Test Case: Directory containing files"""
    time_diff = timedelta(days=8)

    feed_ip = [('/tmp/clean_outdir/1', time_diff),
               ('/tmp/clean_outdir/2', time_diff),
               ('/tmp/clean_outdir/a/3', time_diff),
               ('/tmp/clean_outdir/a/4', time_diff),
               ('/tmp/clean_outdir/b/5', time_diff),
               ('/tmp/clean_outdir/b/6', time_diff),
               ('/tmp/clean_outdir/b/c/7', time_diff),
               ('/tmp/clean_outdir/b/c/8', time_diff),
               ('/tmp/clean_outdir/b/d/9', time_diff),
               ('/tmp/clean_outdir/b/d/10', time_diff)]

    expected_op = set(['/tmp/clean_outdir/1',
                       '/tmp/clean_outdir/2',
                       '/tmp/clean_outdir/a/3',
                       '/tmp/clean_outdir/a/4',
                       '/tmp/clean_outdir/b/5',
                       '/tmp/clean_outdir/b/6',
                       '/tmp/clean_outdir/b/c/7',
                       '/tmp/clean_outdir/b/c/8',
                       '/tmp/clean_outdir/b/d/9',
                       '/tmp/clean_outdir/b/d/10'])

    sys_argv = ['clean_outdir.py',  '/tmp/clean_outdir']

    remove_calls_log = set()

    def _patch_os_remove(fname):
      remove_calls_log.add(fname)

    os_path_exists.return_value = True
    os_remove.side_effect = _patch_os_remove
    get_old_files_in_dir.return_value = feed_ip

    clean_outdir.main(sys_argv)
    self.assertSetEqual(expected_op, remove_calls_log)


if __name__ == '__main__':
  unittest.main()
