# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Test whether a fresh checkout ('fetch dart') works.

DEPS = [
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'recipe_engine/buildbucket',
  'recipe_engine/properties',
]


def RunSteps(api):
  repo_url = api.tryserver.gerrit_change_repo_url
  fetch_ref = api.tryserver.gerrit_change_fetch_ref
  target_ref = api.tryserver.gerrit_change_target_ref
  extra_sync_flags = []
  if repo_url and fetch_ref and target_ref:
    # Apply the patch on the target branch if it's a CL.
    extra_sync_flags.extend(
        ['--patch-ref', '%s@%s:%s' % (repo_url, target_ref, fetch_ref)])
  else:
    # Check out the commit if it's not a CL.
    revision = api.buildbucket.gitiles_commit.id
    extra_sync_flags.extend(["--revision", revision])
  # The cache directory is intentionally omitted so this recipe properly
  # simulates a completely fresh checkout. A cache directory might make things
  # work when they're actually broken.
  api.gclient.set_config('dart', CACHE_DIR=None)
  api.gclient.checkout(extra_sync_flags=extra_sync_flags)


def GenTests(api):
  yield (api.test('ci'))
  yield (api.test('try') + api.properties.tryserver())
