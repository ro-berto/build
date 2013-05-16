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

  root = build_properties.get('root', '')
  # FIXME: Rietveld passes the blink path as src/third_party/WebKit
  #        so we have to strip the src bit off before passing to
  #        api.checkout_path. :(
  if root.startswith('src'):
    root = root[3:].lstrip('/')

  # FIXME: Remove the blink_bare repository type.
  if repo_name == 'blink_bare':
    root = ''

  return {
    'checkout': 'gclient',
    'gclient_spec': spec,
    'steps': git_steps + [
      steps.apply_issue_step(root),
      steps.step('presubmit', [
        api.depot_tools_path('presubmit_support.py'),
        '--root', api.checkout_path(root),
        '--commit',
        '--verbose', '--verbose',
        '--issue', build_properties['issue'],
        '--patchset', build_properties['patchset'],
        '--skip_canned', 'CheckRietveldTryJobExecution',
        '--skip_canned', 'CheckTreeIsOpen',
        '--skip_canned', 'CheckBuildbotPendingBuilds',
        '--rietveld_url', build_properties['rietveld'],
        '--rietveld_email', '',  # activates anonymous mode
        '--rietveld_fetch'])
    ]
  }
