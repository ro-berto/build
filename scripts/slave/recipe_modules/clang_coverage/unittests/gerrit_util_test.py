#!/usr/bin/env vpython
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import json
import os
import sys
import tempfile
import unittest

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import gerrit_util


class GerritUtilTest(unittest.TestCase):

  @mock.patch('gerrit_util.urllib2.urlopen')
  def test_fetch_diff_from_gerrit(self, mock_urlopen):
    revisions = {
        'revisions': {
            'da745617c0329e2a5faf53cbd577047d789e909d': {
                '_number': 1
            }
        }
    }
    file_content = 'line one\nline two\n'

    mock_urlopen().getcode.side_effect = [404, 200, 404, 200]
    mock_urlopen().read.side_effect = [
        ')]}\n' + json.dumps(revisions),
        base64.b64encode(file_content)
    ]

    result = gerrit_util.fetch_files_content('chromium-review.googlesource.com',
                                             'chromium/src', 123456, 1,
                                             ['dir/test.cc'])
    self.assertEqual([file_content], result)

  def test_generate_line_number_mapping_same_file(self):
    from_file = tempfile.NamedTemporaryFile()
    from_file.write('The same content\n')
    from_file.flush()

    to_file = tempfile.NamedTemporaryFile()
    to_file.write('The same content\n')
    to_file.flush()

    line_num_mapping = gerrit_util.generate_line_number_mapping(
        from_file.name, to_file.name)
    self.assertDictEqual({1: (1, 'The same content')}, line_num_mapping)

  def test_generate_line_number_mapping_one_diff_section(self):
    from_file = tempfile.NamedTemporaryFile()
    from_file_content = ('line 1\n' 'line 2\n' 'line 3\n')
    from_file.write(from_file_content)
    from_file.flush()

    to_file = tempfile.NamedTemporaryFile()
    to_file_content = ('line 2, changed\n' 'line 3\n')
    to_file.write(to_file_content)
    to_file.flush()

    line_num_mapping = gerrit_util.generate_line_number_mapping(
        from_file.name, to_file.name)
    self.assertDictEqual({3: (2, 'line 3')}, line_num_mapping)

  def test_generate_line_number_mapping_multiple_diff_section(self):
    from_file = tempfile.NamedTemporaryFile()
    from_file_content = ('line 1\n'
                         'line 2\n'
                         'line 3\n'
                         'line 4\n'
                         'line 5\n'
                         'line 6\n'
                         'line 7\n'
                         'line 9\n'
                         'line 9\n'
                         'line 10\n'
                         'line 11\n'
                         'line 12\n'
                         'line 13\n'
                         'line 14\n'
                         'line 15\n')
    from_file.write(from_file_content)
    from_file.flush()

    to_file = tempfile.NamedTemporaryFile()
    to_file_content = (
        'line 1\n'
        'line 3, changed\n'  # line 2 removed and line 3 changed.
        'line 4\n'
        'line 5\n'
        'line 6\n'
        'line 7\n'
        'line 9\n'
        'line 9\n'
        'line 10\n'
        'line 11\n'
        'line 12\n'
        'line 13\n'
        'line 14, changed\n'  # line 14 changed.
        'line 15\n')
    to_file.write(to_file_content)
    to_file.flush()

    line_num_mapping = gerrit_util.generate_line_number_mapping(
        from_file.name, to_file.name)
    self.assertDictEqual({
        1: (1, 'line 1'),
        4: (3, 'line 4'),
        5: (4, 'line 5'),
        6: (5, 'line 6'),
        7: (6, 'line 7'),
        8: (7, 'line 9'),
        9: (8, 'line 9'),
        10: (9, 'line 10'),
        11: (10, 'line 11'),
        12: (11, 'line 12'),
        13: (12, 'line 13'),
        15: (14, 'line 15')
    }, line_num_mapping)


if __name__ == '__main__':
  unittest.main()
