# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetSteps(api):
  # TODO(iannucci): Pass the build repo info directly via properties
  repo_name = api.properties.get('repo_name')

  def git_steps(step_history, _failure):
    spec = step_history['gclient setup'].json_data['CheckoutSpec']
    if spec['solutions'][0]['url'].endswith('.git'):
      seed_steps = ['git config user.email', 'git config user.name',
                    'git clean']
      yield api.git('config', 'user.email', 'commit-bot@chromium.org',
                      seed_steps=seed_steps)
      yield api.git('config', 'user.name', 'The Commit Bot')
      yield api.git('clean', '-xfq')

  root = api.properties.get('root', '')
  # FIXME: Rietveld passes the blink path as src/third_party/WebKit
  #        so we have to strip the src bit off before passing to
  #        api.checkout_path. :(
  if root.startswith('src'):
    root = root[3:].lstrip('/')

  # FIXME: Remove the blink_bare repository type.
  if repo_name == 'blink_bare':
    root = ''

  return (
    api.gclient_checkout(repo_name),
    git_steps,
    api.apply_issue(root),
    api.step('presubmit', [
      api.depot_tools_path('presubmit_support.py'),
      '--root', api.checkout_path(root),
      '--commit',
      '--verbose', '--verbose',
      '--issue', api.properties['issue'],
      '--patchset', api.properties['patchset'],
      '--skip_canned', 'CheckRietveldTryJobExecution',
      '--skip_canned', 'CheckTreeIsOpen',
      '--skip_canned', 'CheckBuildbotPendingBuilds',
      '--rietveld_url', api.properties['rietveld'],
      '--rietveld_email', '',  # activates anonymous mode
      '--rietveld_fetch'])
  )
