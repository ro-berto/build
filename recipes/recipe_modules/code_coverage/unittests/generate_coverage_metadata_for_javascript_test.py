#!/usr/bin/env vpython
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import tempfile
import unittest

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import generate_coverage_metadata_for_javascript as generator


class GenerateCoverageMetadataForJavaScriptTest(unittest.TestCase):

  MOCK_LINE_COLUMN_FORMAT_OUTPUT = (
      # Covered lines
      [{
          'count': 3,
          'last': 3,
          'first': 1
      }, {
          'count': 1,
          'last': 4,
          'first': 4
      }, {
          'count': 2,
          'last': 6,
          'first': 5
      }, {
          'count': 0,
          'first': 7,
          'last': 7
      }, {
          'count': 2,
          'last': 9,
          'first': 8
      }, {
          'count': 3,
          'last': 10,
          'first': 10
      }, {
          'count': 1,
          'last': 11,
          'first': 11
      }],
      # Uncovered blocks
      [{
          'ranges': [{
              'end': 18,
              'first': 16
          }],
          'line': 6
      }, {
          'ranges': [{
              'end': 17,
              'first': 0
          }],
          'line': 7
      }, {
          'ranges': [{
              'end': 3,
              'first': 0
          }],
          'line': 8
      }])

  @mock.patch.object(os, 'listdir')
  def test_get_json_files_ignores_everything_else(self, mock_listdir):
    mock_input_dir_listdir = [
        '/b/some/path/browser_tests_javascript.json',
        '/b/some/path/unexpected_file.txt',
        '/b/some/path/tests',
        '/b/some/path/scripts',
    ]
    mock_listdir.return_value = mock_input_dir_listdir

    expected_output = [
        '/b/some/path/browser_tests_javascript.json',
    ]
    actual_output = generator.get_json_coverage_files('/b/some/path')
    self.assertListEqual(expected_output, actual_output)

  @mock.patch.object(os.path, 'exists')
  def test_get_source_files_returns_relative_paths(self, mock_exists):
    mock_input_coverage_info = '{ \
      "//relative/path/to/file/a.js": [{"end": 100, "count": 2}], \
      "//relative/path/to/file/b.js": [{"end": 200, "count": 1}] \
    }'

    mock_exists.side_effect = [True, True]

    actual_output = []
    with mock.patch.object(
        generator,
        'open',
        mock.mock_open(read_data=mock_input_coverage_info),
        create=True):
      actual_output = generator.get_coverage_data_and_paths(
          '/b/some/path/src', '/b/some/path/coverage_data.json')

    expected_output = {
        '/b/some/path/src/relative/path/to/file/a.js': [{
            'end': 100,
            'count': 2
        }],
        '/b/some/path/src/relative/path/to/file/b.js': [{
            'end': 200,
            'count': 1
        }]
    }

    self.assertEqual(actual_output, expected_output)

  @mock.patch.object(os.path, 'exists')
  def test_get_source_files_nonexistant_path_fails(self, mock_exists):
    mock_input_coverage_info = '{ \
      "//relative/path/to/file/a.js": [], \
      "//relative/path/to/file/b.js": [] \
    }'

    # Return False for the first absolute path indicating
    # the file /b/some/path/src/relative/path/to/file/a.js
    # does not exist.
    mock_exists.side_effect = [False, True]

    with mock.patch.object(
        generator,
        'open',
        mock.mock_open(read_data=mock_input_coverage_info),
        create=True):
      with self.assertRaises(Exception):
        generator.get_coverage_data_and_paths(
            '/b/some/path/src', '/b/some/path/coverage_data.json')

  def test_convert_to_line_column(self):
    mock_source_file = 'exports.test = arg => { return arg ? "y" : "n" }'
    mock_coverage_blocks = [{
        'end': 41,
        'count': 1
    }, {
        'end': 46,
        'count': 0
    }, {
        'end': 48,
        'count': 1
    }]

    expected_output = (
        # Covered lines
        [{
            'count': 1,
            'first': 1,
            'last': 1
        }],
        # Uncovered Blocks
        [{
            'ranges': [{
                'end': 46,
                'first': 41
            }],
            'line': 1
        }],
    )

    with tempfile.NamedTemporaryFile(suffix='.js', mode='w+') as f:
      f.write(mock_source_file)
      f.seek(0, os.SEEK_SET)

      output = generator.convert_coverage_to_line_column_format(
          f.name, mock_coverage_blocks)

      self.assertEqual(output, expected_output)

  def test_convert_to_line_column_coverage_offset_smaller_than_file(self):
    mock_source_file = 'exports.test = arg => { return arg ? "yes" : "no" }'
    mock_coverage_blocks = [{
        'end': 41,
        'count': 1
    }, {
        'end': 46,
        'count': 0
    }, {
        'end': 48,
        'count': 1
    }]

    with tempfile.NamedTemporaryFile(suffix='.js', mode='w+') as f:
      f.write(mock_source_file)
      f.seek(0, os.SEEK_SET)

      with self.assertRaises(Exception):
        generator.convert_coverage_to_line_column_format(
            f.name, mock_coverage_blocks)

  def test_convert_to_line_column_coverage_offset_bigger_than_file(self):
    mock_source_file = 'exports.test = arg => { return arg ? "y" : "n" }'
    mock_coverage_blocks = [{
        'end': 41,
        'count': 1
    }, {
        'end': 46,
        'count': 0
    }, {
        'end': 50,
        'count': 1
    }]

    with tempfile.NamedTemporaryFile(suffix='.js', mode='w+') as f:
      f.write(mock_source_file)
      f.seek(0, os.SEEK_SET)

      with self.assertRaises(Exception):
        generator.convert_coverage_to_line_column_format(
            f.name, mock_coverage_blocks)

  def test_convert_to_line_column_multiple_lines(self):
    mock_source_file = 'function test(arg) {\n\
  arg += 1;\n\
  if (arg == 2) {\n\
    return "yes";\n\
  }\n\
  if (arg == 3) {\n\
    return "no";\n\
  }\n\
  return "maybe";\n\
}\n\
exports.test = test;'

    mock_coverage_blocks = [{
        'count': 3,
        'end': 49
    }, {
        'count': 1,
        'end': 72
    }, {
        'count': 2,
        'end': 89
    }, {
        'count': 0,
        'end': 111
    }, {
        'count': 2,
        'end': 130
    }, {
        'count': 3,
        'end': 131
    }, {
        'count': 1,
        'end': 152
    }]

    expected_output = self.MOCK_LINE_COLUMN_FORMAT_OUTPUT

    with tempfile.NamedTemporaryFile(suffix='.js', mode='w+') as f:
      f.write(mock_source_file)
      f.seek(0, os.SEEK_SET)

      output = generator.convert_coverage_to_line_column_format(
          f.name, mock_coverage_blocks)
      self.assertEqual(output, expected_output)

  def test_get_files_coverage_data_duplicate_files_exception(self):
    absolute_checkout_path = '/b/some/src'

    coverage_data_one = {
        absolute_checkout_path + '/relative/path/to/file/a.js': [{
            'end': 100,
            'count': 2
        },],
        absolute_checkout_path + '/relative/path/to/file/b.js': [{
            'end': 150,
            'count': 1
        },],
    }

    coverage_data_two = {
        absolute_checkout_path + '/relative/path/to/file/a.js': [{
            'end': 100,
            'count': 2
        },],
        absolute_checkout_path + '/relative/path/to/file/c.js': [{
            'end': 200,
            'count': 4
        },],
    }

    mock_get_coverage_data_and_paths = mock.Mock()
    mock_convert_coverage_to_line_column_format = mock.Mock()

    with mock.patch.object(generator, 'get_coverage_data_and_paths',
                           mock_get_coverage_data_and_paths):

      with mock.patch.object(generator,
                             'convert_coverage_to_line_column_format',
                             mock_convert_coverage_to_line_column_format):

        mock_get_coverage_data_and_paths.side_effect = [
            coverage_data_one, coverage_data_two
        ]
        mock_convert_coverage_to_line_column_format.return_value = ('covered',
                                                                    'uncovered')
        with self.assertRaises(Exception):
          generator.get_files_coverage_data('/b/some/src', [
              '/b/some/src/out/Default/coverage_one.json',
              '/b/some/src/out/Default/coverage_two.json'
          ])

  def test_get_files_coverage_data_paths_relative_to_src(self):
    coverage_data_one = {
        '/b/some/src/path/to/file/a.js': [{
            'end': 100,
            'count': 2
        },],
        '/b/some/src/path/to/file/b.js': [{
            'end': 150,
            'count': 1
        },],
    }

    coverage_data_two = {
        '/b/some/src/path/to/file/c.js': [{
            'end': 100,
            'count': 2
        },],
        '/b/some/src/path/to/file/d.js': [{
            'end': 200,
            'count': 4
        },],
    }

    expected_relative_paths = [
        '//path/to/file/a.js',
        '//path/to/file/b.js',
        '//path/to/file/c.js',
        '//path/to/file/d.js',
    ]

    mock_get_coverage_data_and_paths = mock.Mock()
    mock_convert_coverage_to_line_column_format = mock.Mock()

    with mock.patch.object(generator, 'get_coverage_data_and_paths',
                           mock_get_coverage_data_and_paths):

      with mock.patch.object(generator,
                             'convert_coverage_to_line_column_format',
                             mock_convert_coverage_to_line_column_format):

        mock_get_coverage_data_and_paths.side_effect = [
            coverage_data_one, coverage_data_two
        ]

        mock_convert_coverage_to_line_column_format.return_value = \
            self.MOCK_LINE_COLUMN_FORMAT_OUTPUT
        output = generator.get_files_coverage_data('/b/some/src', [
            '/b/some/src/out/Default/coverage_one.json',
            '/b/some/src/out/Default/coverage_two.json'
        ])

        for file_data in output:
          self.assertIn(file_data['path'], expected_relative_paths)

  def test_get_line_coverage_metric_summary(self):
    input_line_range = [
        {
            'count': 1,
            'first': 1,
            'last': 5
        },
        {
            'count': 0,
            'first': 6,
            'last': 6
        },
        {
            'count': 1,
            'first': 7,
            'last': 11
        },
        {
            'count': 0,
            'first': 12,
            'last': 15
        },
    ]

    expected_output = {
        'name': 'line',
        'total': 15,
        'covered': 10,
    }

    output = generator.get_line_coverage_metric_summary(input_line_range)
    self.assertEqual(output, expected_output)

  def test_get_line_coverage_metric_summary_no_line_coverage(self):
    input_line_range = [
        {
            'count': 0,
            'first': 1,
            'last': 5
        },
        {
            'count': 0,
            'first': 6,
            'last': 6
        },
        {
            'count': 0,
            'first': 7,
            'last': 11
        },
        {
            'count': 0,
            'first': 12,
            'last': 15
        },
    ]

    expected_output = {
        'name': 'line',
        'total': 15,
        'covered': 0,
    }

    output = generator.get_line_coverage_metric_summary(input_line_range)
    self.assertEqual(output, expected_output)

  def test_get_line_coverage_metric_summary_all_covered(self):
    input_line_range = [
        {
            'count': 3,
            'first': 1,
            'last': 5
        },
        {
            'count': 1,
            'first': 6,
            'last': 6
        },
        {
            'count': 5,
            'first': 7,
            'last': 11
        },
        {
            'count': 8,
            'first': 12,
            'last': 15
        },
    ]

    expected_output = {
        'name': 'line',
        'total': 15,
        'covered': 15,
    }

    output = generator.get_line_coverage_metric_summary(input_line_range)
    self.assertEqual(output, expected_output)


if __name__ == '__main__':
  unittest.main()
