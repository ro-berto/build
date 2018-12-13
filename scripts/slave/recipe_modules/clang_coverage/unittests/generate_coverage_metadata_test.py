#!/usr/bin/env vpython
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

import mock

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
    expected_line_data = dict([(1, 3), (2, 3), (3, 3), (5, 2), (6, 2)])
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
    expected_line_data = dict([(1, 3), (2, 3), (3, 3), (5, 0)])
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
    expected_line_data = dict([(1, 3), (2, 3), (3, 1), (4, 3), (5, 3)])
    expected_block_data = {}
    line_data, block_data = generator._extract_coverage_info(segments)
    self.assertDictEqual(expected_line_data, line_data)
    self.assertDictEqual(expected_block_data, block_data)

  def test_to_compressed_file_record(self):
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
        'filename':
            '/path/to/chromium/src/base/base.cc',
    }
    expected_record = {
        'path':
            'base/base.cc',
        'total_lines':
            8,
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
        'uncovered_blocks': [{
            'line': 3,
            'ranges': [{
                'first': 12,
                'last': 18,
            }]
        }],
    }
    self.maxDiff = None
    record = generator._to_compressed_file_record(src_path, file_coverage_data)
    self.assertDictEqual(expected_record, record)

  # This test tests that for *uncontinous* regions, even if their lines are
  # executed the same number of times, when converted to compressed format,
  # lines in different regions shouldn't be merged together.
  def test_to_compressed_file_record_for_uncontinous_lines(self):
    src_path = '/path/to/chromium/src'
    file_coverage_data = {
        'segments': [
            [102, 35, 4, True, True],
            [104, 4, 0, False, False],
            [107, 35, 4, True, True],
            [109, 4, 0, False, False],
        ],
        'summary': {
            'lines': {
                'count': 6,
            }
        },
        'filename':
            '/path/to/chromium/src/base/base.cc',
    }
    expected_record = {
        'path':
            'base/base.cc',
        'total_lines':
            6,
        'lines': [
            {
                'first': 102,
                'last': 104,
                'count': 4,
            },
            {
                'first': 107,
                'last': 109,
                'count': 4,
            },
        ]
    }
    self.maxDiff = None
    record = generator._to_compressed_file_record(src_path, file_coverage_data)
    self.assertDictEqual(expected_record, record)

  def test_rebase_line_and_block_data(self):
    line_data = [(1, 3), (2, 3), (3, 3), (5, 0)]
    block_data = {5: [[2, 10]]}
    file_name = 'base/base.cc'
    diff_mapping = {'base/base.cc': {'5': [16, 'A line added by the patch.']}}

    rebased_line_data, rebased_block_data = (
        generator._rebase_line_and_block_data(line_data, block_data,
                                              diff_mapping[file_name]))

    expected_line_data = [(16, 0)]
    expected_block_data = {16: [[2, 10]]}
    self.maxDiff = None
    self.assertListEqual(expected_line_data, rebased_line_data)
    self.assertDictEqual(expected_block_data, rebased_block_data)

  def test_to_compressed_file_record_with_diff_mapping(self):
    src_path = '/path/to/chromium/src'
    file_coverage_data = {
        'segments': [
            [1, 2, 3, True, True],
            [3, 10, 0, False, False],
            [5, 2, 0, True, True],
            [5, 10, 0, False, False],
        ],
        'summary': {
            'lines': {
                'count': 5,
            }
        },
        'filename':
            '/path/to/chromium/src/base/base.cc',
    }
    diff_mapping = {
        'base/base.cc': {
            '2': [10, 'A line added by the patch.'],
            '3': [11, 'Another added line.'],
            '5': [16, 'One more line.']
        }
    }

    record = generator._to_compressed_file_record(src_path, file_coverage_data,
                                                  diff_mapping)

    expected_record = {
        'path':
            'base/base.cc',
        'total_lines':
            5,
        'lines': [
            {
                'first': 10,
                'last': 11,
                'count': 3,
            },
            {
                'first': 16,
                'last': 16,
                'count': 0,
            },
        ],
        'uncovered_blocks': [{
            'line': 16,
            'ranges': [{
                'first': 2,
                'last': 10,
            }]
        }],
    }

    self.maxDiff = None
    self.assertDictEqual(expected_record, record)

  def test_compute_llvm_args_with_sharded_output(self):
    args, shard_dir = generator._compute_llvm_args(
        '/path/to/coverage.profdata',
        '/path/to/llvm-cov', ['/path/to/1.exe', '/path/to/2.exe'],
        ['/src/a.cc', '/src/b.cc'],
        '/path/output/dir',
        5,
        no_sharded_output=False)
    expected_args = [
        '/path/to/llvm-cov',
        'export',
        '-output-dir',
        '/path/output/dir/shards',
        '-num-threads',
        '5',
        '-instr-profile',
        '/path/to/coverage.profdata',
        '/path/to/1.exe',
        '-object',
        '/path/to/2.exe',
        '/src/a.cc',
        '/src/b.cc',
    ]
    self.assertListEqual(expected_args, args)
    self.assertEqual('/path/output/dir/shards', shard_dir)

  def test_compute_llvm_args_without_sharded_output(self):
    args, shard_dir = generator._compute_llvm_args(
        '/path/to/coverage.profdata',
        '/path/to/llvm-cov', ['/path/to/1.exe', '/path/to/2.exe'],
        ['/src/a.cc', '/src/b.cc'],
        '/path/output/dir',
        5,
        no_sharded_output=True)
    expected_args = [
        '/path/to/llvm-cov',
        'export',
        '-instr-profile',
        '/path/to/coverage.profdata',
        '/path/to/1.exe',
        '-object',
        '/path/to/2.exe',
        '/src/a.cc',
        '/src/b.cc',
    ]
    self.assertListEqual(expected_args, args)
    self.assertIsNone(shard_dir)

  @mock.patch.object(generator, '_get_coverage_data_in_json')
  def test_generate_metadata_for_per_cl_coverage(self, mock_get_coverage_data):
    mock_get_coverage_data.return_value = {
        'data': [{
            'files': [{
                'segments': [
                    [1, 2, 3, True, True],
                    [3, 10, 0, False, False],
                    [5, 2, 0, True, True],
                    [5, 10, 0, False, False],
                ],
                'summary': {
                    'lines': {
                        'count': 5,
                        'covered': 3,
                        'percent': 60,
                    },
                    'functions': {
                        'count': 2,
                        'covered': 2,
                        'percent': 100,
                    },
                    'regions': {
                        'count': 4,
                        'covered': 3,
                        'percent': 75,
                    },
                },
                'filename':
                    '/path/to/src/dir/file.cc',
            }]
        }]
    }

    diff_mapping = {
        'dir/file.cc': {
            '2': [10, 'A line added by the patch.'],
            '3': [11, 'Another added line.'],
            '5': [16, 'One more line.']
        }
    }

    compressed_data = generator._generate_metadata(
        src_path='/path/to/src',
        output_dir='/path/to/output_dir',
        profdata_path='/path/to/coverage.profdata',
        llvm_cov_path='/path/to/llvm-cov',
        binaries=['/path/to/binary1', '/path/to/binary2'],
        component_mapping=None,
        sources=['/path/to/src/dir/file.cc'],
        diff_mapping=diff_mapping)

    expected_compressed_files = [{
        'path':
            '//dir/file.cc',
        'lines': [{
            'count': 3,
            'last': 11,
            'first': 10
        }, {
            'count': 0,
            'last': 16,
            'first': 16
        }],
        'total_lines':
            5,
        'uncovered_blocks': [{
            'ranges': [{
                'last': 10,
                'first': 2
            }],
            'line': 16
        }]
    }]
    self.maxDiff = None
    self.assertListEqual(expected_compressed_files, compressed_data['files'])

  @mock.patch.object(generator, '_get_coverage_data_in_json')
  def test_generate_metadata_for_full_repo_coverage(self,
                                                    mock_get_coverage_data):
    # Number of files should not exceed 1000; otherwise sharding will happen.
    mock_get_coverage_data.return_value = {
        'data': [{
            'files': [
                {
                    'segments': [
                        [5, 2, 0, True, True],
                        [5, 10, 0, False, False],
                    ],
                    'summary': {
                        'lines': {
                            'count': 1,
                            'covered': 0,
                            'percent': 0,
                        },
                        'functions': {
                            'count': 1,
                            'covered': 0,
                            'percent': 0,
                        },
                        'regions': {
                            'count': 1,
                            'covered': 0,
                            'percent': 0,
                        },
                    },
                    'filename':
                        '/path/to/src/dir1/file1.cc',
                },
                {
                    'segments': [
                        [1, 1, 1, True, True],
                        [1, 6, 0, False, False],
                    ],
                    'summary': {
                        'lines': {
                            'count': 1,
                            'covered': 1,
                            'percent': 100,
                        },
                        'functions': {
                            'count': 1,
                            'covered': 1,
                            'percent': 100,
                        },
                        'regions': {
                            'count': 1,
                            'covered': 1,
                            'percent': 100,
                        },
                    },
                    'filename':
                        '/path/to/src/dir2/file2.cc',
                },
            ]
        }]
    }

    component_mapping = {'dir1': 'Test>Component', 'dir2': 'Test>Component'}

    compressed_data = generator._generate_metadata(
        src_path='/path/to/src',
        output_dir='/path/to/output_dir',
        profdata_path='/path/to/coverage.profdata',
        llvm_cov_path='/path/to/llvm-cov',
        binaries=['/path/to/binary1', '/path/to/binary2'],
        component_mapping=component_mapping,
        sources=[],
        diff_mapping=None)

    expected_compressed_components = [{
        'dirs': [
            {
                'path':
                    '//dir1/',
                'name':
                    'dir1/',
                'summaries': [{
                    'covered': 0,
                    'total': 1,
                    'name': 'region'
                }, {
                    'covered': 0,
                    'total': 1,
                    'name': 'function'
                }, {
                    'covered': 0,
                    'total': 1,
                    'name': 'line'
                }]
            },
            {
                'path':
                    '//dir2/',
                'name':
                    'dir2/',
                'summaries': [{
                    'covered': 1,
                    'total': 1,
                    'name': 'region'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'function'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'line'
                }]
            },
        ],
        'path':
            'Test>Component',
        'summaries': [{
            'covered': 1,
            'total': 2,
            'name': 'region'
        }, {
            'covered': 1,
            'total': 2,
            'name': 'function'
        }, {
            'covered': 1,
            'total': 2,
            'name': 'line'
        }]
    }]

    self.maxDiff = None
    self.assertListEqual(expected_compressed_components,
                         compressed_data['components'])

    expected_compressed_summaries = [{
        'covered': 1,
        'total': 2,
        'name': 'region'
    }, {
        'covered': 1,
        'total': 2,
        'name': 'function'
    }, {
        'covered': 1,
        'total': 2,
        'name': 'line'
    }]

    self.assertListEqual(expected_compressed_summaries,
                         compressed_data['summaries'])

    expected_compressed_dirs = [
        {
            'dirs': [
                {
                    'path':
                        '//dir1/',
                    'name':
                        'dir1/',
                    'summaries': [{
                        'covered': 0,
                        'total': 1,
                        'name': 'region'
                    }, {
                        'covered': 0,
                        'total': 1,
                        'name': 'function'
                    }, {
                        'covered': 0,
                        'total': 1,
                        'name': 'line'
                    }]
                },
                {
                    'path':
                        '//dir2/',
                    'name':
                        'dir2/',
                    'summaries': [{
                        'covered': 1,
                        'total': 1,
                        'name': 'region'
                    }, {
                        'covered': 1,
                        'total': 1,
                        'name': 'function'
                    }, {
                        'covered': 1,
                        'total': 1,
                        'name': 'line'
                    }]
                },
            ],
            'files': [],
            'summaries': [{
                'covered': 1,
                'total': 2,
                'name': 'region'
            }, {
                'covered': 1,
                'total': 2,
                'name': 'function'
            }, {
                'covered': 1,
                'total': 2,
                'name': 'line'
            }],
            'path':
                '//'
        },
        {
            'dirs': [],
            'files': [{
                'name':
                    'file1.cc',
                'path':
                    '//dir1/file1.cc',
                'summaries': [{
                    'covered': 0,
                    'total': 1,
                    'name': 'region'
                }, {
                    'covered': 0,
                    'total': 1,
                    'name': 'function'
                }, {
                    'covered': 0,
                    'total': 1,
                    'name': 'line'
                }]
            }],
            'summaries': [{
                'covered': 0,
                'total': 1,
                'name': 'region'
            }, {
                'covered': 0,
                'total': 1,
                'name': 'function'
            }, {
                'covered': 0,
                'total': 1,
                'name': 'line'
            }],
            'path':
                '//dir1/'
        },
        {
            'dirs': [],
            'files': [{
                'name':
                    'file2.cc',
                'path':
                    '//dir2/file2.cc',
                'summaries': [{
                    'covered': 1,
                    'total': 1,
                    'name': 'region'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'function'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'line'
                }]
            }],
            'summaries': [{
                'covered': 1,
                'total': 1,
                'name': 'region'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'function'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'line'
            }],
            'path':
                '//dir2/'
        },
    ]

    self.assertListEqual(expected_compressed_dirs, compressed_data['dirs'])

    expected_compressed_files = [
        {
            'path':
                '//dir1/file1.cc',
            'lines': [{
                'count': 0,
                'last': 5,
                'first': 5
            }],
            'total_lines':
                1,
            'uncovered_blocks': [{
                'ranges': [{
                    'last': 10,
                    'first': 2
                }],
                'line': 5
            }]
        },
        {
            'path': '//dir2/file2.cc',
            'lines': [{
                'count': 1,
                'last': 1,
                'first': 1
            }],
            'total_lines': 1
        },
    ]

    self.assertListEqual(expected_compressed_files, compressed_data['files'])


if __name__ == '__main__':
  unittest.main()
