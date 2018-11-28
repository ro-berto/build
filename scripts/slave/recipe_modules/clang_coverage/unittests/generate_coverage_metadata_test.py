#!/usr/bin/env vpython
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import generate_coverage_metadata as generator


class GenerateCoverageMetadataTest(unittest.TestCase):

  def test_extract_coverage_info_odd_segments(self):
    segments = [
        [1, 2, 3, True, True],
        [3, 10, 0, False, False],
        [4, 5, 0, False, False],
        [5, 2, 2, True, True],
        [6, 10, 0, False, False],
    ]
    expected_line_data = dict([
        (1, 3), (2, 3), (3, 3), (5, 2), (6, 2)
    ])
    expected_block_data = {}
    line_data, block_data = generator._extract_coverage_info(segments)
    self.assertDictEqual(expected_line_data, line_data)
    self.assertDictEqual(expected_block_data, block_data)

  def test_extract_coverage_info_even_segments(self):
    segments = [
        [1, 2, 3, True, True],
        [3, 10, 0, False, False],
        [5, 2, 0, True, True],
        [5, 10, 0, False, False],
    ]
    expected_line_data = dict([
        (1, 3), (2, 3), (3, 3), (5, 0)
    ])
    uncovered_blocks_line_5 = [[2, 10]]
    line_data, block_data = generator._extract_coverage_info(segments)
    self.assertDictEqual(expected_line_data, line_data)
    self.assertEqual(1, len(block_data))
    self.assertListEqual(uncovered_blocks_line_5, block_data.get(5))

  def test_extract_coverage_info_overlapped_regions(self):
    segments = [
        [1, 2, 3, True, True],
        [3, 2, 1, True, True],
        [3, 10, 0, False, False],
        [5, 10, 0, False, False],
    ]
    expected_line_data = dict([
        (1, 3), (2, 3), (3, 1), (4, 3), (5, 3)
    ])
    expected_block_data = {}
    line_data, block_data = generator._extract_coverage_info(segments)
    self.assertDictEqual(expected_line_data, line_data)
    self.assertDictEqual(expected_block_data, block_data)

  def test_to_file_record_flat_format(self):
    src_path = '/path/to/chromium/src'
    file_coverage_data = {
        'segments': [
            [1, 2, 3, True, True],
            [3, 2, 1, True, True],
            [3, 10, 0, False, False],
            [5, 10, 0, False, False],
            [6, 2, 0, True, True],
            [7, 2, 0, False, False],
        ],
        'summary': {
            'lines': {
                'count': 8,
            }
        },
        'filename': '/path/to/chromium/src/base/base.cc',
    }
    expected_record = {
        'path': 'base/base.cc',
        'total_lines': 8,
        'lines': [
            {
                'line': 1,
                'count': 3,
            },
            {
                'line': 2,
                'count': 3,
            },
            {
                'line': 3,
                'count': 1,
            },
            {
                'line': 4,
                'count': 3,
            },
            {
                'line': 5,
                'count': 3,
            },
            {
                'line': 6,
                'count': 0,
            },
            {
                'line': 7,
                'count': 0,
            },
        ]
    }
    record = generator._to_file_record(
        src_path, file_coverage_data, compressed_format=False)
    self.assertDictEqual(expected_record, record)

  def test_to_file_record_compressed_format(self):
    src_path = '/path/to/chromium/src'
    file_coverage_data = {
        'segments': [
            [1, 2, 3, True, True],
            [3, 2, 1, True, True],
            [3, 10, 0, False, False],
            [3, 12, 0, True, True],
            [3, 18, 0, False, False],
            [5, 10, 0, False, False],
            [6, 2, 0, True, True],
            [7, 2, 0, False, False],
        ],
        'summary': {
            'lines': {
                'count': 8,
            }
        },
        'filename': '/path/to/chromium/src/base/base.cc',
    }
    expected_record = {
        'path': 'base/base.cc',
        'total_lines': 8,
        'lines': [
            {
                'first': 1,
                'last': 2,
                'count': 3,
            },
            {
                'first': 3,
                'last': 3,
                'count': 1,
            },
            {
                'first': 4,
                'last': 5,
                'count': 3,
            },
            {
                'first': 6,
                'last': 7,
                'count': 0,
            },
        ],
        'uncovered_blocks': [
            {
                'line': 3,
                'ranges': [
                    {
                        'first': 12,
                        'last': 18,
                    }
                ]
            }
        ],
    }
    self.maxDiff = None
    record = generator._to_file_record(
        src_path, file_coverage_data, compressed_format=True)
    self.assertDictEqual(expected_record, record)

  def test_compute_llvm_args_with_sharded_output(self):
    args, shard_dir = generator._compute_llvm_args(
        '/path/to/coverage.profdata',
        '/path/to/llvm-cov',
        ['/path/to/1.exe', '/path/to/2.exe'],
        ['/src/a.cc', '/src/b.cc'],
        '/path/output/dir', 5, no_sharded_output=False)
    expected_args = [
        '/path/to/llvm-cov', 'export', '-output-dir', '/path/output/dir/shards',
        '-num-threads', '5', '-instr-profile',
        '/path/to/coverage.profdata', '/path/to/1.exe',
        '-object', '/path/to/2.exe',
        '/src/a.cc', '/src/b.cc',
    ]
    self.assertListEqual(expected_args, args)
    self.assertEqual('/path/output/dir/shards', shard_dir)

  def test_compute_llvm_args_without_sharded_output(self):
    args, shard_dir = generator._compute_llvm_args(
        '/path/to/coverage.profdata',
        '/path/to/llvm-cov',
        ['/path/to/1.exe', '/path/to/2.exe'],
        ['/src/a.cc', '/src/b.cc'],
        '/path/output/dir', 5, no_sharded_output=True)
    expected_args = [
        '/path/to/llvm-cov', 'export', '-instr-profile',
        '/path/to/coverage.profdata', '/path/to/1.exe',
        '-object', '/path/to/2.exe',
        '/src/a.cc', '/src/b.cc',
    ]
    self.assertListEqual(expected_args, args)
    self.assertIsNone(shard_dir)

  def test_rebase_flat_data(self):
    flat_data = {
        'files': [{
            'path':
                'base/base.cc',
            'total_lines':
                8,
            'lines': [{
                'line': 1,
                'count': 3,
            }, {
                'line': 2,
                'count': 3,
            }, {
                'line': 3,
                'count': 1,
            }, {
                'line': 4,
                'count': 3,
            }]
        }]
    }

    diff_mapping = {'base/base.cc': {'3': [16, 'A line added by the patch.']}}
    rebased_flat_data = generator._rebase_flat_data(flat_data, diff_mapping)
    expected_flat_data = {
        'files': [{
            'path': 'base/base.cc',
            'total_lines': 1,
            'lines': [{
                'line': 16,
                'count': 1,
            }]
        }]
    }
    self.assertEqual(expected_flat_data, rebased_flat_data)


if __name__ == '__main__':
  unittest.main()
