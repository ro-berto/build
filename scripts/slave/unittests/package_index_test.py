#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Tests for package_index.py."""

import gzip
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import test_env  # pylint: disable=relative-import

from slave.chromium import package_index

TEST_CC_FILE_CONTENT = '#include "test.h"\nint main() {\nreturn 0;\n}\n'
TEST_H_FILE_CONTENT = ('#ifndef TEST_H\n#define TEST_H\n#include "test2.h"\n'
                       '#endif\n')
TEST2_H_FILE_CONTENT = '#ifndef TEST2_H\n#define TEST2_H\n#endif\n'
COMPILE_ARGUMENTS = 'clang++ -fsyntax-only -std=c++11 -c test.cc -o test.o'

# Test values for corpus, root, and revision
CORPUS = 'chromium-test'
VNAME_ROOT = 'linux'
REVISION = '0123456789'
OUT_DIR = 'src/out/chromium-linux/Debug'

class PackageIndexTest(unittest.TestCase):

  def setUp(self):
    # Emulate the chromium build directory setup: a root dir named "src" which
    # contains the code in subdirectories, along with an
    # "out/chromium-linux/Debug" build directory which all the compilation DB
    # entries are relative to.
    self.root_dir = tempfile.mkdtemp()
    src_dir = os.path.join(self.root_dir, 'src/')
    self.build_dir = os.path.join(src_dir, 'out/chromium-linux/Debug/')
    os.makedirs(self.build_dir)

    def set_content(file_name, content):
      with open(file_name, 'w') as f: f.write(content)

    self.test_cc_file_name = os.path.join(src_dir, 'test.cc')
    set_content(self.test_cc_file_name, TEST_CC_FILE_CONTENT)

    self.test_h_file_name = os.path.join(src_dir, 'test.h')
    set_content(self.test_h_file_name, TEST_H_FILE_CONTENT)

    self.test2_h_file_name = os.path.join(src_dir, 'test2.h')
    set_content(self.test2_h_file_name, TEST2_H_FILE_CONTENT)

    compdb_dictionary = {
        'directory': self.build_dir,
        'command': COMPILE_ARGUMENTS,
        'file': '../../../test.cc',
    }
    # Write a compilation database to a file.
    with tempfile.NamedTemporaryFile(
        suffix='.json', delete=False) as self.compdb_file:
      self.compdb_file.write(json.dumps([compdb_dictionary]))

    # Create the test.cc.filepaths file referenced through the compilation
    # database
    with open(self.test_cc_file_name + '.filepaths', 'wb') as filepaths_file:
      filepaths_file.write('\n'.join([
          os.path.join('../../../', self.test_cc_file_name),
          os.path.join('../../../', self.test_h_file_name),
          os.path.join('../../../', self.test2_h_file_name),
      ]))

    self.index_pack = package_index.IndexPack(
        os.path.realpath(self.compdb_file.name), corpus=CORPUS, root=VNAME_ROOT,
        revision=REVISION, out_dir=OUT_DIR)
    self.assertTrue(os.path.exists(self.index_pack.index_directory))
    self.assertTrue(os.path.exists(
        os.path.join(self.index_pack.index_directory, 'files')))
    self.assertTrue(os.path.exists(
        os.path.join(self.index_pack.index_directory, 'units')))

  def tearDown(self):
    if os.path.exists(self.index_pack.index_directory):
      shutil.rmtree(self.index_pack.index_directory)
    shutil.rmtree(self.root_dir)

  def _CheckDataFile(self, filename, content):
    filepath = os.path.join(self.index_pack.index_directory, 'files', filename)
    self.assertTrue(os.path.exists(filepath))
    with gzip.open(filepath, 'rb') as data_file:
      actual_content = data_file.read()
    self.assertEquals(content, actual_content)

  def testGenerateDataFiles(self):
    self.index_pack._GenerateDataFiles()
    test_cc_file = hashlib.sha256(TEST_CC_FILE_CONTENT).hexdigest() + '.data'
    test_h_file = hashlib.sha256(TEST_H_FILE_CONTENT).hexdigest() + '.data'
    self._CheckDataFile(test_cc_file, TEST_CC_FILE_CONTENT)
    self._CheckDataFile(test_h_file, TEST_H_FILE_CONTENT)

  def testGenerateUnitFiles(self):
    # Setup some dictionaries which are usually filled by _GenerateDataFiles()
    self.index_pack.filehashes = {
        self.test_cc_file_name:
            hashlib.sha256(TEST_CC_FILE_CONTENT).hexdigest(),
        self.test_h_file_name:
            hashlib.sha256(TEST_H_FILE_CONTENT).hexdigest(),
        self.test2_h_file_name:
            hashlib.sha256(TEST2_H_FILE_CONTENT).hexdigest(),
    }
    self.index_pack.filesizes = {
        self.test_cc_file_name: len(TEST_CC_FILE_CONTENT),
        self.test_h_file_name: len(TEST_H_FILE_CONTENT),
        self.test2_h_file_name: len(TEST2_H_FILE_CONTENT),
    }

    # Now _GenerateUnitFiles() can be called.
    self.index_pack._GenerateUnitFiles()

    # Because we only called _GenerateUnitFiles(), the index pack directory
    # should only contain the one unit file for the one compilation unit in our
    # test compilation database.
    for root, _, files in os.walk(self.index_pack.index_directory):
      for unit_file_name in files:
        with gzip.open(os.path.join(root, unit_file_name), 'rb') as unit_file:
          unit_file_content = unit_file.read()

        # Assert that the name of the unit file is correct.
        unit_file_hash = hashlib.sha256(unit_file_content).hexdigest()
        self.assertEquals(unit_file_name, unit_file_hash + '.unit')

        # Assert that the json content encodes valid dictionaries.
        compilation_unit_wrapper = json.loads(unit_file_content)
        self.assertEquals(compilation_unit_wrapper['format'], 'kythe')
        compilation_unit_dictionary = compilation_unit_wrapper['content']

        self.assertEquals(compilation_unit_dictionary['v_name']['corpus'],
                          CORPUS)
        self.assertEquals(compilation_unit_dictionary['v_name']['root'],
                          VNAME_ROOT)
        self.assertEquals(compilation_unit_dictionary['source_file'],
                          ['../../../test.cc'])
        self.assertEquals(compilation_unit_dictionary['revision'],
                          REVISION)
        self.assertEquals(compilation_unit_dictionary['output_key'], 'test.o')

        self.assertEquals(len(compilation_unit_dictionary['required_input']),
                          len(self.index_pack.filesizes))

        test_cc_entry = compilation_unit_dictionary['required_input'][0]
        self.assertEquals(test_cc_entry['info']['digest'],
                          hashlib.sha256(TEST_CC_FILE_CONTENT).hexdigest())
        self.assertEquals(test_cc_entry['info']['path'], '../../../test.cc')
        self.assertEquals(test_cc_entry['v_name']['path'], 'src/test.cc')
        self.assertEquals(test_cc_entry['v_name']['corpus'], CORPUS)
        self.assertEquals(test_cc_entry['v_name']['root'], VNAME_ROOT)

        test_h_entry = compilation_unit_dictionary['required_input'][1]
        self.assertEquals(test_h_entry['info']['digest'],
                          hashlib.sha256(TEST_H_FILE_CONTENT).hexdigest())
        self.assertEquals(test_h_entry['info']['path'], '../../../test.h')
        self.assertEquals(test_h_entry['v_name']['path'], 'src/test.h')
        self.assertEquals(test_h_entry['v_name']['corpus'], CORPUS)
        self.assertEquals(test_h_entry['v_name']['root'], VNAME_ROOT)

        test2_h_entry = compilation_unit_dictionary['required_input'][2]
        self.assertEquals(test2_h_entry['info']['digest'],
                          hashlib.sha256(TEST2_H_FILE_CONTENT).hexdigest())
        self.assertEquals(test2_h_entry['info']['path'], '../../../test2.h')
        self.assertEquals(test2_h_entry['v_name']['path'], 'src/test2.h')
        self.assertEquals(test2_h_entry['v_name']['corpus'], CORPUS)
        self.assertEquals(test2_h_entry['v_name']['root'], VNAME_ROOT)

        real_compile_arguments = COMPILE_ARGUMENTS.split()[1:]
        self.assertEquals(
            compilation_unit_dictionary['argument'],
            (
                real_compile_arguments + ['-w', '-nostdinc++']
            ))

if __name__ == '__main__':
  unittest.main()
