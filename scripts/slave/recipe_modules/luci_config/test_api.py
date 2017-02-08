# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import json

from recipe_engine import recipe_test_api


class LuciConfigTestApi(recipe_test_api.RecipeTestApi):
  def get_project_config(self, project, config, content):
    return self.step_data(
        "Get project %r config %r" % (project, config),
        self.m.raw_io.output_text(
            json.dumps({
              "content": base64.b64encode(content),
              "content_hash": "v1:814564d6e6507ad7de56de8c76548a31633ce3e4",
              "revision": "80abb4d6f37e89ba0786c5bca9c599565693fe12",
              "kind": "config#resourcesItem",
              # NOTE: Invalid etag, truncated for line length.
              "etag": "\"-S_IMdk0_sAeij2f-EAhBG43QvQ/JlXgwF3XIs6IVH1\""
            })))

  def get_projects(self, projects):
    return self.step_data('Get luci-config projects', self.m.raw_io.output_text(
        json.dumps({
            'projects': [{
               'repo_type': 'GITILES',
               'id': repo_id,
               'repo_url': 'https://repo.repo/%s' % repo_id,
            } for repo_id in projects ]})))
