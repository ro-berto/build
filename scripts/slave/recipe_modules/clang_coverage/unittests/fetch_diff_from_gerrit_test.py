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

import fetch_diff_from_gerrit


class FetchDiffFromGerritTest(unittest.TestCase):

  @mock.patch('fetch_diff_from_gerrit.sys.stdout')
  @mock.patch('fetch_diff_from_gerrit.urllib2.urlopen')
  def test_fetch_diff_from_gerrit(self, mock_urlopen, mock_stdout):
    revisions = {
        'revisions': {
            'da745617c0329e2a5faf53cbd577047d789e909d': {
                '_number': 1
            }
        }
    }
    gerrit_diff = ('diff --git a/path/test.txt b/path/test.txt\n'
                   'index 0719398930..4a2b716881 100644\n'
                   '--- a/path/test.txt\n'
                   '+++ b/path/test.txt\n'
                   '@@ -10,2 +10,3 @@\n'
                   ' Line 10\n'
                   '-Line 11\n'
                   '+A different line 11\n'
                   '+A newly added line 12\n')

    mock_urlopen().read.side_effect = [
        ')]}\n' + json.dumps(revisions),
        base64.b64encode(gerrit_diff)
    ]
    fetch_diff_from_gerrit.fetch_diff(
        'chromium-review.googlesource.com', 'chromium/src', 123456, 1)
    mock_stdout.called_once_with(gerrit_diff)


if __name__ == '__main__':
  unittest.main()
