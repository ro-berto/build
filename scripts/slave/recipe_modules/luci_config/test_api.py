# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import json

from recipe_engine import recipe_test_api


class LuciConfigTestApi(recipe_test_api.RecipeTestApi):
  def get_project_config(
      self, project, config, content,
      path='',
      revision='80abb4d6f37e89ba0786c5bca9c599565693fe12'):
    return self.m.url.json(
        'Get project %r config %r' % (project, config),
        {
          'content': base64.b64encode(content),
          'content_hash': 'v1:814564d6e6507ad7de56de8c76548a31633ce3e4',
          'revision': revision,
          'kind': 'config#resourcesItem',
          'url': 'https://chromium.googlesource.com/%s/+/%s/%s%s' % (
            project, revision, path, config),
          # NOTE: Invalid etag, truncated for line length.
          'etag': '"-S_IMdk0_sAeij2f-EAhBG43QvQ/JlXgwF3XIs6IVH1"',
        })

  def get_projects(self, projects):
    return self.m.url.json('Get luci-config projects', {
            'projects': [{
               'repo_type': 'GITILES',
               'id': repo_id,
               'repo_url': 'https://repo.repo/%s' % repo_id,
            } for repo_id in projects ]})
