# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os

from recipe_engine import recipe_test_api

# Path to the production trees file. We need to use system os.path to make this
# available as test data whereever the simulation is run.
PROD_TREES_FILE = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'gatekeeper_trees.json'))

class GatekeeperTestApi(recipe_test_api.RecipeTestApi):
  def fake_test_data(self, data=None):
    if not data:
      data = self.fake_test_json()

    return self.m.json.output(data)

  def fake_test_json(self):
    return {
      'blink': {
        'build-db': 'blink_build_db.json',
        'masters': {
          'https://build.chromium.org/p/chromium.webkit': ["*"],
        },
        'filter-domain': 'google.com',
        'open-tree': True,
        'password-file': '.blink_status_password',
        'revision-properties': 'got_revision',
        'set-status': True,
        'sheriff-url': 'https://build.chromium.org/p/chromium/%s.js',
        'status-url': 'https://blink-status.appspot.com',
        'status-user': 'gatekeeper@google.com',
        'track-revisions': True,
        'use-project-email-address': True,
      },
      'chromium': {},
    }

  def infra_config_data(self):
    return self.m.json.output({
      'foobar': {
        'config': 'foobar/tree_closers.json',
      },
    })

  def gitiles_config_data(self):
    return self.m.json.output({
      'foobar': {
        'gitiles-config': {
          'repo_url': 'https://chromium.googlesource.com/foo/bar',
          'ref': 'refs/heads/baz',
          'path': 'biz/buz.json',
        },
      },
    })

  def production_data(self):
    with open(PROD_TREES_FILE) as f:
      return self.m.json.output(json.load(f))
