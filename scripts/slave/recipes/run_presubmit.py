# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetFactoryProperties(api, factory_properties, build_properties):
  # TODO(iannucci): Pass the build repo info directly via build_properties
  repo_name = factory_properties.get('repo_name')
  steps = api.Steps(build_properties)

  spec = steps.gclient_common_spec(repo_name)

  git_steps = []
  if spec['solutions'][0]['url'].endswith('.git'):
    email = 'commit-bot@chromium.org'
    git_steps = [
      steps.git_step('config', 'user.email', email),
      steps.git_step('config', 'user.name', 'The Commit Bot'),
      steps.git_step('clean', '-xfq'),
    ]

  return {
    'checkout': 'gclient',
    'gclient_spec': spec,
    'steps': git_steps + [
      steps.apply_issue_step(),
      steps.step('presubmit', [
        api.depot_tools_path('presubmit_support.py'),
        '--root', api.checkout_path(),
        '--commit',
        '--verbose', '--verbose',
        '--issue', build_properties['issue'],
        '--patchset', build_properties['patchset'],
        '--skip_canned', 'CheckRietveldTryJobExecution',
        '--skip_canned', 'CheckTreeIsOpen',
        '--skip_canned', 'CheckBuildbotPendingBuilds',
        '--skip_canned', 'CheckOwners',
        '--rietveld_url', build_properties['rietveld'],
        '--rietveld_fetch'])
    ]
  }
