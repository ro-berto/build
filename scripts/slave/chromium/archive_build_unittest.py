#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import os.path
import shutil
import simplejson
import tempfile
import unittest
import sys
import zipfile

BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path.append(os.path.join(BASE_DIR, 'scripts'))
sys.path.append(os.path.join(BASE_DIR, 'site_config'))

from slave.chromium import archive_build
from common import chromium_utils
import config


TEMP_FILES = ['foo.txt',
              'bar.txt',
              os.path.join('foo', 'buzz.txt'),
              os.path.join('foo', 'bing'),
              os.path.join('fee', 'foo', 'bar'),
              os.path.join('fee', 'faa', 'bar'),
              os.path.join('fee', 'fie', 'fo'),
              os.path.join('foo', 'fee', 'faa', 'boo.txt')]

DIR_LIST = ['foo',
            os.path.join('fee', 'foo'),
            os.path.join('fee', 'faa'),
            os.path.join('fee', 'fie'),
            os.path.join('foo', 'fee', 'faa')]

TEMP_FILES_WITH_WILDCARDS = ['foo.txt',
                             'bar.txt',
                             os.path.join('foo', '*'),
                             os.path.join('fee', '*', 'bar'),
                             os.path.join('fee', '*', 'fo'),
                             os.path.join('foo', 'fee', 'faa', 'boo.txt')]

# Sample FILES.cfg-style contents.
TEST_FILES_CFG = [
  {
    'filename': 'allany.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
  },
  {
    'filename': 'official64.txt',
    'arch': ['64bit'],
    'buildtype': ['official'],
  },
  {
    'filename': 'dev32.txt',
    'arch': ['32bit'],
    'buildtype': ['dev'],
  },
]

ZIP_TEST_FILES = ['file1.txt',
                  'file2.txt',
                  'file3.txt']

EXTRA_ZIP_TEST_FILES = ['extra1.txt',
                        'extra2.txt',
                        'extra3.txt']

TEST_FILES = ['test1.exe',
              'test2.exe',
              os.path.join('dir1', 'test3.exe')]

TEST_FILES_NO_DEEP_DIRS = ['test1.exe',
                           'test2.exe']

EXTRA_TEST_FILES = ['extra_test1.exe',
                    'extra_test2.exe',
                    os.path.join('extra_dir1', 'extra_test3.exe')]


class MockOptions(object):
  """ Class used to mock the optparse options object for the Stager.
  """
  def __init__(self, src_dir, build_dir, target, archive_path,
               extra_archive_paths, build_number, default_chromium_revision,
               default_webkit_revision, default_v8_revision):
    self.src_dir = src_dir
    self.build_dir = build_dir
    self.target = target
    self.dirs = {
      'www_dir_base': archive_path,
      'symbol_dir_base': archive_path,
    }
    self.extra_archive_paths = extra_archive_paths
    self.build_number = build_number
    self.default_chromium_revision = default_chromium_revision
    self.default_webkit_revision = default_webkit_revision
    self.default_v8_revision = default_v8_revision
    self.installer = config.Archive.installer_exe
    self.factory_properties = {}


class PlatformError(Exception): pass
class InternalStateError(Exception): pass


class ArchiveTest(unittest.TestCase):
  # Attribute '' defined outside __init__
  # pylint: disable=W0201

  def setUp(self):
    self.temp_dir = tempfile.mkdtemp()
    self.temp_files = TEMP_FILES

    # Build up the temp files
    for temp_file in self.temp_files:
      temp_path = os.path.join(self.temp_dir, temp_file)
      dir_name = os.path.dirname(temp_path)

      if not os.path.exists(temp_path):
        relative_dir_name = os.path.dirname(temp_file)
        if relative_dir_name and not os.path.exists(dir_name):
          os.makedirs(dir_name)
        open(temp_path, 'a')

    # Make some directories to make the stager happy.
    self.target = 'Test'
    if chromium_utils.IsWindows():
      self.build_dir = os.path.join(self.temp_dir, 'build')
    elif chromium_utils.IsLinux():
      self.build_dir = os.path.join(self.temp_dir, 'out')
    elif chromium_utils.IsMac():
      self.build_dir = os.path.join(self.temp_dir, 'xcodebuild')
    else:
      raise PlatformError(
          'Platform "%s" is not currently supported.' % sys.platform)
    os.makedirs(os.path.join(self.build_dir, self.target))
    self.src_dir = os.path.join(self.temp_dir, 'build', 'src')
    os.makedirs(self.src_dir)
    self.archive_dir = os.path.join(self.temp_dir, 'archive')
    os.makedirs(self.archive_dir)
    # Make a directory to hold an extra files and tests specifier:
    self.extra_files_dir = os.path.join(self.temp_dir, 'build', 'src', 'extra')
    os.makedirs(self.extra_files_dir)

    # Create the FILES file and seed with contents:
    self.extra_files = os.path.join(self.extra_files_dir, 'FILES')
    extra_file = open(self.extra_files, 'w')
    for f in ZIP_TEST_FILES:
      extra_file.write(f + '\n')
    extra_file.close()

    # Create the TESTS file and seed with contents:
    self.extra_tests = os.path.join(self.extra_files_dir, 'TESTS')
    extra_tests = open(self.extra_tests, 'w')
    for t in EXTRA_TEST_FILES:
      extra_tests.write(t + '\n')
    extra_tests.close()
    # The stager object will be initialized in initializeStager method.
    self.stager = None

  def initializeStager(self, build_number=None, default_chromium_revision=None,
                       default_webkit_revision=None, default_v8_revision=None):
    self.options = MockOptions(self.src_dir, self.build_dir, self.target,
                               self.archive_dir, self.extra_files_dir,
                               build_number, default_chromium_revision,
                               default_webkit_revision, default_v8_revision)
    if self.options.build_number:
      self.stager = archive_build.StagerByBuildNumber(self.options)
    else:
      self.stager = archive_build.StagerByChromiumRevision(self.options)

  def tearDown(self):
    shutil.rmtree(self.temp_dir)

  def prepareToolDir(self):
    # Build up a directory for Zip file testing
    if chromium_utils.IsWindows():
      self.tool_dir = 'chrome/tools/build/win'
    elif chromium_utils.IsLinux():
      self.tool_dir = 'chrome/tools/build/linux'
    elif chromium_utils.IsMac():
      self.tool_dir = 'chrome/tools/build/mac'
    else:
      raise PlatformError(
          'Platform "%s" is not currently supported.' % sys.platform)
    self.tool_dir = os.path.join(self.src_dir, self.tool_dir)
    os.makedirs(self.tool_dir)

  def createFileSetInBuildDir(self, file_list):
    for f in file_list:
      dir_part = os.path.dirname(f)
      if (dir_part):
        dir_path = os.path.join(self.build_dir, self.target, dir_part)
        os.makedirs(dir_path)

      temp_file = open(os.path.join(self.build_dir, self.target, f), 'w')
      temp_file.write('contents')
      temp_file.close()

  def createZipFileTestDir(self):
    self.prepareToolDir()

    self.FILES = os.path.join(self.tool_dir, 'FILES.cfg')
    f = open(self.FILES, 'w')
    f.write("FILES = %s" % str(TEST_FILES_CFG))
    f.close()

    self.EMPTY_FILES = os.path.join(self.tool_dir, 'EMPTY_FILES')
    f = open(self.EMPTY_FILES, 'a')

    self.createFileSetInBuildDir(ZIP_TEST_FILES + EXTRA_ZIP_TEST_FILES +
                                 [i['filename'] for i in TEST_FILES_CFG])

  def createTestFiles(self, file_list):
    self.prepareToolDir()

    self.TESTS = os.path.join(self.tool_dir, 'TESTS')
    f = open(self.TESTS, 'w')
    f.write('\n'.join(file_list))
    f.close()

    self.createFileSetInBuildDir(file_list)

  def createExtraTestFiles(self):
    if not self.tool_dir:
      raise InternalStateError('createTestFiles must be called first')

    for tf in EXTRA_TEST_FILES:
      dir_part = os.path.dirname(tf)
      if (dir_part):
        dir_path = os.path.join(self.build_dir, dir_part)
        os.makedirs(dir_path)

      test_file = open(os.path.join(self.build_dir, tf), 'w')
      test_file.write('contents')
      test_file.close()

  def verifyZipFile(self, zip_dir, zip_file_path, archive_name, expected_files):
    # Extract the files from the archive
    extract_dir = os.path.join(zip_dir, 'extract')
    os.makedirs(extract_dir)
    zip_file = zipfile.ZipFile(zip_file_path)
    # The extractall method is supported from V2.6
    if hasattr(zip_file, 'extractall'):
      zip_file.extractall(extract_dir)  # pylint: disable=E1101
      # Check that all expected files are there
      extracted_files = os.listdir(os.path.join(extract_dir, archive_name))
      self.assertEquals(len(expected_files), len(extracted_files))
      for f in extracted_files:
        self.assertTrue(f in expected_files)
    else:
      test_result = zip_file.testzip()
      self.assertTrue(not test_result)

    zip_file.close()

  def testExpandWildcards(self):
    path_list = TEMP_FILES_WITH_WILDCARDS[:]
    expected_path_list = TEMP_FILES[:]
    expected_path_list.sort()

    self.initializeStager()
    expanded_path_list = archive_build.ExpandWildcards(self.temp_dir, path_list)
    expanded_path_list.sort()
    self.assertEquals(expected_path_list, expanded_path_list)

  def testExtractDirsFromPaths(self):
    path_list = TEMP_FILES[:]
    expected_dir_list = DIR_LIST[:]
    expected_dir_list.sort()

    self.initializeStager()
    dir_list = archive_build.ExtractDirsFromPaths(path_list)
    dir_list.sort()
    self.assertEquals(expected_dir_list, dir_list)

  def testGetExtraFiles(self):
    expected_extra_files_list = ZIP_TEST_FILES[:]
    expected_extra_files_list.sort()

    self.initializeStager()
    extra_files_list = self.stager.GetExtraFiles('extra', 'FILES')
    extra_files_list.sort()

    self.assertEquals(expected_extra_files_list, extra_files_list)

  def testCreateArchiveFile(self):
    self.createZipFileTestDir()

    self.initializeStager()
    archive_name = 'test'
    arch = '64bit'
    buildtype = 'official'
    files_list = self.stager.ParseFilesList(buildtype, arch)
    # Verify FILES.cfg was parsed correctly.
    for i in TEST_FILES_CFG:
      if arch in i['arch'] and buildtype in i['buildtype']:
        self.assertTrue(i['filename'] in files_list)
    zip_dir, zip_file_path = self.stager.CreateArchiveFile(archive_name,
                                                           files_list)
    self.assertTrue(zip_dir)
    self.assertTrue(zip_file_path)
    self.assertTrue(os.path.exists(zip_file_path))
    self.verifyZipFile(zip_dir, zip_file_path, archive_name, files_list)

  def testCreateEmptyArchiveFile(self):
    self.createZipFileTestDir()
    self.initializeStager()
    zip_dir, zip_file = self.stager.CreateArchiveFile('test_empty',
        os.path.basename(self.EMPTY_FILES))
    self.assertFalse(zip_dir)
    self.assertFalse(zip_file)
    self.assertFalse(os.path.exists(zip_file))

  def testUploadTests(self):
    # This test is currently only applicable on Windows.
    if not chromium_utils.IsWindows():
      return

    self.createTestFiles(TEST_FILES)
    self.initializeStager()
    self.stager.UploadTests(self.archive_dir)

    expected_archived_tests = TEST_FILES
    archived_tests = os.listdir(os.path.join(self.archive_dir,
                                             'chrome-win32.test'))
    self.assertEquals(len(expected_archived_tests), len(archived_tests))

  def testUploadTestsWithExtras(self):
    # This test is currently only applicable on Windows.
    if not chromium_utils.IsWindows():
      return

    self.createTestFiles(TEST_FILES)
    self.createExtraTestFiles()
    self.initializeStager()
    self.stager.UploadTests(self.archive_dir)

    expected_archived_tests = TEST_FILES + EXTRA_TEST_FILES
    archived_tests = os.listdir(os.path.join(self.archive_dir,
                                             'chrome-win32.test'))
    self.assertEquals(len(expected_archived_tests), len(archived_tests))

  def testUploadTestsNoDeepPaths(self):
    # This test is currently only applicable on Windows.
    if not chromium_utils.IsWindows():
      return

    self.createTestFiles(TEST_FILES_NO_DEEP_DIRS)
    self.initializeStager()
    self.stager.UploadTests(self.archive_dir)

    expected_archived_tests = TEST_FILES_NO_DEEP_DIRS
    archived_tests = os.listdir(os.path.join(self.archive_dir,
                                             'chrome-win32.test'))
    self.assertEquals(len(expected_archived_tests), len(archived_tests))

  def testGenerateRevisionFile(self):
    build_number = None
    chromium_revision = 12345
    webkit_revision = 54321
    v8_revision = 33333
    self.initializeStager(build_number, chromium_revision, webkit_revision,
                          v8_revision)
    self.stager.GenerateRevisionFile()
    self.assertTrue(os.path.exists(self.stager.revisions_path))
    self.assertEquals(None, self.stager.GetLastBuildRevision())
    fp = open(self.stager.revisions_path)
    revisions_dict = simplejson.loads(fp.read())
    self.assertEquals(self.stager.last_chromium_revision,
                      revisions_dict['chromium_revision'])
    self.assertEquals(self.stager.last_webkit_revision,
                      revisions_dict['webkit_revision'])
    self.assertEquals(self.stager.last_v8_revision,
                      revisions_dict['v8_revision'])
    fp.close()

  def testSaveToLastChangeFileAndGetLastBuildRevisionByChromiumRevision(self):
    """This test is to test function SaveBuildRevisionToSpecifiedFile and
    GetLastBuildRevision when acrchiving by chromium revision.
    """
    build_number = None
    chromium_revision = 12345
    webkit_revision = 54321
    v8_revision = 33333
    expect_last_change_file_contents = '%d' % (chromium_revision)
    self.initializeStager(build_number, chromium_revision, webkit_revision,
                          v8_revision)
    last_change_file_path = self.stager.last_change_file
    # At first, there is no last change file.
    self.assertFalse(os.path.exists(last_change_file_path))
    self.assertEquals(None, self.stager.GetLastBuildRevision())
    # Save the revision information to last change file.
    self.stager.SaveBuildRevisionToSpecifiedFile(last_change_file_path)
    # Check the contents in last change file.
    self.assertTrue(os.path.exists(last_change_file_path))
    fp = open(last_change_file_path)
    self.assertEquals(expect_last_change_file_contents, fp.read())
    fp.close()
    self.assertEquals(chromium_revision, self.stager.GetLastBuildRevision())

  def testSaveToLastChangeFileAndGetLastBuildRevisionByBuildNumber(self):
    """This test is to test function SaveBuildRevisionToSpecifiedFile and
    GetLastBuildRevision when acrchiving by build number.
    """
    build_number = 99999
    chromium_revision = 12345
    webkit_revision = 54321
    v8_revision = 33333
    expect_last_change_file_contents = '%d' % (build_number)
    self.initializeStager(build_number, chromium_revision, webkit_revision,
                          v8_revision)
    last_change_file_path = self.stager.last_change_file
    # At first, there is no last change file.
    self.assertFalse(os.path.exists(last_change_file_path))
    self.assertEquals(None, self.stager.GetLastBuildRevision())
    # Save the revision information to last change file.
    self.stager.SaveBuildRevisionToSpecifiedFile(last_change_file_path)
    # Check the contents in last change file.
    self.assertTrue(os.path.exists(last_change_file_path))
    fp = open(last_change_file_path)
    self.assertEquals(expect_last_change_file_contents, fp.read())
    fp.close()
    self.assertEquals(build_number, self.stager.GetLastBuildRevision())


if __name__ == '__main__':
  # Run with a bit more output.
  suite = unittest.TestLoader().loadTestsFromTestCase(ArchiveTest)
  unittest.TextTestRunner(verbosity=2).run(suite)
