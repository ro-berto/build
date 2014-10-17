# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'git',
  'gsutil',
  'json',
  'path',
  'properties',
  'step',
]

def GenSteps(api):
  api.chromium.cleanup_temp()
  api.gclient.set_config('chromium')
  api.gclient.apply_config('v8')
  api.bot_update.ensure_checkout(
      force=True, no_shallow=True, with_branch_heads=True)

  # TODO(machenbach): Remove svn config after the git switch.
  api.git(
      'svn', 'init', 'https://v8.googlecode.com/svn',
      name='git svn init',
      cwd=api.path['slave_build'].join('v8'))
  api.git(
      'config', '--unset-all', 'svn-remote.svn.fetch',
      name='git config unset-all',
      cwd=api.path['slave_build'].join('v8'))
  api.git(
      'config', '--add', 'svn-remote.svn.fetch',
      'branches/bleeding_edge:refs/remotes/origin/master',
      name='git config add master',
      cwd=api.path['slave_build'].join('v8'))
  api.git(
      'config', '--add', 'svn-remote.svn.fetch',
      'trunk:refs/remotes/origin/candidates',
      name='git config add candidates',
      cwd=api.path['slave_build'].join('v8'))
  api.git(
      'config', '--add', 'svn-remote.svn.fetch',
      'branches/3.28:refs/remotes/branch-heads/3.28',
      name='git config add 3.28',
      cwd=api.path['slave_build'].join('v8'))
  api.git(
      'config', '--add', 'svn-remote.svn.fetch',
      'branches/3.29:refs/remotes/branch-heads/3.29',
      name='git config add 3.29',
      cwd=api.path['slave_build'].join('v8'))

  api.step(
      'V8Releases',
      [api.path['slave_build'].join(
           'v8', 'tools', 'push-to-trunk', 'releases.py'),
       '-c', api.path['checkout'],
       '--json', api.path['slave_build'].join('v8-releases-update.json'),
       '--branch', 'recent',
       '--vc-interface', 'git_read_svn_write'],
      cwd=api.path['slave_build'].join('v8'),
    )
  api.gsutil.upload(api.path['slave_build'].join('v8-releases-update.json'),
                    'chromium-v8-auto-roll',
                    api.path.join('v8rel', 'v8-releases-update.json'))


def GenTests(api):
  yield api.test('standard') + api.properties.generic(mastername='client.v8')