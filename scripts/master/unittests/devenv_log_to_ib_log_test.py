#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import unittest

import test_env

from master.log_parser import cl_command


class DevenvLogToIbLogTest(unittest.TestCase):

  def testConvert(self):
    source_log = open(os.path.join(test_env.DATA_PATH,
                                   'error-log-compile-stdio-devenv'))
    expected_result_log = open(
        os.path.join(test_env.DATA_PATH,
                     'error-log-compile-stdio-devenv-converted'))
    converted_content = cl_command.DevenvLogToIbLog(source_log.read()).Convert()
    self.assertEqual(expected_result_log.read(), converted_content)

    source_log.close()
    expected_result_log.close()


if __name__ == '__main__':
  unittest.main()
