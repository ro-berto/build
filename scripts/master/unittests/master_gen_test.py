#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for scripts/master/master_gen.py."""

import os
import tempfile
import unittest


# This adjusts sys.path, so it must be imported before the other modules.
import test_env  # pylint: disable=W0403

from buildbot.schedulers.basic import AnyBranchScheduler

from master import master_gen


SAMPLE_WATERFALL_PYL = """\
{
  "master_base_class": "_FakeMasterBase",
  "master_port": 20999,
  "master_port_alt": 40999,
  "bot_port": 30999,
  "templates": ["templates"],

  "builder_defaults": {
    "recipe": "test_recipe",
    "properties": {
      "config": "Release",
    },
    "scheduler": "test_repo",
    "bot_pool": "main",
    "botbuilddir": "test",
  },

  "builders": {
    "Test Linux": {
    },
    "Test Linux Timeouts": {
      "builder_timeout_s": 7200,
      "no_output_timeout_s": 3600,
    },
    "Test Linux Remote Run": {
      "use_remote_run": True,
      "remote_run_repository": "some_git_url",
    },
    "Test Linux Nightly": {
      "recipe": "test_nightly_recipe",
      "scheduler": "nightly",
      "category": "0nightly"
    },
    "Test Linux Build Everything": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "scheduler": "test_all",
      "bot_pools": ["main"],
      "botbuilddir": "test",
      "category": "1all"
    },
  },

  "schedulers": {
    "nightly": {
      "type": "cron",
      "hour": 4,
      "minute": 15,
    },
    "test_repo": {
      "type": "git_poller",
      "git_repo_url": "https://chromium.googlesource.com/test/test.git",
    },
    "test_all": {
      "type": "git_poller_any",
      "git_repo_url": "https://chromium.googlesource.com/test/test.git",
      "branch": [r"refs/branch\-heads/\d+\.\d+", r"refs/heads/.*"],
    },
  },

  "bot_pools": {
    "main": {
      "os":  "linux",
      "version": "precise",
      "bots": "vm9999-m1",
    },
  },
}
"""


SAMPLE_TRYSERVER_PYL = """\
{
  "master_base_class": "_FakeMasterBase",
  "master_port": 20999,
  "master_port_alt": 40999,
  "bot_port": 30999,
  "buildbucket_bucket": "fake_bucket",
  "service_account_file": "fake_service_account",
  "templates": ["templates"],

  "builders": {
    "Test Linux": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "scheduler": None,
      "bot_pools": ["main"],
      "botbuilddir": "test"
    }
  },

  "schedulers": {},

  "bot_pools": {
    "main": {
      "os":  "linux",
      "version": "precise",
      "bots": "vm{9998..9999}-m1",
    },
  },
}
"""

# This class fakes the base class from master_site_config.py.
class _FakeMasterBase(object):
  in_production = False
  is_production_host = False


# This class fakes the actual master class in master_site_config.py.
class _FakeMaster(_FakeMasterBase):
  project_name = 'test'
  master_port = '20999'
  slave_port = '30999'
  master_port_alt = '40999'
  buildbot_url = 'https://build.chromium.org/p/test'
  buildbucket_bucket = None
  service_account_file = None


class PopulateBuildmasterConfigTest(unittest.TestCase):
  def setUp(self):
    super(PopulateBuildmasterConfigTest, self).setUp()
    os.environ['BUILDBOT_TEST_PASSWORD'] = 'hot bananas'

  def tearDown(self):
    super(PopulateBuildmasterConfigTest, self).tearDown()
    os.environ.pop('BUILDBOT_TEST_PASSWORD', None)

  def verify_timeouts(self, builder, expected_builder_timeout=None,
                      expected_no_output_timeout=2400):
    steps = builder['factory'].steps
    self.assertEqual(1, len(steps))
    step_dict = steps[0][1]
    self.assertEqual(step_dict['maxTime'], expected_builder_timeout)
    self.assertEqual(step_dict['timeout'], expected_no_output_timeout)

  def test_waterfall(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_WATERFALL_PYL)
      fp.close()

      c = {}
      master_gen.PopulateBuildmasterConfig(c, fp.name, _FakeMaster)
      c['builders'] = sorted(c['builders'])

      self.assertEqual(len(c['builders']), 5)
      self.assertEqual(c['builders'][0]['name'], 'Test Linux')
      self.verify_timeouts(c['builders'][0])

      self.assertEqual(c['builders'][1]['name'], 'Test Linux Timeouts')
      self.verify_timeouts(c['builders'][1], 7200, 3600)

      self.assertEqual(c['builders'][2]['name'], 'Test Linux Remote Run')
      self.verify_timeouts(c['builders'][2])

      self.assertEqual(c['builders'][4]['name'], 'Test Linux Build Everything')

      self.assertEqual(len(c['change_source']), 2)
      self.assertEqual(len(c['change_source'][1].branches), 2)
      self.assertEqual(len(c['schedulers']), 3)

      self.assertEqual(c['schedulers'][1].name, 'test_all')
      self.assertTrue(isinstance(c['schedulers'][1], AnyBranchScheduler))
    finally:
      os.remove(fp.name)

  def test_tryservers(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_TRYSERVER_PYL)
      fp.close()

      c = {}
      master_gen.PopulateBuildmasterConfig(c, fp.name, _FakeMaster)

      self.assertEqual(len(c['builders']), 1)
      self.assertEqual(c['builders'][0]['name'], 'Test Linux')
      self.assertEqual(set(s.slavename for s in c['slaves']),
                       set(['vm9998-m1', 'vm9999-m1']))

      self.assertEqual(len(c['change_source']), 0)
      self.assertEqual(len(c['schedulers']), 0)
    finally:
      os.remove(fp.name)


# TODO: Remove this code once all of the builders.pyl formats have
# been upgraded to the new nomenclature.

OLD_TRYSERVER_PYL = """\
{
  "master_base_class": "_FakeMasterBase",
  "master_port": 20999,
  "master_port_alt": 40999,
  "slave_port": 30999,
  "buildbucket_bucket": "fake_bucket",
  "service_account_file": "fake_service_account",
  "templates": ["templates"],

  "builders": {
    "Test Linux": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "scheduler": None,
      "slave_pools": ["main"],
      "slavebuilddir": "test"
    }
  },

  "schedulers": {},

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
}
"""

class OldNomenclature(unittest.TestCase):
  def setUp(self):
    super(OldNomenclature, self).setUp()
    os.environ['BUILDBOT_TEST_PASSWORD'] = 'hot bananas'

  def tearDown(self):
    super(OldNomenclature, self).tearDown()
    os.environ.pop('BUILDBOT_TEST_PASSWORD', None)

  def test_old_nomenclature(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(OLD_TRYSERVER_PYL)
      fp.close()

      c = {}
      master_gen.PopulateBuildmasterConfig(c, fp.name, _FakeMaster)

      self.assertEqual(len(c['builders']), 1)
      self.assertEqual(c['builders'][0]['name'], 'Test Linux')

      self.assertEqual(len(c['change_source']), 0)
      self.assertEqual(len(c['schedulers']), 0)
    finally:
      os.remove(fp.name)


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()
