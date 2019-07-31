#!/usr/bin/env vpython
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import json
import os
import sys
import unittest

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import gerrit_util


class GerritUtilTest(unittest.TestCase):

  @mock.patch('gerrit_util.urllib2.urlopen')
  def test_fetch_file_content_from_gerrit(self, mock_urlopen):
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


if __name__ == '__main__':
  unittest.main()
