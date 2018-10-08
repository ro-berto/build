#!/usr/bin/env vpython
# coding=utf-8
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for sync_generated_files_codesearch."""

import os
import shutil
import tempfile
import unittest

import sync_generated_files as sync

class SyncGeneratedFilesCodesearchTest(unittest.TestCase):
  def setUp(self):
    super(SyncGeneratedFilesCodesearchTest, self).setUp()
    self.src_dir = tempfile.mkdtemp(suffix='_%s_src' % self._testMethodName)
    os.makedirs(os.path.join(self.src_dir, 'Debug', 'gen'))
    self.dest_dir = tempfile.mkdtemp(suffix='_%s_dest' % self._testMethodName)

  def tearDown(self):
    super(SyncGeneratedFilesCodesearchTest, self).tearDown()
    shutil.rmtree(self.src_dir)
    shutil.rmtree(self.dest_dir)

  def testCopyFilesBasic(self):
    with open(os.path.join(self.src_dir, 'Debug', 'gen', 'foo.cc'), 'w') as f:
      f.write('foo contents')

    sync.copy_generated_files(self.src_dir, self.dest_dir, 'Debug')

    try:
      self.assertEqual(
          open(os.path.join(
              self.dest_dir, 'Debug', 'gen', 'foo.cc'), 'r').read(),
          'foo contents')
    except IOError as e:
      self.fail(e)

  def testCopyFilesNested(self):
    os.makedirs(os.path.join(self.src_dir, 'Debug', 'gen', 'dir1'))
    os.makedirs(os.path.join(self.src_dir, 'Debug', 'gen', 'dir2', 'dir21'))
    with open(os.path.join(self.src_dir, 'Debug', 'gen', 'foo.cc'), 'w') as f:
      f.write('foo contents')
    with open(os.path.join(
        self.src_dir, 'Debug', 'gen', 'dir1', 'bar.css'), 'w') as f:
      f.write('bar contents')
    with open(os.path.join(
        self.src_dir, 'Debug', 'gen', 'dir2', 'baz.js'), 'w') as f:
      f.write('baz contents')
    with open(os.path.join(
        self.src_dir, 'Debug', 'gen', 'dir2', 'dir21', 'quux.json'), 'w') as f:
      f.write('quux contents')
    with open(os.path.join(
        self.src_dir, 'Debug', 'gen', 'dir2', 'dir21', 'zip.txt'), 'w') as f:
      f.write('zip contents')

    sync.copy_generated_files(self.src_dir, self.dest_dir, 'Debug')

    try:
      self.assertEqual(
          open(os.path.join(
              self.dest_dir, 'Debug', 'gen', 'foo.cc'), 'r').read(),
          'foo contents')
      self.assertEqual(
          open(os.path.join(
              self.dest_dir, 'Debug', 'gen', 'dir1', 'bar.css'), 'r').read(),
          'bar contents')
      self.assertEqual(
          open(os.path.join(
              self.dest_dir, 'Debug', 'gen', 'dir2', 'baz.js'), 'r').read(),
          'baz contents')
      self.assertEqual(
          open(os.path.join(
              self.dest_dir, 'Debug', 'gen', 'dir2', 'dir21', 'quux.json'),
               'r').read(),
          'quux contents')
      self.assertEqual(
          open(os.path.join(
              self.dest_dir, 'Debug', 'gen', 'dir2', 'dir21', 'zip.txt'),
               'r').read(),
          'zip contents')
    except IOError as e:
      self.fail(e)

  def testCopyFilesNotWhitelisted(self):
    with open(os.path.join(
        self.src_dir, 'Debug', 'gen', 'foo.crazy'), 'w') as f:
      f.write('foo contents')

    sync.copy_generated_files(self.src_dir, self.dest_dir, 'Debug')

    self.assertFalse(
        os.path.exists(os.path.join(
            self.dest_dir, 'Debug', 'gen', 'foo.crazy')))

  def testCopyFilesContentsChanged(self):
    with open(os.path.join(self.src_dir, 'Debug', 'gen', 'foo.cc'), 'w') as f:
      f.write('new foo contents')

    os.makedirs(os.path.join(self.dest_dir, 'Debug', 'gen'))
    with open(os.path.join(self.dest_dir, 'Debug', 'gen', 'foo.cc'), 'w') as f:
      f.write('old foo contents')

    sync.copy_generated_files(self.src_dir, self.dest_dir, 'Debug')

    try:
      self.assertEqual(
          open(os.path.join(
              self.dest_dir, 'Debug', 'gen', 'foo.cc'), 'r').read(),
          'new foo contents')
    except IOError as e:
      self.fail(e)

  def testCopyFilesDeleteNoLongerExistingFiles(self):
    with open(os.path.join(self.src_dir, 'Debug', 'gen', 'foo.cc'), 'w') as f:
      f.write('foo contents')

    os.makedirs(os.path.join(self.dest_dir, 'Debug', 'gen', 'the_dir'))
    with open(os.path.join(
        self.dest_dir, 'Debug', 'gen', 'the_dir', 'the_file.cc'), 'w') as f:
      f.write('the data')

    sync.copy_generated_files(self.src_dir, self.dest_dir, 'Debug')

    self.assertFalse(os.path.exists(os.path.join(
        self.dest_dir, 'Debug', 'gen', 'the_dir')))
    self.assertFalse(os.path.exists(os.path.join(
        self.dest_dir, 'Debug', 'gen', 'the_dir', 'the_file.cc')))

  def testCopyFilesDeleteNestedEmptyDirs(self):
    with open(os.path.join(self.src_dir, 'Debug', 'gen', 'foo.cc'), 'w') as f:
      f.write('foo contents')

    os.makedirs(os.path.join(
        self.dest_dir, 'Debug', 'gen', 'the_dir', 'inner_dir'))
    with open(os.path.join(
        self.dest_dir, 'Debug', 'gen', 'the_dir', 'inner_dir', 'the_file.cc'),
              'w') as f:
      f.write('the data')

    sync.copy_generated_files(self.src_dir, self.dest_dir, 'Debug')

    self.assertFalse(os.path.exists(
        os.path.join(self.dest_dir, 'Debug', 'gen', 'the_dir')))
    self.assertFalse(os.path.exists(
        os.path.join(self.dest_dir, 'Debug', 'gen', 'the_dir', 'inner_dir')))
    self.assertFalse(os.path.exists(
        os.path.join(self.dest_dir, 'Debug', 'gen', 'the_dir', 'inner_dir',
                     'the_file.cc')))

  def testCopyFilesDeleteExcludedFiles(self):
    os.makedirs(os.path.join(self.src_dir, 'Debug', 'gen', 'the_dir'))
    with open(os.path.join(self.src_dir, 'Debug', 'gen', 'foo.cc'), 'w') as f:
      f.write('foo contents')
    with open(os.path.join(
        self.src_dir, 'Debug', 'gen', 'the_dir', 'the_file.woah'), 'w') as f:
      f.write('the data')

    os.makedirs(os.path.join(self.dest_dir, 'Debug', 'gen', 'the_dir'))
    with open(os.path.join(
        self.dest_dir, 'Debug', 'gen', 'the_dir', 'the_file.woah'), 'w') as f:
      f.write('the data')

    sync.copy_generated_files(self.src_dir, self.dest_dir, 'Debug')

    self.assertFalse(os.path.exists(
        os.path.join(self.dest_dir, 'Debug', 'gen', 'the_dir')))
    self.assertFalse(os.path.exists(
        os.path.join(self.dest_dir, 'Debug', 'gen', 'the_dir',
                     'the_file.woah')))


if __name__ == '__main__':
  unittest.main()
