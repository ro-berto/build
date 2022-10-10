#!/usr/bin/env vpython3
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
    self.src_root = tempfile.mkdtemp(suffix='_%s_src' % self._testMethodName)
    self.dest_root = tempfile.mkdtemp(suffix='_%s_dest' % self._testMethodName)

  def tearDown(self):
    super(SyncGeneratedFilesCodesearchTest, self).tearDown()
    shutil.rmtree(self.src_root)
    shutil.rmtree(self.dest_root)

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

  def testCopyFilesWithSecrets(self):
    with open(os.path.join(self.src_root, 'foo.json'), 'w') as f:
      f.write('foo contents')
    with open(os.path.join(self.src_root, 'creds1.json'), 'w') as f:
      f.write('"accessToken": "ya29.c.dontuploadme"')
    with open(os.path.join(self.src_root, 'creds2.json'), 'w') as f:
      f.write('"code": "4/topsecret"')

    with open(os.path.join(self.dest_root, 'creds2.json'), 'w') as f:
      f.write('"code": "4/topsecret"')

    sync.copy_generated_files(self.src_root, self.dest_root)

    try:
      with open(os.path.join(self.dest_root, 'foo.json'), 'r') as f:
        self.assertEqual(f.read(), 'foo contents')
    except IOError as e:
      self.fail(e)

    try:
      with open(os.path.join(self.dest_root, 'creds1.json'), 'r') as f:
        self.fail('creds1.json should not be synced')
    except IOError as e:
      pass

    try:
      with open(os.path.join(self.dest_root, 'creds2.json'), 'r') as f:
        self.fail('creds2.json should have been deleted')
    except IOError as e:
      pass

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

  def testCopyFilesIgnore(self):
    with open(os.path.join(self.src_root, 'relevant.cc'), 'w') as f:
      f.write('relevant contents')
    with open(os.path.join(self.src_root, 'ignorefile.cc'), 'w') as f:
      f.write('ignorefile contents')
    os.makedirs(os.path.join(self.src_root, 'ignoredir'))
    with open(os.path.join(self.src_root, 'ignoredir', 'foo.cc'), 'w') as f:
      f.write('foo contents')

    with open(os.path.join(self.dest_root, 'ignorefile.cc'), 'w') as f:
      f.write('ignorefile contents')
    os.makedirs(os.path.join(self.dest_root, 'ignoredir'))
    with open(os.path.join(self.dest_root, 'ignoredir', 'foo.cc'), 'w') as f:
      f.write('foo contents')
    with open(os.path.join(self.dest_root, 'ignoredir', 'bar.cc'), 'w') as f:
      f.write('bar contents')

    ignore = set((
        os.path.join(self.src_root, 'ignoredir'),
        os.path.join(self.src_root, 'ignorefile.cc'),
    ))

    # Files not mentioned in kzip should not be copied.
    sync.copy_generated_files(
        self.src_root, self.dest_root, kzip_input_suffixes=None, ignore=ignore)

    self.assertTrue(os.path.exists(os.path.join(self.dest_root, 'relevant.cc')))
    self.assertFalse(
        os.path.exists(os.path.join(self.dest_root, 'ignoredir', 'foo.cc')))
    self.assertFalse(
        os.path.exists(os.path.join(self.dest_root, 'ignoredir', 'bar.cc')))
    self.assertFalse(os.path.exists(os.path.join(self.dest_root, 'ignoredir')))
    self.assertFalse(
        os.path.exists(os.path.join(self.dest_root, 'ignorefile.cc')))


if __name__ == '__main__':
  unittest.main()
