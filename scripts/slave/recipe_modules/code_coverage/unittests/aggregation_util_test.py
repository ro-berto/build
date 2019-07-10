#!/usr/bin/env vpython
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import aggregation_util


class AggregationUtilTest(unittest.TestCase):

  def test_basic(self):
    files_coverage_data = [
        {
            'path': '//dir/file.cc',
            'lines': [{
                'first': 1,
                'last': 1,
                'count': 1,
            }],
            'total_lines': 1,
            'summaries': [{
                'name': 'line',
                'covered': 1,
                'total': 1,
            }],
        },
    ]

    dir_to_component = {'dir': 'Test>Component'}
    per_directory_data, per_component_data = (
        aggregation_util.get_aggregated_coverage_data_from_files(
            files_coverage_data, dir_to_component))

    expected_per_directory_data = {
        '//': {
            'dirs': [{
                'name': 'dir/',
                'path': '//dir/',
                'summaries': [{
                    'name': 'line',
                    'covered': 1,
                    'total': 1,
                }]
            }],
            'files': [],
            'path':
                '//',
            'summaries': [{
                'name': 'line',
                'covered': 1,
                'total': 1,
            }]
        },
        '//dir/': {
            'dirs': [],
            'files': [{
                'name': 'file.cc',
                'path': '//dir/file.cc',
                'summaries': [{
                    'name': 'line',
                    'covered': 1,
                    'total': 1,
                }]
            }],
            'path':
                '//dir/',
            'summaries': [{
                'name': 'line',
                'covered': 1,
                'total': 1,
            }]
        }
    }

    expected_per_component_data = {
        'Test>Component': {
            'dirs': [{
                'name': 'dir/',
                'path': '//dir/',
                'summaries': [{
                    'name': 'line',
                    'covered': 1,
                    'total': 1,
                }]
            }],
            'path':
                'Test>Component',
            'summaries': [{
                'name': 'line',
                'covered': 1,
                'total': 1,
            }]
        }
    }

    self.maxDiff = None
    self.assertDictEqual(expected_per_directory_data, per_directory_data)
    self.assertDictEqual(expected_per_component_data, per_component_data)

  def test_avoid_component_double_counting(self):
    files_coverage_data = [
        {
            'path': '//dir/file1.cc',
            'lines': [{
                'first': 1,
                'last': 1,
                'count': 1,
            }],
            'total_lines': 1,
            'summaries': [{
                'name': 'line',
                'covered': 1,
                'total': 1,
            }],
        },
        {
            'path': '//dir/subdir/file2.cc',
            'lines': [{
                'first': 1,
                'last': 2,
                'count': 1,
            }],
            'total_lines': 2,
            'summaries': [{
                'name': 'line',
                'covered': 2,
                'total': 2,
            }],
        },
    ]

    dir_to_component = {'dir': 'Test>Component', 'dir/subdir': 'Test>Component'}
    per_directory_data, per_component_data = (
        aggregation_util.get_aggregated_coverage_data_from_files(
            files_coverage_data, dir_to_component))

    expected_per_directory_data = {
        '//': {
            'dirs': [{
                'name': 'dir/',
                'path': '//dir/',
                'summaries': [{
                    'name': 'line',
                    'covered': 3,
                    'total': 3
                }]
            }],
            'files': [],
            'path':
                '//',
            'summaries': [{
                'name': 'line',
                'covered': 3,
                'total': 3
            }]
        },
        '//dir/': {
            'dirs': [{
                'name': 'subdir/',
                'path': '//dir/subdir/',
                'summaries': [{
                    'name': 'line',
                    'covered': 2,
                    'total': 2
                }]
            }],
            'files': [{
                'name': 'file1.cc',
                'path': '//dir/file1.cc',
                'summaries': [{
                    'name': 'line',
                    'covered': 1,
                    'total': 1
                }]
            }],
            'path':
                '//dir/',
            'summaries': [{
                'name': 'line',
                'covered': 3,
                'total': 3
            }]
        },
        '//dir/subdir/': {
            'dirs': [],
            'files': [{
                'name': 'file2.cc',
                'path': '//dir/subdir/file2.cc',
                'summaries': [{
                    'name': 'line',
                    'covered': 2,
                    'total': 2
                }]
            }],
            'path':
                '//dir/subdir/',
            'summaries': [{
                'name': 'line',
                'covered': 2,
                'total': 2
            }]
        }
    }

    expected_per_component_data = {
        'Test>Component': {
            'dirs': [{
                'name': 'dir/',
                'path': '//dir/',
                'summaries': [{
                    'name': 'line',
                    'covered': 3,
                    'total': 3
                }]
            }],
            'path':
                'Test>Component',
            'summaries': [{
                'name': 'line',
                'covered': 3,
                'total': 3
            }]
        }
    }

    self.maxDiff = None
    self.assertDictEqual(expected_per_directory_data, per_directory_data)
    self.assertDictEqual(expected_per_component_data, per_component_data)


if __name__ == '__main__':
  unittest.main()
