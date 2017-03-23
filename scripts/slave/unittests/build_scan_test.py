#!/usr/bin/env python
# coding=utf-8
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for build_scan.py"""

# Needs to be at the top, otherwise coverage will spit nonsense.
import utils  # "relative import" pylint: disable=W0403

import json
import mock
import os
import StringIO
import unittest
import urllib
import urllib2

import test_env  # pylint: disable=W0403,W0611

from slave import build_scan

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class BuildScanTest(unittest.TestCase):
  def testURLRetry(self):
    wanted = {'a': 'hi'}

    with mock.patch('slave.build_scan.time.sleep') as sleep_mock:
      err_resp = mock.Mock()
      err_resp.status = 500
      resp = mock.Mock()
      resp.status = 200
      http = mock.Mock()
      http.request.side_effect = [
          (err_resp, None), (resp, '}]);' + json.dumps(wanted))]

      result = build_scan._get_from_milo('endpoint', 'data', http=http)
      self.assertEqual(result, wanted)
      self.assertEqual(sleep_mock.call_args_list, [mock.call(2)])
      self.assertEqual(len(http.request.call_args_list), 2)


if __name__ == '__main__':
  with utils.print_coverage(include=['build_scan.py']):
    unittest.main()
