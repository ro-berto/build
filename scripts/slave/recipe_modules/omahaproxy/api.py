# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cStringIO
import csv

from slave import recipe_api


class OmahaproxyApi(recipe_api.RecipeApi):
  """APIs for interacting with omahaproxy."""

  @staticmethod
  def split_version(text):
    result = [int(x) for x in text.split('.')]
    assert len(result) == 4
    return result

  def history(self, min_major_version=None):
    TEST_DATA = """os,channel,version,timestamp
        win,canary,41.0.2270.0,2015-01-08 19:48:09.982040
        linux,dev,41.0.2267.0,2015-01-06 19:58:10.377100
        mac,beta,36.0.1985.49,2014-06-04 17:40:47.808350"""
    raw_history = self.m.url.fetch(
        'https://omahaproxy.appspot.com/history',
        step_test_data=lambda: self.m.raw_io.test_api.output(TEST_DATA))
    csv_reader = csv.reader(cStringIO.StringIO(raw_history))
    data = list(csv_reader)
    header = data[0]
    for row in data[1:]:
      candidate = {header[i]: row[i] for i in range(len(row))}
      if (min_major_version and
          self.split_version(candidate['version'])[0] < min_major_version):
        continue
      yield candidate
