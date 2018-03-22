#!/usr/bin/env vpython
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""pusub_json_status_push unit tests"""

import unittest
import zlib
from cStringIO import StringIO

import test_env  # pylint: disable=relative-import

from master.pubsub_json_status_push import StatusPush, MessageTooBigError


class PubSubJsonStatusPush(unittest.TestCase):
  def setUp(self):
    super(PubSubJsonStatusPush, self).setUp()
    self._old_compress = getattr(zlib, 'compress')
    setattr(zlib, 'compress', lambda x: x)

  def tearDown(self):
    setattr(zlib, 'compress', self._old_compress)


  def test_batch_data_no_builds(self):
    master = {'foo': 'bar'}
    builds = []
    sp = StatusPush(None, 'fake', None)
    data = list(sp._get_pubsub_messages(master, builds))
    self.assertEquals(len(data), 1)

  def test_batch_data_5_builds(self):
    master = {'foo': 'bar'}
    builds = ['#' * 1000000 for _ in xrange(5)]
    sp = StatusPush(None, 'fake', None)
    data = list(sp._get_pubsub_messages(master, builds))
    self.assertEquals(len(data), 1)

  def test_batch_data_10_builds(self):
    master = {'foo': 'bar'}
    builds = ['#' * 1000000 for _ in xrange(10)]
    sp = StatusPush(None, 'fake', None)
    self.assertRaises(
        MessageTooBigError, list, sp._get_pubsub_messages(master, builds))
    self.assertEquals(sp._splits, 2)
    data = list(sp._get_pubsub_messages(master, builds))
    self.assertEquals(len(data), 2)


if __name__ == '__main__':
  unittest.main()
