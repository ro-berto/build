# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class Gatekeeper(recipe_api.RecipeApi):
  """Module for Gatekeeper NG."""
  def __call__(self, gatekeeper_json, gatekeeper_trees_json):
    config = self.m.json.read(
      'reading %s' % self.m.path.basename(gatekeeper_trees_json),
      gatekeeper_trees_json,
      step_test_data=self.test_api.test_data,
    ).json.output

    args = ['-v', '--json', gatekeeper_json]

    for tree_name, tree_args in config.iteritems():
      if tree_args.get('status-url'):
        args.extend(['--status-url', tree_args['status-url']])
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
      if tree_args.get('filter-domain'):
        args.extend(['--filter-domain', tree_args['filter-domain']])
      if tree_args.get('status-user'):
        args.extend(['--status-user', tree_args['status-user']])

      if tree_args.get('masters'):
        args.extend(tree_args['masters'])

      self.m.python(
        'gatekeeper: %s' % str(tree_name),
        self.m.path['build'].join('scripts', 'slave', 'gatekeeper_ng.py'),
        args,
      )
