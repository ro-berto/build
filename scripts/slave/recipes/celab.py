# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/python',
  'recipe_engine/time',
]

from recipe_engine.recipe_api import Property

CELAB_REPO = "https://chromium.googlesource.com/enterprise/cel"


def _get_bin_directory(api, checkout):
  bin_dir = checkout.join('out')
  if api.platform.is_linux:
    bin_dir = bin_dir.join('linux_amd64', 'bin')
  elif api.platform.is_win:
    bin_dir = bin_dir.join('windows_amd64', 'bin')
  return bin_dir


def RunSteps(api):
  # Checkout the CELab repo
  go_root = api.path['start_dir'].join('go')
  src_root = go_root.join('src', "chromium.googlesource.com", "enterprise")
  api.file.ensure_directory('init src_root if not exists', src_root)

  with api.context(cwd=src_root):
    api.gclient.set_config('celab')
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()
  checkout = api.path['checkout']

  # Install Go & Protoc
  bootstrap_script = checkout.join('infra', 'bootstrap.py')
  bootstrap_root = api.path['start_dir'].join("bootstrap")
  api.python('celab bootstrap', bootstrap_script, [bootstrap_root])
  add_paths = [
    go_root.join('bin'),
    bootstrap_root.join('golang', 'go', 'bin'),
    bootstrap_root.join('protoc', 'bin'),
  ]

  # Build CELab
  goenv = {"GOPATH": go_root}
  with api.context(cwd=checkout, env=goenv, env_suffixes={'PATH': add_paths}):
    api.python('install deps', 'build.py', ['deps', '--install', '--verbose'])
    api.python('build', 'build.py', ['build', '--verbose'])

  # Upload binaries for CI builds
  if api.buildbucket.build.builder.bucket == 'ci':
    today = api.time.utcnow().date()
    gs_dest = '%s/%s/%s' % (
      api.buildbucket.builder_name,
      today.strftime('%Y/%m/%d'),
      api.buildbucket.build.id)
    api.gsutil.upload(
      source=_get_bin_directory(api, checkout).join('**'),
      bucket='celab',
      dest=gs_dest,
      name='upload CELab binaries',
      link_name='CELab binaries')


def GenTests(api):
  yield (
      api.test('basic_try') +
      api.buildbucket.try_build(project='celab', bucket='try', git_repo=CELAB_REPO)
  )
  yield (
      api.test('basic_ci_linux') +
      api.platform('linux', 64) +
      api.buildbucket.ci_build(project='celab', bucket='ci', git_repo=CELAB_REPO)
  )
  yield (
      api.test('basic_ci_windows') +
      api.platform('win', 64) +
      api.buildbucket.ci_build(project='celab', bucket='ci', git_repo=CELAB_REPO)
  )
