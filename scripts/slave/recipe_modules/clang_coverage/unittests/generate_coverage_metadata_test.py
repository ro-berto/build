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

  # This test uses the following code:
  # 1|      1|int main() {
  # 2|      1|  if ((2 > 1) || (3 > 2)) {
  # 3|      1|    return 0;
  # 4|      1|  }
  # 5|      0|
  # 6|      0|  return 1;
  # 7|      0|}
  #
  # Where the first column is the line number and the second column is the
  # expected number of times the line is executed.
  def test_parse_exported_coverage_json(self):
    segments = [
        [1, 12, 1, True, True],
        [2, 7, 1, True, True],
        [2, 14, 1, True, False],
        [2, 18, 0, True, True],
        [2, 25, 1, True, False],
        [2, 27, 1, True, True],
        [4, 4, 0, True, False],
        [6, 3, 0, True, True],
        [7, 2, 0, False, False],
    ]

    expected_line_data = dict([(1, 1), (2, 1), (3, 1), (4, 1), (5, 0), (6, 0),
                               (7, 0)])
    expected_block_data = {2: [[18, 24]]}
    line_data, block_data = generator._extract_coverage_info(segments)
    self.assertDictEqual(expected_line_data, line_data)
    self.assertDictEqual(expected_block_data, block_data)

  # This test uses the following code:
  # 1|      1|int main() { return 0; }
  #
  # Where the first column is the line number and the second column is the
  # expected number of times the line is executed.
  def test_parse_exported_coverage_json_one_line(self):
    segments = [[1, 12, 1, True, True], [1, 25, 0, False, False]]

    expected_line_data = dict([(1, 1)])
    expected_block_data = {}
    line_data, block_data = generator._extract_coverage_info(segments)
    self.assertDictEqual(expected_line_data, line_data)
    self.assertDictEqual(expected_block_data, block_data)

  # This test uses the following code:
  # 1|      1|int main() {
  # 2|      1|  if ((2 > 1) || (3 > 2)) {
  # 3|      1|    return 0;
  # 4|      1|  }
  # 5|      0|
  # 6|      0|  return 1;
  # 7|      0|}
  #
  # Where the first column is the line number and the second column is the
  # expected number of times the line is executed.
  def test_to_compressed_file_record(self):
    src_path = '/path/to/chromium/src'
    file_coverage_data = {
        'segments': [
            [1, 12, 1, True, True],
            [2, 7, 1, True, True],
            [2, 14, 1, True, False],
            [2, 18, 0, True, True],
            [2, 25, 1, True, False],
            [2, 27, 1, True, True],
            [4, 4, 0, True, False],
            [6, 3, 0, True, True],
            [7, 2, 0, False, False],
        ],
        'summary': {
            'lines': {
                'count': 7,
            }
        },
        'filename':
            '/path/to/chromium/src/base/base.cc',
    }
    expected_record = {
        'path':
            'base/base.cc',
        'total_lines':
            7,
        'lines': [
            {
                'first': 1,
                'last': 4,
                'count': 1,
            },
            {
                'first': 5,
                'last': 7,
                'count': 0,
            },
        ],
        'uncovered_blocks': [{
            'line': 2,
            'ranges': [{
                'first': 18,
                'last': 24,
            }]
        }],
    }
    self.maxDiff = None
    record = generator._to_compressed_file_record(src_path, file_coverage_data)
    self.assertDictEqual(expected_record, record)

  # This test uses made-up segments, and the intention is to test that for
  # *uncontinous* regions, even if their lines are executed the same number of
  # times, when converted to compressed format, lines in different regions
  # shouldn't be merged together.
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

  # This test uses the following code:
  # 1|      1|int main() {
  # 2|      1|  if ((2 > 1) || (3 > 2)) {
  # 3|      1|    return 0;
  # 4|      1|  }
  # 5|      0|
  # 6|      0|  return 1;
  # 7|      0|}
  #
  # Where the first column is the line number and the second column is the
  # expected number of times the line is executed.
  def test_rebase_line_and_block_data(self):
    line_data = [(1, 1), (2, 1), (3, 1), (4, 1), (5, 0), (6, 0), (7, 0)]
    block_data = {2: [[18, 24]]}
    file_name = 'base/base.cc'
    diff_mapping = {'base/base.cc': {'2': [16, 'A line added by the patch.']}}

    rebased_line_data, rebased_block_data = (
        generator._rebase_line_and_block_data(line_data, block_data,
                                              diff_mapping[file_name]))

    expected_line_data = [(16, 1)]
    expected_block_data = {16: [[18, 24]]}
    self.maxDiff = None
    self.assertListEqual(expected_line_data, rebased_line_data)
    self.assertDictEqual(expected_block_data, rebased_block_data)

  # This test uses the following code:
  # 1|      1|int main() {
  # 2|      1|  if ((2 > 1) || (3 > 2)) {
  # 3|      1|    return 0;
  # 4|      1|  }
  # 5|      0|
  # 6|      0|  return 1;
  # 7|      0|}
  #
  # Where the first column is the line number and the second column is the
  # expected number of times the line is executed.
  def test_to_compressed_file_record_with_diff_mapping(self):
    src_path = '/path/to/chromium/src'
    file_coverage_data = {
        'segments': [
            [1, 12, 1, True, True],
            [2, 7, 1, True, True],
            [2, 14, 1, True, False],
            [2, 18, 0, True, True],
            [2, 25, 1, True, False],
            [2, 27, 1, True, True],
            [4, 4, 0, True, False],
            [6, 3, 0, True, True],
            [7, 2, 0, False, False],
        ],
        'summary': {
            'lines': {
                'count': 7,
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
            7,
        'lines': [
            {
                'first': 10,
                'last': 11,
                'count': 1,
            },
            {
                'first': 16,
                'last': 16,
                'count': 0,
            },
        ],
        'uncovered_blocks': [{
            'line': 10,
            'ranges': [{
                'first': 18,
                'last': 24,
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

  # This test uses the following code:
  # 1|      1|int main() {
  # 2|      1|  if ((2 > 1) || (3 > 2)) {
  # 3|      1|    return 0;
  # 4|      1|  }
  # 5|      0|
  # 6|      0|  return 1;
  # 7|      0|}
  #
  # Where the first column is the line number and the second column is the
  # expected number of times the line is executed.
  @mock.patch.object(generator, '_get_coverage_data_in_json')
  def test_generate_metadata_for_per_cl_coverage(self, mock_get_coverage_data):
    mock_get_coverage_data.return_value = {
        'data': [{
            'files': [{
                'segments': [[1, 12, 1, True, True], [2, 7, 1, True, True],
                             [2, 14, 1, True, False], [2, 18, 0, True, True],
                             [2, 25, 1, True, False], [2, 27, 1, True, True],
                             [4, 4, 0, True, False], [6, 3, 0, True, True],
                             [7, 2, 0, False, False]],
                'summary': {
                    'functions': {
                        'count': 1,
                        'covered': 1,
                        'percent': 100
                    },
                    'lines': {
                        'count': 7,
                        'covered': 4,
                        'percent': 57
                    },
                    'regions': {
                        'count': 6,
                        'covered': 4,
                        'notcovered': 2,
                        'percent': 67
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
            'count': 1,
            'last': 11,
            'first': 10
        }, {
            'count': 0,
            'last': 16,
            'first': 16
        }],
        'total_lines':
            7,
        'uncovered_blocks': [{
            'ranges': [{
                'last': 24,
                'first': 18
            }],
            'line': 10
        }]
    }]
    self.maxDiff = None
    self.assertListEqual(expected_compressed_files, compressed_data['files'])

  # This test uses the following code:
  # /path/to/src/dir1/file1.cc
  # 1|      1|int main() {
  # 2|      1|  if ((2 > 1) || (3 > 2)) {
  # 3|      1|    return 0;
  # 4|      1|  }
  # 5|      0|
  # 6|      0|  return 1;
  # 7|      0|}
  #
  # /path/to/src/dir2/file2.cc
  # 1|      1|int main() { return 0; }
  #
  # Where the first column is the line number and the second column is the
  # expected number of times the line is executed.
  @mock.patch.object(generator.repository_util, 'GetFileRevisions')
  @mock.patch.object(generator, '_get_coverage_data_in_json')
  def test_generate_metadata_for_full_repo_coverage(
      self, mock_get_coverage_data, mock_GetFileRevisions):
    # Number of files should not exceed 1000; otherwise sharding will happen.
    mock_GetFileRevisions.return_value = {
        '//dir1/file1.cc': ('hash1', 1234),
        '//dir2/file2.cc': ('hash2', 5678),
    }
    mock_get_coverage_data.return_value = {
        'data': [{
            'files': [
                {
                    'segments': [
                        [1, 12, 1, True, True],
                        [2, 7, 1, True, True],
                        [2, 14, 1, True, False],
                        [2, 18, 0, True, True],
                        [2, 25, 1, True, False],
                        [2, 27, 1, True, True],
                        [4, 4, 0, True, False],
                        [6, 3, 0, True, True],
                        [7, 2, 0, False, False],
                    ],
                    'summary': {
                        'functions': {
                            'count': 1,
                            'covered': 1,
                            'percent': 100
                        },
                        'lines': {
                            'count': 7,
                            'covered': 4,
                            'percent': 57
                        },
                        'regions': {
                            'count': 6,
                            'covered': 4,
                            'notcovered': 2,
                            'percent': 67
                        },
                    },
                    'filename':
                        '/path/to/src/dir1/file1.cc',
                },
                {
                    'segments': [[1, 12, 1, True, True],
                                 [1, 25, 0, False, False]],
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
                    'covered': 4,
                    'total': 6,
                    'name': 'region'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'function'
                }, {
                    'covered': 4,
                    'total': 7,
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
            'covered': 5,
            'total': 7,
            'name': 'region'
        }, {
            'covered': 2,
            'total': 2,
            'name': 'function'
        }, {
            'covered': 5,
            'total': 8,
            'name': 'line'
        }]
    }]

    self.maxDiff = None
    self.assertListEqual(expected_compressed_components,
                         compressed_data['components'])

    expected_compressed_summaries = [{
        'covered': 5,
        'total': 7,
        'name': 'region'
    }, {
        'covered': 2,
        'total': 2,
        'name': 'function'
    }, {
        'covered': 5,
        'total': 8,
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
                        'covered': 4,
                        'total': 6,
                        'name': 'region'
                    }, {
                        'covered': 1,
                        'total': 1,
                        'name': 'function'
                    }, {
                        'covered': 4,
                        'total': 7,
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
                'covered': 5,
                'total': 7,
                'name': 'region'
            }, {
                'covered': 2,
                'total': 2,
                'name': 'function'
            }, {
                'covered': 5,
                'total': 8,
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
                    'covered': 4,
                    'total': 6,
                    'name': 'region'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'function'
                }, {
                    'covered': 4,
                    'total': 7,
                    'name': 'line'
                }]
            }],
            'summaries': [{
                'covered': 4,
                'total': 6,
                'name': 'region'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'function'
            }, {
                'covered': 4,
                'total': 7,
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
                'count': 1,
                'last': 4,
                'first': 1,
            }, {
                'count': 0,
                'last': 7,
                'first': 5,
            }],
            'total_lines':
                7,
            'uncovered_blocks': [{
                'ranges': [{
                    'last': 24,
                    'first': 18,
                }],
                'line': 2
            }],
            'revision':
                'hash1',
            'timestamp':
                1234,
        },
        {
            'path': '//dir2/file2.cc',
            'lines': [{
                'count': 1,
                'last': 1,
                'first': 1
            }],
            'total_lines': 1,
            'revision': 'hash2',
            'timestamp': 5678,
        },
    ]

    self.assertListEqual(expected_compressed_files, compressed_data['files'])


if __name__ == '__main__':
  unittest.main()
