# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe for Skia Infra.


DEPS = [
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


INFRA_GO = 'skia.googlesource.com/buildbot.git'
INFRA_GIT_URL = 'https://skia.googlesource.com/buildbot'


def git(api, *cmd, **kwargs):
  git_cmd = 'git.bat' if api.platform.is_win else 'git'
  api.step(
      'git %s' % cmd[0],
      cmd=[git_cmd] + list(cmd),
      **kwargs)


def git_checkout(api, url, dest, ref=None):
  """Create a git checkout of the given repo in dest."""
  if api.path.exists(dest.join('.git')):
    # Already have a git checkout. Ensure that the correct remote is set.
    git(api, 'remote', 'set-url', 'origin', INFRA_GIT_URL, cwd=dest)
  else:
    # Clone the repo
    git(api, 'clone', INFRA_GIT_URL, dest)

  # Ensure that the correct ref is checked out.
  git(api, 'fetch', 'origin', cwd=dest)
  git(api, 'clean', '-d', '-f', cwd=dest)
  git(api, 'reset', '--hard', ref or 'origin/master', cwd=dest)


def GenSteps(api):
  go_dir = api.path['slave_build'].join('go')
  go_src = go_dir.join('src')
  api.path.makedirs('makedirs go/src', go_src)
  infra_dir = go_src.join(INFRA_GO)

  # Check out the infra repo.
  git_checkout(
      api,
      INFRA_GIT_URL,
      dest=infra_dir,
      ref=api.properties.get('revision', 'origin/master'))
  # TODO(borenet): Apply patch for trybots!
  # Fetch Go dependencies.
  env = {'GOPATH': go_dir}
  api.step('Update', cmd=['go', 'get', './...'], cwd=infra_dir, env=env)

  # Run tests.
  api.python('run_unittests', 'run_unittests', cwd=infra_dir, env=env)


def GenTests(api):
  yield (
      api.test('Infra-PerCommit') +
      api.path.exists(api.path['slave_build'].join('go', 'src', INFRA_GO,
                                                   '.git'))
  )
  yield (
      api.test('Infra-PerCommit_initialcheckout')
  )
