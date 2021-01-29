#!/usr/bin/env vpython
# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import os
import sys
import unittest

import test_env  # pylint: disable=relative-import

import goma_utils


class GomaUtilTest(unittest.TestCase):

  def testGetLogFileTimestamp(self):
    self.assertEquals(
        datetime.datetime(2006, 1, 2, 15, 4, 5),
        goma_utils.
        GetLogFileTimestamp('gomacc.host.user.log.INFO.20060102-150405.123456')
    )


if __name__ == '__main__':
  unittest.main()
