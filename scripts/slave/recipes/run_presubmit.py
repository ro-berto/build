# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from slave import recipe_util

def GetFactoryProperties(build_properties):
  bp = build_properties
  git_steps = []
  if bp['root_repo_url'].endswith('.git'):
    email = 'commit-bot@chromium.org'
    git_steps = [
      recipe_util.git_step(bp, ['config', 'user.email', email]),
      recipe_util.git_step(bp, ['config', 'user.name', 'The Commit Bot']),
      recipe_util.git_step(bp, ['clean', '-xfq']),
    ]

  return {
    'checkout': 'gclient',
    'gclient_spec': recipe_util.gclient_spec(bp),
    'steps': git_steps + [
      recipe_util.apply_patch_step(bp),
      recipe_util.step('presubmit', [
        recipe_util.depot_tools_path('presubmit_support.py'),
        '--root', recipe_util.checkout(bp),
        '--commit',
        '--author', bp['blamelist'][0],
        '--description', bp['description'],
        '--issue', bp['issue'],
        '--patchset', bp['patchset'],
        '--skip_canned', 'CheckRietveldTryJobExecution',
        '--skip_canned', 'CheckTreeIsOpen',
        '--skip_canned', 'CheckBuildbotPendingBuilds',
        '--skip_canned', 'CheckOwners',
        '--rietveld_url', bp['rietveld']],
        add_properties=False)
    ]
  }
