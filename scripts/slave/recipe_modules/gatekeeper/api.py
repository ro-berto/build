# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class Gatekeeper(recipe_api.RecipeApi):
  """Module for Gatekeeper NG."""
  def __call__(self, gatekeeper_default_json, gatekeeper_trees_json):
    config = self.m.json.read(
      'reading %s' % self.m.path.basename(gatekeeper_trees_json),
      gatekeeper_trees_json,
    ).json.output

    for tree_name, tree_args in config.iteritems():
      # Use tree-specific config if specified, otherwise use default.
      # Tree-specific configs must be relative to the trees file.
      gatekeeper_json = gatekeeper_default_json
      if tree_args.get('config'):
        assert '..' not in tree_args['config'].split('/')
        gatekeeper_json = self.m.path.join(
            self.m.path.dirname(gatekeeper_trees_json),
            *tree_args['config'].split('/'))

      args = [
          '--json', gatekeeper_json,
          '--service-account-path',
          self.m.puppet_service_account.get_key_path('gatekeeper'),
      ]

      if tree_args.get('status-url'):
        args.extend(['--status-url', tree_args['status-url']])
      if tree_args.get('sheriff-url'):
        args.extend(['--sheriff-url', tree_args['sheriff-url']])
      if tree_args.get('set-status'):
        args.append('--set-status')
      if tree_args.get('open-tree'):
        args.append('--open-tree')
      if tree_args.get('track-revisions'):
        args.append('--track-revisions')
      if tree_args.get('revision-properties'):
        args.extend(['--revision-properties', tree_args['revision-properties']])
      if tree_args.get('build-db'):
        args.extend(['--build-db', tree_args['build-db']])
      if tree_args.get('password-file'):
        args.extend(['--password-file', tree_args['password-file']])
      if tree_args.get('use-project-email-address'):
        args.extend(['--default-from-email',
                     '%s-buildbot@chromium-build.appspotmail.com' % tree_name])
      elif tree_args.get('default-from-email'): # pragma: nocover
        args.extend(['--default-from-email', tree_args['default-from-email']])
      if tree_args.get('filter-domain'):
        args.extend(['--filter-domain', tree_args['filter-domain']])
      if tree_args.get('status-user'):
        args.extend(['--status-user', tree_args['status-user']])

      if tree_args.get('masters'):
        if self.c and self.c.use_new_logic:
          valid_masters = []

          modifies_tree = False
          if tree_args.get('set-status') or tree_args.get('open-tree'):
            modifies_tree = True

          for master, allowed in tree_args['masters'].items():
            if '*' in allowed:
              valid_masters.append(master)
            elif allowed:
              valid_masters.append(master + ':' + ','.join(allowed))
          args.extend(valid_masters)
        else: #pragma: no cover
          args.extend(tree_args['masters'])

      try:
        self.m.build.python(
          'gatekeeper: %s' % str(tree_name),
          self.package_repo_resource('scripts', 'slave', 'gatekeeper_ng.py'),
          args,
        )
      except self.m.step.StepFailure:
        pass
