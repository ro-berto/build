#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for scripts/master/master_gen.py."""

import os
import tempfile
import unittest


# This adjusts sys.path, so it must be imported before the other modules.
import test_env

from master import master_gen


SAMPLE_BUILDERS_PY = """\
{
  "builders": {
    "Test Linux": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "slave_pools": ["main"],
      "slavebuilddir": "test"
    }
  },
  "git_repo_url": "https://chromium.googlesource.com/test/test.git",
  "master_base_class": "_FakeMaster",
  "master_port": 20999,
  "master_port_alt": 40999,
  "master_type": "waterfall",
  "slave_port": 30999,
  "slave_pools": {
    "main": {
      "slave_data": {
        "bits": 64,
        "os":  "linux",
        "version": "precise"
      },
      "slaves": ["vm9999-m1"],
    },
  },
  "templates": ["templates"],
}
"""


class _FakeMaster(object):
  in_production = False
  is_production_host = False
  project_name = 'test'
  project_url = 'https://example.com/'
  buildbucket_bucket = None

  @classmethod
  def GetBotPassword(cls):
    return ''


class PopulateBuildmasterConfigTest(unittest.TestCase):
  def test_waterfall(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_BUILDERS_PY)
      fp.close()

      setattr(_FakeMaster, '_FakeMaster', _FakeMaster)
      c = {}
      master_gen.PopulateBuildmasterConfig(c, fp.name, _FakeMaster)

      self.assertEqual(len(c['builders']), 1)
      self.assertEqual(c['builders'][0]['name'], 'Test Linux')

      self.assertEqual(len(c['change_source']), 1)
      self.assertEqual(len(c['schedulers']), 1)
    finally:
      os.remove(fp.name)

  def test_tryserver(self):
    try:
      contents = SAMPLE_BUILDERS_PY.replace('waterfall', 'tryserver')
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(contents)
      fp.close()

      setattr(_FakeMaster, '_FakeMaster', _FakeMaster)
      c = {}
      master_gen.PopulateBuildmasterConfig(c, fp.name, _FakeMaster)

      self.assertEqual(len(c['builders']), 1)
      self.assertEqual(c['builders'][0]['name'], 'Test Linux')

      self.assertEqual(len(c['change_source']), 0)
      self.assertEqual(len(c['schedulers']), 1)
    finally:
      os.remove(fp.name)



if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()
