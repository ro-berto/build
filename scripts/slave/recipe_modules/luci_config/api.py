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

  def _fetch(self, url, **kwargs):
    """Wraps url fetch.

    By default retries requests because app engine flakiness yay."""
    kwargs.setdefault('attempts', 3)
    return self.m.url.fetch(url, **kwargs)

  def get_projects(self):
    """Fetch the mapping of project id to url from luci-config.

    Returns:
      A dictionary mapping project id to its luci-config project spec (among
      which there is a repo_url key).
    """
    url = self.c.base_url + '_ah/api/config/v1/projects'
    fetch_result = self._fetch(
        url, step_name='Get luci-config projects',
        headers=self._get_headers()
      )

    mapping = {}
    for project in json.loads(fetch_result)['projects']:
      # Unicode and str-s don't mix well
      mapping[str(project['id'])] = {str(k): str(v) for k, v in project.items()}
    return mapping

  def get_project_config(self, project, config):
    """Fetch the project config from luci-config.

    Args:
      project: The name of the project in luci-config.
      config: The config to fetch from refs/heads/master of the project.

    Returns:
      The json returned from luci-config.
    """
    url = self.c.base_url + '/_ah/api/config/v1/config_sets/'
    url += self.m.url.quote('projects/%s/refs/heads/master' % project, safe='')
    url += '/config/%s' % config

    fetch_result = self._fetch(
        url, step_name='Get project %r config %r' % (project, config),
        headers=self._get_headers())
    result = json.loads(fetch_result)
    result['content'] = base64.b64decode(result['content'])
    return result

  def parse_textproto(self, lines):
    """(badly) parses a text protobuf.

    This is not real protobuf parsing at the moment; eventually, maybe it could
    be. For now, it's enough to just get by.

    We assume all fields are repeated since we don't have a proto spec to work
    with.

    Args:
      lines: a list of the lines to parse
    Returns:
      A recursive dictionary of lists.
    """
    def parse_atom(text):
      # NOTE: Assuming we only have numbers and strings to avoid using
      # ast.literal_eval
      try:
        return int(text)
      except ValueError:
        return text.strip("'").strip('"')

    ret = {}
    while lines:
      line = lines.pop(0).strip()

      m = re.match(r'(\w+)\s*:\s*(.*)', line)
      if m:
        ret.setdefault(m.group(1), []).append(parse_atom(m.group(2)))
        continue

      m = re.match(r'(\w+)\s*{', line)
      if m:
        subparse = self.parse_textproto(lines)
        ret.setdefault(m.group(1), []).append(subparse)
        continue

      if line == '}':
        return ret
      if line == '':
        continue

      raise ValueError(
          'Could not understand line: <%s>' % line) # pragma: no cover
    return ret

  def get_project_metadata(self, project):
    mapping = self.get_projects()
    return mapping.get(project)

