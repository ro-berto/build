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
    self.src_root = self.formatDebugGenDir(self.src_dir)
    os.makedirs(self.src_root)

    self.dest_dir = tempfile.mkdtemp(suffix='_%s_dest' % self._testMethodName)
    self.dest_root = self.formatDebugGenDir(self.dest_dir)
    os.makedirs(self.dest_root)

  def tearDown(self):
    super(SyncGeneratedFilesCodesearchTest, self).tearDown()
    shutil.rmtree(self.src_dir)
    shutil.rmtree(self.dest_dir)

  def formatDebugGenDir(self, path):
    return os.path.join(path, 'Debug', 'gen')

  def testCopyFilesBasic(self):
    with open(os.path.join(self.src_root, 'foo.cc'), 'w') as f:
      f.write('foo contents')

    sync.copy_generated_files(self.src_root, self.dest_root)

    try:
      with open(os.path.join(self.dest_root, 'foo.cc'), 'r') as f:
        self.assertEqual(f.read(), 'foo contents')
    except IOError as e:
      self.fail(e)

  def testCopyFilesNested(self):
    os.makedirs(os.path.join(self.src_root, 'dir1'))
    os.makedirs(os.path.join(self.src_root, 'dir2', 'dir21'))
    with open(os.path.join(self.src_root, 'foo.cc'), 'w') as f:
      f.write('foo contents')
    with open(os.path.join(self.src_root, 'dir1', 'bar.css'), 'w') as f:
      f.write('bar contents')
    with open(os.path.join(self.src_root, 'dir2', 'baz.js'), 'w') as f:
      f.write('baz contents')
    with open(os.path.join(self.src_root, 'dir2', 'dir21', 'quux.json'),
              'w') as f:
      f.write('quux contents')
    with open(os.path.join(self.src_root, 'dir2', 'dir21', 'zip.txt'),
              'w') as f:
      f.write('zip contents')

    sync.copy_generated_files(self.src_root, self.dest_root)

    try:
      with open(os.path.join(self.dest_root, 'foo.cc'), 'r') as f:
        self.assertEqual(f.read(), 'foo contents')
      with open(os.path.join(self.dest_root, 'dir1', 'bar.css'), 'r') as f:
        self.assertEqual(f.read(), 'bar contents')
      with open(os.path.join(self.dest_root, 'dir2', 'baz.js'), 'r') as f:
        self.assertEqual(f.read(), 'baz contents')
      with open(
          os.path.join(self.dest_root, 'dir2', 'dir21', 'quux.json'), 'r') as f:
        self.assertEqual(f.read(), 'quux contents')
      with open(os.path.join(self.dest_root, 'dir2', 'dir21', 'zip.txt'),
                'r') as f:
        self.assertEqual(f.read(), 'zip contents')
    except IOError as e:
      self.fail(e)

  def testCopyFilesNotWhitelisted(self):
    with open(os.path.join(self.src_root, 'foo.crazy'), 'w') as f:
      f.write('foo contents')

    sync.copy_generated_files(self.src_root, self.dest_root)

    self.assertFalse(os.path.exists(os.path.join(self.dest_root, 'foo.crazy')))

  def testCopyFilesContentsChanged(self):
    with open(os.path.join(self.src_root, 'foo.cc'), 'w') as f:
      f.write('new foo contents')

    with open(os.path.join(self.dest_root, 'foo.cc'), 'w') as f:
      f.write('old foo contents')

    sync.copy_generated_files(self.src_root, self.dest_root)

    try:
      with open(os.path.join(self.dest_root, 'foo.cc'), 'r') as f:
        self.assertEqual(f.read(), 'new foo contents')
    except IOError as e:
      self.fail(e)

  def testCopyFilesDeleteNoLongerExistingFiles(self):
    with open(os.path.join(self.src_root, 'foo.cc'), 'w') as f:
      f.write('foo contents')

    os.makedirs(os.path.join(self.dest_root, 'the_dir'))
    with open(os.path.join(self.dest_root, 'the_dir', 'the_file.cc'), 'w') as f:
      f.write('the data')

    sync.copy_generated_files(self.src_root, self.dest_root)

    self.assertFalse(os.path.exists(os.path.join(self.dest_root, 'the_dir')))
    self.assertFalse(
        os.path.exists(os.path.join(self.dest_root, 'the_dir', 'the_file.cc')))

  def testCopyFilesDeleteNestedEmptyDirs(self):
    with open(os.path.join(self.src_root, 'foo.cc'), 'w') as f:
      f.write('foo contents')

    os.makedirs(os.path.join(self.dest_root, 'the_dir', 'inner_dir'))
    with open(
        os.path.join(self.dest_root, 'the_dir', 'inner_dir', 'the_file.cc'),
        'w') as f:
      f.write('the data')

    sync.copy_generated_files(self.src_root, self.dest_root)

    self.assertFalse(os.path.exists(os.path.join(self.dest_root, 'the_dir')))
    self.assertFalse(
        os.path.exists(os.path.join(self.dest_root, 'the_dir', 'inner_dir')))
    self.assertFalse(
        os.path.exists(
            os.path.join(self.dest_root, 'the_dir', 'inner_dir',
                         'the_file.cc')))

  def testCopyFilesDeleteExcludedFiles(self):
    os.makedirs(os.path.join(self.src_root, 'the_dir'))
    with open(os.path.join(self.src_root, 'foo.cc'), 'w') as f:
      f.write('foo contents')
    with open(os.path.join(self.src_root, 'the_dir', 'the_file.woah'),
              'w') as f:
      f.write('the data')

    os.makedirs(os.path.join(self.dest_root, 'the_dir'))
    with open(os.path.join(self.dest_root, 'the_dir', 'the_file.woah'),
              'w') as f:
      f.write('the data')

    sync.copy_generated_files(self.src_root, self.dest_root)

    self.assertFalse(os.path.exists(os.path.join(self.dest_root, 'the_dir')))
    self.assertFalse(
        os.path.exists(
            os.path.join(self.dest_root, 'the_dir', 'the_file.woah')))

  def testCopyFilesKzipSuffixSet(self):
    with open(os.path.join(self.src_root, 'foo.cc'), 'w') as f:
      f.write('foo contents')
    with open(os.path.join(self.src_root, 'bar.cc'), 'w') as f:
      f.write('bar contents')

    with open(os.path.join(self.dest_root, 'bar.cc'), 'w') as f:
      f.write('bar contents')
    with open(os.path.join(self.dest_root, 'baz.cc'), 'w') as f:
      f.write('baz contents')

    kzip_suffixes = set(('foo.cc',))

    # Files not mentioned in kzip should not be copied.
    sync.copy_generated_files(self.src_root, self.dest_root, kzip_suffixes)

    self.assertTrue(os.path.exists(os.path.join(self.dest_root, 'foo.cc')))
    self.assertFalse(os.path.exists(os.path.join(self.dest_root, 'bar.cc')))
    self.assertFalse(os.path.exists(os.path.join(self.dest_root, 'baz.cc')))


if __name__ == '__main__':
  unittest.main()
