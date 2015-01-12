# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urlparse

from slave import recipe_api

class RietveldApi(recipe_api.RecipeApi):
  def calculate_issue_root(self):
    """Returns path where a patch should be applied to based on "patch_project".

    Maps Rietveld's "patch_project" to a path of directories relative to
    api.gclient.c.solutions[0].name which describe where to place the patch.

    Returns:
      Relative path or empty string if patch_project is not set or path for a
      given is unknown.
    """
    patch_project = self.m.properties.get('patch_project')
    patch_project_roots = {
      'blink': ['third_party', 'WebKit'],
    }

    path_parts = patch_project_roots.get(patch_project)
    if path_parts:
      patch_root = self.m.path.join(*path_parts)
    else:
      patch_root = self.m.properties.get('root') or ''
      if patch_root.startswith('src'):
        patch_root = patch_root[3:].lstrip('/')

    return patch_root

  def apply_issue(self, *root_pieces, **kwargs):
    """Call apply_issue from depot_tools.

    Args:
      root_pieces (strings): location where to run apply_issue, relative to the
        checkout root.
      authentication (string or None): authentication scheme to use. Can be None
        or 'oauth2'. See also apply_issue.py --help (-E and --no-auth options.)
    """
    # TODO(pgervais): replace *root_pieces by a single Path object.
    authentication = kwargs.get('authentication', None)
    rietveld_url = self.m.properties['rietveld']
    issue_number = self.m.properties['issue']

    if authentication == 'oauth2':
      step_result = self.m.python(
        'apply_issue',
        self.m.path['depot_tools'].join('apply_issue.py'), [
          '-r', self.m.path['checkout'].join(*root_pieces),
          '-i', issue_number,
          '-p', self.m.properties['patchset'],
          '-s', rietveld_url,
          '-E', self.m.path['build'].join('site_config',
                                          '.rietveld_client_email'),
          '-k', self.m.path['build'].join('site_config',
                                          '.rietveld_secret_key')
          ],
        )

    else:
      step_result = self.m.python(
        'apply_issue',
        self.m.path['depot_tools'].join('apply_issue.py'), [
          '-r', self.m.path['checkout'].join(*root_pieces),
          '-i', issue_number,
          '-p', self.m.properties['patchset'],
          '-s', rietveld_url,
          '--no-auth'],
        )
    step_result.presentation.links['Applied issue %s' % issue_number] = (
      urlparse.urljoin(rietveld_url, str(issue_number)))

