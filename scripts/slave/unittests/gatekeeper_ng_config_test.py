#!/usr/bin/env vpython
# coding=utf-8
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for gatekeeper_ng_config.py.

"""

import json
import os
import tempfile
import unittest

import test_env  # pylint: disable=relative-import

from slave import gatekeeper_ng_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# TODO(stip, martiniss): convert rest of old config tests to this style

class GatekeeperTest(unittest.TestCase):
  def setUp(self):
    _, self.fname = tempfile.mkstemp("gc.json")

    self.cfg = {}

  def load_config(self):
    with open(self.fname, 'w') as cfg_file:
      cfg_file.write(json.dumps(self.cfg))

    return gatekeeper_ng_config.load_gatekeeper_config(self.fname)

  def add_master_config(self, master, cfg):
    self.cfg['masters'] = self.cfg.get('masters', {})

    self.assertNotIn(master, self.cfg['masters'])
    self.cfg['masters'][master] = [cfg]

  def add_builder_config(self, master, builder, cfg):
    self.add_master_config(master, {'builders': {builder: cfg}})

  def add_category(self, name, contents):
    self.cfg['categories'] = self.cfg.get('categories', {})

    self.assertNotIn(name, self.cfg['categories'])
    self.cfg['categories'][name] = contents

  def testInheritCategoryFromMasterWithBuilderForgive(self):
    self.add_master_config(
        "http://example.com/test_master",
        {
          "categories": ["test"],
          "builders": {
              "*": { "categories": [ "other_test" ] }
          }
        },
    )

    self.add_category(
        "test",
        {
            "closing_optional": [
                "bot_update",
                "update",
            ],
        },
    )

    self.add_category(
        "other_test",
        {
            "forgiving_optional": [
                "bot_update",
                "package build",
            ],
        },
    )

    config = self.load_config()

    cfg = config['http://example.com/test_master'][0]['*']
    fo, co = cfg['forgiving_optional'], cfg['closing_optional']
    self.assertEqual(fo, set(['bot_update', 'package build']))
    self.assertEqual(co, set(['update']))

  def testConflictingMultipleBuilderEntries(self):
    self.add_builder_config(
        "http://example.com/master",
        "builder1",
        {
            "categories": ['test1', 'test2'],
        })

    self.add_category(
        "test1",
        {
            "closing_optional": [
                "bot_update",
            ],
        },
    )

    self.add_category(
        "test2",
        {
            "forgiving_optional": [
                "bot_update",
            ],
        },
    )

    with self.assertRaises(ValueError):
      self.load_config()


if __name__ == '__main__':
  unittest.main()
