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

    # IOError is a super class of ssl.SSLError, which we are getting when the
    # requests time out.
    for exc_class in (urllib2.URLError, IOError):
      with mock.patch('slave.build_scan.time.sleep') as sleep_mock:
        with mock.patch('slave.build_scan.urllib2.urlopen') as func:
          func.side_effect = [exc_class('test error'), StringIO.StringIO(
              json.dumps(wanted))]

          result = build_scan._url_open_json('url')
          self.assertEqual(result, wanted)
          self.assertEqual(sleep_mock.call_args_list, [mock.call(2)])
          self.assertEqual(len(func.call_args_list), 2)
          for call_itm in func.call_args_list:
            self.assertIsInstance(call_itm[0][0], urllib2.Request)
            self.assertEqual(call_itm[0][0].get_full_url(), 'url')
            self.assertEqual(call_itm[1], {'timeout': 30})


if __name__ == '__main__':
  with utils.print_coverage(include=['build_scan.py']):
    unittest.main()
