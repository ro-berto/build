# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

import base64
import collections
import re
import json

class LuciConfigApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(LuciConfigApi, self).__init__(**kwargs)
    self.set_config('basic')

  def get_config_defaults(self):
    return {
      'BASE_URL': 'https://luci-config.appspot.com/',
    }

  def _get_headers(self):
    if not self.c.auth_token:
      return {}

    return {
      'Authorization': 'Bearer %s' % self.c.auth_token
    }

  def get_projects(self):
    """Fetch the mapping of project id to url from luci-config.

    Returns:
      A dictionary mapping project id to its luci-config project spec (among
      which there is a repo_url key).
    """
    url = self.c.base_url + '_ah/api/config/v1/projects'
    reuslt = self.m.url.get_json(url, step_name='Get luci-config projects',
        headers=self._get_headers()).output

    mapping = {}
    for project in reuslt['projects']:
      # Unicode and str-s don't mix well
      mapping[str(project['id'])] = {str(k): str(v) for k, v in project.items()}
    return mapping

  # TODO(tandrii): remove this after usages are removed downstream.
  def get_project_config(self, project, config):
    """Do not use. Use get_ref_config instead."""
    return self.get_ref_config(project, 'refs/heads/master', config)

  def get_ref_config(self, project, ref, config):
    """Fetch the ref config from luci-config.

    Args:
      project: The name of the project in luci-config.
      ref: git ref, e.g., 'refs/heads/master'
      config: The config to fetch from refs/heads/master of the project.

    Returns:
      The json returned from luci-config with 'content' field already base64
      decoded.
    """
    url = self.c.base_url + '/_ah/api/config/v1/config_sets/'
    url += self.m.url.quote('projects/%s/%s' % (project, ref), safe='')
    url += '/config/%s' % config

    result = self.m.url.get_json(
        url,
        step_name='Get project %r %r config %r' % (project, ref, config),
        headers=self._get_headers()).output
    result['content'] = base64.b64decode(result['content'])
    return result

  def get_project_metadata(self, project):
    mapping = self.get_projects()
    return mapping.get(project)
