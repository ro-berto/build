# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe for Skia Infra.


import re


DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/infra_paths',
  'depot_tools/rietveld',
  'file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]


INFRA_GO = 'go.skia.org/infra'
INFRA_GIT_URL = 'https://skia.googlesource.com/buildbot'

REF_HEAD = 'HEAD'
REF_ORIGIN_MASTER = 'origin/master'


def git(api, *cmd, **kwargs):
  git_cmd = 'git.bat' if api.platform.is_win else 'git'
  return api.step(
      'git %s' % cmd[0],
      cmd=[git_cmd] + list(cmd),
      **kwargs)


def git_checkout(api, url, dest, ref=None):
  """Create a git checkout of the given repo in dest."""
  if api.path.exists(dest.join('.git')):
    # Already have a git checkout. Ensure that the correct remote is set.
    with api.step.context({'cwd': dest}):
      git(api, 'remote', 'set-url', 'origin', INFRA_GIT_URL)
  else:
    # Clone the repo
    git(api, 'clone', INFRA_GIT_URL, dest)

  # Ensure that the correct ref is checked out.
  ref = ref or REF_ORIGIN_MASTER
  if ref == REF_HEAD:
    ref = REF_ORIGIN_MASTER
  with api.step.context({'cwd': dest}):
    git(api, 'fetch', 'origin')
    git(api, 'clean', '-d', '-f')
    git(api, 'checkout', 'master')
    git(api, 'reset', '--hard', ref)

  api.path['checkout'] = dest

  # Run bot_update, just to apply patches.
  cfg_kwargs = {'CACHE_DIR': '/b/cache'}
  gclient_cfg = api.gclient.make_config(**cfg_kwargs)
  dirname = api.path['start_dir'].join('go', 'src', 'go.skia.org')
  basename = 'infra'
  sln = gclient_cfg.solutions.add()
  sln.name = basename
  sln.managed = False
  sln.url = INFRA_GIT_URL
  sln.revision = ref
  gclient_cfg.got_revision_mapping[basename] = 'got_revision'
  with api.step.context({'cwd': dirname}):
    api.bot_update.ensure_checkout(gclient_config=gclient_cfg)

  with api.step.context({'cwd': dest}):
    # Fix the remote URL, since bot_update switches it to the cached repo.
    git(api, 'remote', 'set-url', 'origin', INFRA_GIT_URL)

    # Re-checkout master, since bot_update detaches us. We already set master
    # to the correct commit, and any applied patch should not have been committed,
    # so this should be safe.
    git(api, 'checkout', 'master')

    # "git status" just to sanity check.
    git(api, 'status')


def RunSteps(api):
  # The 'build' and 'depot_tools' directories are provided through isolate
  # and aren't in the expected location, so we need to override them.
  api.path.c.base_paths['depot_tools'] = (
      api.path.c.base_paths['start_dir'] +
      ('build', 'scripts', 'slave', '.recipe_deps', 'depot_tools'))
  api.path.c.base_paths['build'] = (
      api.path.c.base_paths['start_dir'] + ('build',))

  go_dir = api.path['start_dir'].join('go')
  go_src = go_dir.join('src')
  api.file.makedirs('makedirs go/src', go_src)
  infra_dir = go_src.join(INFRA_GO)

  # Check out the infra repo.
  git_checkout(
      api,
      INFRA_GIT_URL,
      dest=infra_dir,
      ref=api.properties.get('revision', 'origin/master'))

  # Fetch Go dependencies.
  env = {'CHROME_HEADLESS': '1',
         'GOPATH': go_dir,
         'GIT_USER_AGENT': 'git/1.9.1',  # I don't think this version matters.
         'PATH': api.path.pathsep.join([str(go_dir.join('bin')), '%(PATH)s'])}
  with api.step.context({'cwd': infra_dir}):
    api.step('update_deps', cmd=['go', 'get', '-u', './...'], env=env)

  # Checkout AGAIN to undo whatever `go get -u` did to the infra repo.
  git_checkout(
      api,
      INFRA_GIT_URL,
      dest=infra_dir,
      ref=api.properties.get('revision', 'origin/master'))

  with api.step.context({'cwd': infra_dir}):
    # Set got_revision.
    test_data = lambda: api.raw_io.test_api.stream_output('abc123')
    rev_parse = git(api, 'rev-parse', 'HEAD',
                    stdout=api.raw_io.output_text(),
                    step_test_data=test_data)
    rev_parse.presentation.properties['got_revision'] = rev_parse.stdout.strip()

    # More prerequisites.
    api.step(
        'install goimports',
        cmd=['go', 'get', 'golang.org/x/tools/cmd/goimports'],
        env=env)
    api.step(
        'install errcheck',
        cmd=['go', 'get', 'github.com/kisielk/errcheck'],
        env=env)
  with api.step.context({'cwd': infra_dir.join('go', 'database')}):
    api.step(
        'setup database',
        cmd=['./setup_test_db'],
        env=env)

  # Run tests.
  buildslave = api.properties['slavename']
  m = re.search('^[a-zA-Z-]*(\d+)$', buildslave)
  karma_port = '9876'
  if m and len(m.groups()) > 0:
    karma_port = '15%s' % m.groups()[0]
  env['KARMA_PORT'] = karma_port
  env['DEPOT_TOOLS'] = api.depot_tools.package_repo_resource()
  with api.step.context({'cwd': infra_dir}):
    api.python('run_unittests', 'run_unittests', env=env)


def GenTests(api):
  yield (
      api.test('Infra-PerCommit') +
      api.path.exists(api.path['start_dir'].join('go', 'src', INFRA_GO,
                                                   '.git')) +
      api.properties(slavename='skiabot-linux-infra-001',
                     path_config='kitchen')
  )
  yield (
      api.test('Infra-PerCommit_initialcheckout') +
      api.properties(slavename='skiabot-linux-infra-001',
                     path_config='kitchen')
  )
  yield (
      api.test('Infra-PerCommit_try') +
      api.properties(patch_storage='rietveld',
                     rietveld='https://codereview.chromium.org',
                     issue=1234,
                     patchset=1,
                     revision=REF_HEAD,
                     slavename='skiabot-linux-infra-001',
                     path_config='kitchen')
  )
  yield (
      api.test('Infra-PerCommit_try_gerrit') +
      api.properties(
          patch_storage='gerrit',
          revision=REF_HEAD,
          slavename='skiabot-linux-infra-001',
          path_config='kitchen') +
      api.properties.tryserver(
          gerrit_project='skia',
          gerrit_url='https://skia-review.googlesource.com/',
      )
  )
