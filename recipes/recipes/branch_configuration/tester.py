# Copyright 20201 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests a change for branch-conditional LUCI services starlark.

The starlark config for the chromium and chrome LUCI projects contains
branch-conditional logic to enable regenerating the configuration files
for release branches by only changing a JSON settings file.
Unfortunately, unless extreme care is taken, it's possible to make a
change on trunk that has no problems but that causes an error when
executed with the settings modified for a branch.

This recipe provides the means to ensure that the configuration can be
generated with the settings modified, so that unexpected errors
shouldn't occur when generating the branch config on branch day. It
provides no guarantees about the effect of the generated configuration
files, only that they can be generated.
"""

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
]


def RunSteps(api):
  gclient_config = api.gclient.make_config()
  s = gclient_config.solutions.add()
  s.url = api.tryserver.gerrit_change_repo_url
  s.name = s.url.rsplit('/', 1)[-1]
  # We don't care about any repos except for the one that we've got a gerrit
  # change for
  s.deps_file = ''
  gclient_config.got_revision_mapping[s.name] = 'got_revision'

  with api.context(cwd=api.path['cache'].join('builder')):
    update_result = api.bot_update.ensure_checkout(
        patch=True, gclient_config=gclient_config)

  repo_path = api.path['cache'].join('builder',
                                     update_result.json.output['root'])

  # TODO(gbeaty) Actually do stuff with the checkout, for now I just want a
  # recipe that I can set up a builder with
  del repo_path


def GenTests(api):
  yield api.test(
      'basic',
      api.buildbucket.try_build(),
  )
