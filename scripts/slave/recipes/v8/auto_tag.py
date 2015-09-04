# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
  'bot_update',
  'gclient',
  'git',
  'path',
  'properties',
  'python',
  'raw_io',
  'step',
  'v8',
]

REPO = 'https://chromium.googlesource.com/v8/v8'
BRANCH_RE = re.compile(r'^\d+\.\d+$')


def GetCommitForRef(api, repo, ref):
  step_result = api.git(
      'ls-remote', repo, ref,
      # For strange reasons, this string is not a string in production without
      # str().
      name=str('git ls-remote %s' % ref.split('/')[-1]),
      cwd=api.path['checkout'],
      stdout=api.raw_io.output(),
  )
  result = step_result.stdout.strip()
  if result:
    # Extract hash if available. Otherwise keep empty string.
    result = result.split()[0]
  step_result.presentation.logs['ref'] = [result]
  return result


def PushRef(api, repo, ref, hsh):
  api.git(
      'push', repo, '+%s:%s' % (hsh, ref),
      cwd=api.path['checkout'],
  )


def LogStep(api, text):
  api.step('log', ['echo', text])


def RunSteps(api):
  # Ensure a proper branch is specified.
  branch = api.properties.get('branch')
  if not branch or not BRANCH_RE.match(branch):
    raise api.step.InfraFailure('A release branch must be specified.')
  repo = api.properties.get('repo', REPO)

  api.gclient.set_config('v8')
  api.bot_update.ensure_checkout(
      force=True, no_shallow=True, with_branch_heads=True)

  branch_ref = 'refs/branch-heads/%s' % branch
  lkgr_ref = 'refs/heads/%s-lkgr' % branch

  # Get current lkgr ref and update to HEAD.
  new_lkgr = GetCommitForRef(api, repo, branch_ref)
  current_lkgr = GetCommitForRef(api, repo, lkgr_ref)
  # If the lkgr_ref doesn't exist, it's an empty string. In this case the push
  # ref command will create it.
  if new_lkgr != current_lkgr:
    PushRef(api, repo, lkgr_ref, new_lkgr)
  else:
    LogStep(api, 'There is no new lkgr.')


def GenTests(api):
  hsh_old = '74882b7a8e55268d1658f83efefa1c2585cee723'
  hsh_new = 'c1a7fd0c98a80c52fcf6763850d2ee1c41cfe8d6'

  def Test(name, current_lkgr, new_lkgr):
    return (
        api.test(name) +
        api.properties.generic(mastername='client.v8.fyi',
                               buildername='Auto-tag',
                               branch='3.4') +
        api.override_step_data(
            'git ls-remote 3.4',
            api.raw_io.stream_output(new_lkgr, stream='stdout'),
        ) +
        api.override_step_data(
            'git ls-remote 3.4-lkgr',
            api.raw_io.stream_output(current_lkgr, stream='stdout'),
        )
    )

  yield Test(
      'same_lkgr',
      hsh_old + '\trefs/heads/3.4-lkgr',
      hsh_old + '\trefs/branch-heads/3.4',
  )
  yield Test(
      'update',
      hsh_old + '\trefs/heads/3.4-lkgr',
      hsh_new + '\trefs/branch-heads/3.4',
  )
  yield Test(
      'missing',
      '',
      hsh_new + '\trefs/branch-heads/3.4',
  )
  yield (
      api.test('missing_branch') +
      api.properties.generic(mastername='client.v8.fyi',
                             buildername='Auto-tag')
  )
