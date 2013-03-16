# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_util

def GetFactoryProperties(build_properties):
  steps = recipe_util.Steps(build_properties)

  git_steps = []
  if build_properties['root_repo_url'].endswith('.git'):
    email = 'commit-bot@chromium.org'
    git_steps = [
      steps.git_step('config', 'user.email', email),
      steps.git_step('config', 'user.name', 'The Commit Bot'),
      steps.git_step('clean', '-xfq'),
    ]

  return {
    'checkout': 'gclient',
    'gclient_spec': steps.gclient_spec(),
    'steps': git_steps + [
      steps.apply_patch_step(),
      steps.step('presubmit', [
        steps.depot_tools_path('presubmit_support.py'),
        '--root', steps.checkout_path(),
        '--commit',
        '--author', build_properties['blamelist'][0],
        '--description', build_properties['description'],
        '--issue', build_properties['issue'],
        '--patchset', build_properties['patchset'],
        '--skip_canned', 'CheckRietveldTryJobExecution',
        '--skip_canned', 'CheckTreeIsOpen',
        '--skip_canned', 'CheckBuildbotPendingBuilds',
        '--skip_canned', 'CheckOwners',
        '--rietveld_url', build_properties['rietveld']])
    ]
  }
