# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from slave import recipe_test_api


class GatekeeperTestApi(recipe_test_api.RecipeTestApi):
  def fake_test_data(self):
    return self.m.json.output({
      'blink': {
        'build-db': 'blink_build_db.json',
        'masters': [
          'https://build.chromium.org/p/chromium.webkit',
        ],
        'filter-domain': 'google.com',
        'open-tree': True,
        'password-file': '.blink_status_password',
        'revision-properties': 'got_revision,got_webkit_revision',
        'set-status': True,
        'sheriff-url': 'https://build.chromium.org/p/chromium/%s.js',
        'status-url': 'https://blink-status.appspot.com',
        'status-user': 'gatekeeper@google.com',
        'track-revisions': True,
        'use-project-email-address': True,
      },
      'chromium': {},
    })

  def read_real_config(self, f):
    return self.m.json.output(json.loads(self.m.file.read_in_build(f)))

  def read_real_internal_config(self, f): # pragma nocover
    return self.m.json.output(json.loads(self.m.file.read_in_build_internal(f)))
