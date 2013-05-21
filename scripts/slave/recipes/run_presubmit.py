# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetSteps(api, factory_properties, build_properties):
  # TODO(iannucci): Pass the build repo info directly via build_properties
  repo_name = factory_properties.get('repo_name')
  steps = api.Steps(build_properties)

  def git_steps(step_history, _failure):
    spec = step_history['gclient setup'].json_data['CheckoutSpec']
    if spec['solutions'][0]['url'].endswith('.git'):
      seed_steps = ['git config user.email', 'git config user.name',
                    'git clean']
      yield steps.git('config', 'user.email', 'commit-bot@chromium.org',
                      seed_steps=seed_steps)
      yield steps.git('config', 'user.name', 'The Commit Bot')
      yield steps.git('clean', '-xfq')

  root = build_properties.get('root', '')
  # FIXME: Rietveld passes the blink path as src/third_party/WebKit
  #        so we have to strip the src bit off before passing to
  #        api.checkout_path. :(
  if root.startswith('src'):
    root = root[3:].lstrip('/')

  # FIXME: Remove the blink_bare repository type.
  if repo_name == 'blink_bare':
    root = ''

  return (
    steps.gclient_checkout(repo_name),
    git_steps,
    steps.apply_issue(root),
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
  )
