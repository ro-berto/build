#!/usr/bin/env vpython3
# Copyright 2018 The Chromium Authors. All rights reserved.
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

import gerrit_util
import rebase_line_number_from_bot_to_gerrit


class RebaseLineNumberFromBotToGerritTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.host = 'chromium-review.googlesource.com'
    self.project = 'chromium/src'
    self.change = 123456
    self.patchset = 1

  @mock.patch.object(gerrit_util, 'fetch_files_content')
  def test_rebase_line_number(self, mocked_fetch_files_content):
    file_on_gerrit_content = 'line 1\nline 2, changed by me\nline 3\n'
    mocked_fetch_files_content.return_value = [file_on_gerrit_content]

    file_on_bot = tempfile.NamedTemporaryFile()
    file_on_bot.write(b'line 0, added by someone else\n'
                      b'line 1, changed by someone else\n'
                      b'line 2, changed by me\n')
    file_on_bot.flush()

    file_on_bot_path = file_on_bot.name
    file_to_line_num_mapping = (
        rebase_line_number_from_bot_to_gerrit.rebase_line_number(
            self.host, self.project, self.change, self.patchset,
            os.path.dirname(file_on_bot_path),
            [os.path.basename(file_on_bot_path)]))

    self.assertEqual({
        os.path.basename(file_on_bot_path): {
            3: (2, 'line 2, changed by me')
        }
    }, file_to_line_num_mapping)
    mocked_fetch_files_content.assert_called_with(
        self.host, self.project, self.change, self.patchset,
        [os.path.basename(file_on_bot_path)])

  @mock.patch.object(gerrit_util, 'fetch_files_content')
  def test_rebase_line_number_with_deleted_file(self,
                                                mocked_fetch_files_content):
    mocked_fetch_files_content.return_value = ['test line\n']
    file_on_bot = tempfile.NamedTemporaryFile()
    file_on_bot.write(b'test line\n')
    file_on_bot.flush()

    file_on_bot_path = file_on_bot.name
    rebase_line_number_from_bot_to_gerrit.rebase_line_number(
        self.host, self.project, self.change, self.patchset,
        os.path.dirname(file_on_bot_path),
        [os.path.basename(file_on_bot_path), 'non_exist_file'])

    mocked_fetch_files_content.assert_called_with(
        self.host, self.project, self.change, self.patchset,
        [os.path.basename(file_on_bot_path)])

  @mock.patch.object(gerrit_util, 'fetch_files_content')
  def test_rebase_line_number_with_deleted_file_only(
      self, mocked_fetch_files_content):
    file_to_line_num_mapping = (
        rebase_line_number_from_bot_to_gerrit.rebase_line_number(
            self.host, self.project, self.change, self.patchset, '/checkout',
            ['non_exist_file']))

    mocked_fetch_files_content.assert_called_with(
        self.host, self.project, self.change, self.patchset, [])
    self.assertDictEqual({}, file_to_line_num_mapping)


if __name__ == '__main__':
  unittest.main()
