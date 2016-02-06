#!/usr/bin/python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..'))
import common.env
common.env.Install()

import mock
import requests

import crrev  # pylint: disable=relative-import


@mock.patch('requests.get')
class CommitPositionTest(unittest.TestCase):

  def test_has_commit_position(self, mock_get):
    mock_response  = mock.MagicMock()
    mock_response.text = '{"number": 1234}'
    mock_get.return_value = mock_response
    self.assertEqual(1234, crrev.commit_position('git_hash'))
    mock_get.assert_called_once_with(
        'https://cr-rev.appspot.com/_ah/api/crrev/v1/commit/git_hash', verify=True)

  def test_has_no_commit_position(self, mock_get):
    mock_response = mock.MagicMock()
    mock_response.text = '{"repo": "catapult"}'
    mock_get.return_value = mock_response
    with self.assertRaises(ValueError):
      crrev.commit_position('git_hash')


@mock.patch('requests.get')
class CommitHashTest(unittest.TestCase):

  def test_commit_hash(self, mock_get):
    mock_response = mock.MagicMock()
    mock_response.text = json.dumps({
        'git_sha': '10b9b4435e25fb8ede2122482426ae81c7980630',
        'repo': 'chromium/src',
        'project': 'chromium',
        'redirect_type': 'GIT_FROM_NUMBER',
        'repo_url': 'https://chromium.googlesource.com/chromium/src/',
    })
    mock_get.return_value = mock_response
    self.assertEqual(
        '10b9b4435e25fb8ede2122482426ae81c7980630',
        crrev.commit_hash(368595))
    mock_get.assert_called_once_with(
        'https://cr-rev.appspot.com/_ah/api/crrev/v1/redirect/368595', verify=True)

  def test_404(self, mock_get):
    mock_response = mock.MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    with self.assertRaises(ValueError):
      crrev.commit_hash(123456)

  def test_other_redirect_type(self, mock_get):
    mock_response = mock.MagicMock()
    mock_response.text = json.dumps({
        'redirect_type': 'RIETVELD',
        'redirect_url': 'https://codereview.chromium.org/1582793006',
    })
    mock_get.return_value = mock_response
    with self.assertRaises(ValueError):
      crrev.commit_hash(1582793006)


if __name__ == '__main__':
  unittest.main()

