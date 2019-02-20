#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Tests for package_index.py."""

import hashlib
import json
import os
import shutil
import tempfile
import unittest
import zipfile

import package_index

TEST_CC_FILE_CONTENT = '#include "test.h"\nint main() {\nreturn 0;\n}\n'
TEST_H_FILE_CONTENT = ('#ifndef TEST_H\n#define TEST_H\n#include "test2.h"\n'
                       '#endif\n')
TEST2_H_FILE_CONTENT = '#ifndef TEST2_H\n#define TEST2_H\n#endif\n'
CC_COMPILE_ARGUMENTS = (r'clang++ -fsyntax-only -DFOO=\"foo\ bar\" -std=c++11 '
                        '-Wno-c++11-narrowing  -Wall -c test.cc -o test.o')
CC_COMPILE_ARGUMENTS_WIN = ('clang-cl.exe --driver-mode=cl /c test.cc '
                            '/Fotest.obj')

TEST_MOJOM_FILE_CONTENT = 'module test.mojom; interface TheInterface {};'
# These are a list rather than a string as that's the format that gn desc spits
# them out in.
MOJOM_COMPILE_ARGUMENTS = [
    '--use_bundled_pylibs', 'generate', '-d', '../../', '-I', '../../', '-o',
    'gen', '--bytecode_path', 'gen/bindings',
    '--filelist={{response_file_name}}', '-g', 'c++', '--typemap',
    'gen/mojo_bindings__type_mappings'
]
TEST_MOJOM_GEN_H_FILE_CONTENT = ('#ifndef TEST_MOJOM_H\n#define '
                                 'TEST_MOJOM_H\n#endif\n')

# Test values for corpus, root, and out dir
CORPUS = 'chromium-test'
VNAME_ROOT = 'linux'
OUT_DIR = 'src/out/chromium-linux/Debug'

class PackageIndexTest(unittest.TestCase):

  def setUp(self):
    # Emulate the chromium build directory setup: a root dir named "src" which
    # contains the code in subdirectories, along with an
    # "out/chromium-linux/Debug" build directory which all the compilation DB
    # entries are relative to.
    self.root_dir = tempfile.mkdtemp()
    os.chdir(self.root_dir)
    src_dir = os.path.join(self.root_dir, 'src/')
    self.build_dir = os.path.join(src_dir, 'out/chromium-linux/Debug/')
    os.makedirs(self.build_dir)
    os.mkdir(os.path.join(self.build_dir, 'gen'))

    def set_content(file_name, content):
      with open(file_name, 'w') as f:
        f.write(content)

    self.test_cc_file_name = os.path.join(src_dir, 'test.cc')
    set_content(self.test_cc_file_name, TEST_CC_FILE_CONTENT)

    self.test_h_file_name = os.path.join(src_dir, 'test.h')
    set_content(self.test_h_file_name, TEST_H_FILE_CONTENT)

    self.test2_h_file_name = os.path.join(src_dir, 'test2.h')
    set_content(self.test2_h_file_name, TEST2_H_FILE_CONTENT)

    self.test_mojom_file_name = os.path.join(src_dir, 'test.mojom')
    set_content(self.test_mojom_file_name, TEST_MOJOM_FILE_CONTENT)

    self.test_mojom_gen_h_file_name = os.path.join(self.build_dir,
                                                   'gen/test.mojom.h')
    set_content(self.test_mojom_gen_h_file_name, TEST_MOJOM_GEN_H_FILE_CONTENT)

    compdb_dictionary = {
        'directory': self.build_dir,
        'command': CC_COMPILE_ARGUMENTS,
        'file': '../../../test.cc',
    }
    # Write a compilation database to a file.
    with tempfile.NamedTemporaryFile(
        suffix='.json', delete=False) as self.compdb_file:
      json.dump([compdb_dictionary], self.compdb_file)

    # Create the test.cc.filepaths file referenced through the compilation
    # database
    with open(self.test_cc_file_name + '.filepaths', 'wb') as filepaths_file:
      filepaths_file.write('\n'.join([
          os.path.join('../../../', self.test_cc_file_name),
          os.path.join('../../../', self.test_h_file_name),
          os.path.join('../../../', self.test2_h_file_name),
          'missing_file_name',
      ]))

    gn_dictionary = {
        "//:test_mojo_bindings__generator": {
            "args": MOJOM_COMPILE_ARGUMENTS,
            "script": "//mojo/mojom_bindings_generator.py",
            "sources": ["//test.mojom"],
            "outputs": ["//out/chromium-linux/Debug/gen/test.mojom.h"],
        }
    }
    with tempfile.NamedTemporaryFile(
        suffix='.json', delete=False) as self.gn_targets_file:
      json.dump(gn_dictionary, self.gn_targets_file)

    # Create a path for the archive to be written to.
    with tempfile.NamedTemporaryFile(
        suffix='.kzip', delete=False) as archive_file:
      self.archive_path = archive_file.name

    self.index_pack = package_index.IndexPack(
        os.path.realpath(self.compdb_file.name),
        os.path.realpath(self.gn_targets_file.name),
        corpus=CORPUS,
        root=VNAME_ROOT,
        out_dir=OUT_DIR,
        verbose=True)
    self.assertTrue(os.path.exists(self.index_pack.index_directory))
    self.assertTrue(os.path.exists(
        os.path.join(self.index_pack.index_directory, 'files')))
    self.assertTrue(os.path.exists(
        os.path.join(self.index_pack.index_directory, 'units')))

  def tearDown(self):
    if os.path.exists(self.compdb_file.name):
      os.remove(self.compdb_file.name)
    if os.path.exists(self.archive_path):
      os.remove(self.archive_path)
    self.index_pack.close()
    shutil.rmtree(self.root_dir)

  def _CheckDataFile(self, filename, content):
    filepath = os.path.join(self.index_pack.index_directory, 'files', filename)
    self.assertTrue(os.path.exists(filepath))
    with open(filepath, 'r') as data_file:
      actual_content = data_file.read()
    self.assertEquals(content, actual_content)

  def testGenerateDataFiles(self):
    self.index_pack._GenerateDataFiles()
    test_cc_file = hashlib.sha256(TEST_CC_FILE_CONTENT).hexdigest()
    test_h_file = hashlib.sha256(TEST_H_FILE_CONTENT).hexdigest()
    test_mojom_file = hashlib.sha256(TEST_MOJOM_FILE_CONTENT).hexdigest()
    test_mojom_gen_h_file = hashlib.sha256(
        TEST_MOJOM_GEN_H_FILE_CONTENT).hexdigest()
    self._CheckDataFile(test_cc_file, TEST_CC_FILE_CONTENT)
    self._CheckDataFile(test_h_file, TEST_H_FILE_CONTENT)
    self._CheckDataFile(test_mojom_file, TEST_MOJOM_FILE_CONTENT)
    self._CheckDataFile(test_mojom_gen_h_file, TEST_MOJOM_GEN_H_FILE_CONTENT)

  def testGenerateUnitFiles(self):
    # Set up the filehashes dict which is usually filled by _GenerateDataFiles()
    self.index_pack.filehashes = {
        self.test_cc_file_name:
            hashlib.sha256(TEST_CC_FILE_CONTENT).hexdigest(),
        self.test_h_file_name:
            hashlib.sha256(TEST_H_FILE_CONTENT).hexdigest(),
        self.test2_h_file_name:
            hashlib.sha256(TEST2_H_FILE_CONTENT).hexdigest(),
        self.test_mojom_file_name:
            hashlib.sha256(TEST_MOJOM_FILE_CONTENT).hexdigest(),
        self.test_mojom_gen_h_file_name:
            hashlib.sha256(TEST_MOJOM_GEN_H_FILE_CONTENT).hexdigest(),
    }

    # Now _GenerateUnitFiles() can be called.
    self.index_pack._GenerateUnitFiles()

    # Because we only called _GenerateUnitFiles(), the index pack directory
    # should only contain the two unit files for the two compilation units in
    # our test compilation database and gn target list.
    units_dir = os.path.join(self.index_pack.index_directory, 'units')
    unit_files = os.listdir(units_dir)
    self.assertEqual(2, len(unit_files))
    for unit_file_name in unit_files:
      with open(os.path.join(units_dir, unit_file_name), 'r') as unit_file:
        unit_file_content = unit_file.read()

      # Assert that the name of the unit file is correct.
      unit_file_hash = hashlib.sha256(unit_file_content).hexdigest()
      self.assertEquals(unit_file_name, unit_file_hash)

      # Assert that the json content encodes valid dictionaries.
      compilation_unit_wrapper = json.loads(unit_file_content)
      compilation_unit_dictionary = compilation_unit_wrapper['unit']

      language = compilation_unit_dictionary['v_name']['language']

      if language == 'c++':
        self.assertEquals(compilation_unit_dictionary['v_name']['corpus'],
                          CORPUS)
        self.assertEquals(compilation_unit_dictionary['v_name']['root'],
                          VNAME_ROOT)

        self.assertEquals(compilation_unit_dictionary['source_file'],
                          ['../../../test.cc'])
        self.assertEquals(compilation_unit_dictionary['output_key'], 'test.o')

        self.assertEquals(len(compilation_unit_dictionary['required_input']), 3)

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

        expected_compile_arguments = [
            u'clang++', u'-fsyntax-only', u'-DFOO="foo bar"', u'-std=c++11',
            u'-c', u'test.cc', u'-o', u'test.o', u'-w',
        ]
        self.assertEquals(compilation_unit_dictionary['argument'],
                          expected_compile_arguments)
      elif language == 'mojom':
        self.assertEquals(compilation_unit_dictionary['v_name']['corpus'],
                          CORPUS)
        self.assertEquals(compilation_unit_dictionary['v_name']['root'],
                          VNAME_ROOT)

        self.assertEquals(compilation_unit_dictionary['source_file'],
                          ['../../../test.mojom'])
        self.assertEquals(compilation_unit_dictionary['output_key'],
                          'gen/test.mojom.h')

        # Expect 2 entries: the file itself and its generated header.
        self.assertEquals(len(compilation_unit_dictionary['required_input']), 2)

        test_mojom_entry = compilation_unit_dictionary['required_input'][0]
        self.assertEquals(test_mojom_entry['info']['digest'],
                          hashlib.sha256(TEST_MOJOM_FILE_CONTENT).hexdigest())
        self.assertEquals(test_mojom_entry['info']['path'],
                          '../../../test.mojom')
        self.assertEquals(test_mojom_entry['v_name']['path'], 'src/test.mojom')
        self.assertEquals(test_mojom_entry['v_name']['corpus'], CORPUS)
        self.assertEquals(test_mojom_entry['v_name']['root'], VNAME_ROOT)

        test_mojom_gen_h_entry = compilation_unit_dictionary['required_input'][
            1]
        self.assertEquals(
            test_mojom_gen_h_entry['info']['digest'],
            hashlib.sha256(TEST_MOJOM_GEN_H_FILE_CONTENT).hexdigest())
        self.assertEquals(test_mojom_gen_h_entry['info']['path'],
                          'gen/test.mojom.h')
        self.assertEquals(test_mojom_gen_h_entry['v_name']['path'],
                          'src/out/chromium-linux/Debug/gen/test.mojom.h')
        self.assertEquals(test_mojom_gen_h_entry['v_name']['corpus'], CORPUS)
        self.assertEquals(test_mojom_gen_h_entry['v_name']['root'], VNAME_ROOT)

        expected_compile_arguments = [
            '--use_bundled_pylibs', 'generate', '-d', '../../', '-I', '../../',
            '-o', 'gen', '--bytecode_path', 'gen/bindings', '-g', 'c++',
            '--typemap', 'gen/mojo_bindings__type_mappings',
            '../../../test.mojom'
        ]
        self.assertEquals(compilation_unit_dictionary['argument'],
                          expected_compile_arguments)
      else:
        self.fail(
            'Expected only c++ and mojom compilation units, got %s' % language)

  def testGenerateUnitFilesWindows(self):
    # Write a new compdb with Windows args.
    compdb_dictionary = {
        'directory': self.build_dir,
        'command': CC_COMPILE_ARGUMENTS_WIN,
        'file': '../../../test.cc',
    }
    with open(self.compdb_file.name, 'w') as compdb_file:
      compdb_file.write(json.dumps([compdb_dictionary]))

    # Write a new test.cc.filepaths file for Windows (using backslash as a path
    # separator).
    with open(self.test_cc_file_name + '.filepaths', 'wb') as filepaths_file:
      filepaths_file.write('\n'.join([
          os.path.join('..\\..\\..\\', self.test_cc_file_name),
          os.path.join('..\\..\\..\\', self.test_h_file_name),
          os.path.join('..\\..\\..\\', self.test2_h_file_name),
          'missing_file_name',
      ]))

    # Recreate the index pack.
    self.index_pack.close()
    self.index_pack = package_index.IndexPack(
        os.path.realpath(self.compdb_file.name),
        os.path.realpath(self.gn_targets_file.name),
        corpus=CORPUS,
        root=VNAME_ROOT,
        out_dir=OUT_DIR,
        verbose=True)

    # Set up the filehashes dict which is usually filled by _GenerateDataFiles()
    self.index_pack.filehashes = {
        self.test_cc_file_name:
            hashlib.sha256(TEST_CC_FILE_CONTENT).hexdigest(),
        self.test_h_file_name:
            hashlib.sha256(TEST_H_FILE_CONTENT).hexdigest(),
        self.test2_h_file_name:
            hashlib.sha256(TEST2_H_FILE_CONTENT).hexdigest(),
        self.test_mojom_file_name:
            hashlib.sha256(TEST_MOJOM_FILE_CONTENT).hexdigest(),
        self.test_mojom_gen_h_file_name:
            hashlib.sha256(TEST_MOJOM_GEN_H_FILE_CONTENT).hexdigest(),
    }

    # Now _GenerateUnitFiles() can be called.
    self.index_pack._GenerateUnitFiles()

    # Because we only called _GenerateUnitFiles(), the index pack directory
    # should only contain the two unit files for the two compilation units in
    # our test compilation database and gn target list.
    units_dir = os.path.join(self.index_pack.index_directory, 'units')
    unit_files = os.listdir(units_dir)
    self.assertEqual(2, len(unit_files))
    for unit_file_name in unit_files:
      with open(os.path.join(units_dir, unit_file_name), 'r') as unit_file:
        unit_file_content = unit_file.read()

      # Assert that the output path was parsed correctly.
      compilation_unit_wrapper = json.loads(unit_file_content)
      compilation_unit_dictionary = compilation_unit_wrapper['unit']

      if compilation_unit_dictionary['v_name']['language'] == 'c++':
        self.assertEquals(compilation_unit_dictionary['output_key'], 'test.obj')

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

        expected_compile_arguments = [
            u'clang-cl.exe', u'--driver-mode=cl', u'/c', u'test.cc',
            u'/Fotest.obj', u'-w',
        ]
        self.assertEquals(compilation_unit_dictionary['argument'],
                          expected_compile_arguments)
      else:
        self.assertEquals(compilation_unit_dictionary['v_name']['language'],
                          'mojom')

  def testCreateArchive(self):
    self.index_pack._GenerateDataFiles()
    self.index_pack._GenerateUnitFiles()
    self.index_pack.CreateArchive(self.archive_path)

    # Verify the structure of the archive. It should be as follows:
    # root/              # Any valid non-empty directory name
    #   units/
    #     abcd1234       # Compilation unit (name is SHA256 of content)
    #     ...
    #   files/
    #     1a2b4c4d       # File contents
    #     ...
    self.assertTrue(os.path.exists(self.archive_path))
    with zipfile.ZipFile(self.archive_path, 'r') as archive:
      zipped_filenames = archive.namelist()

    root = os.path.basename(self.index_pack.index_directory)
    self.assertIn(root + os.path.sep, zipped_filenames);

    self.assertIn(os.path.join(root, 'units', ''), zipped_filenames)

    # Rather than hardcode the SHA256 of the unit files here, we simply verify
    # that at least one exists and that they are all present in the zip.
    units_dir = os.path.join(self.index_pack.index_directory, 'units')
    unit_files = os.listdir(units_dir)
    self.assertNotEqual(0, len(unit_files))
    for unit_file_name in unit_files:
      self.assertIn(os.path.join(root, 'units', unit_file_name),
                    zipped_filenames)

    self.assertIn(os.path.join(root, 'files', ''), zipped_filenames)

    test_cc_file = hashlib.sha256(TEST_CC_FILE_CONTENT).hexdigest()
    self.assertIn(os.path.join(root, 'files', test_cc_file), zipped_filenames)

    test_h_file = hashlib.sha256(TEST_H_FILE_CONTENT).hexdigest()
    self.assertIn(os.path.join(root, 'files', test_h_file), zipped_filenames)

    test_h_file2 = hashlib.sha256(TEST2_H_FILE_CONTENT).hexdigest()
    self.assertIn(os.path.join(root, 'files', test_h_file2), zipped_filenames)

if __name__ == '__main__':
  unittest.main()
