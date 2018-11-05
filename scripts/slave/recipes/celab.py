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
  'recipe_engine/python',
  'recipe_engine/time',
]

from recipe_engine.recipe_api import Property

CELAB_REPO = "https://chromium.googlesource.com/enterprise/cel"


def RunSteps(api):
  # 1. Checkout the CELab repo
  goroot = api.path['start_dir'].join('go')
  srcroot = goroot.join('src', "chromium.googlesource.com", "enterprise")
  api.file.ensure_directory('init srcroot if not exists', srcroot)

  with api.context(cwd=srcroot):
    api.gclient.set_config('celab')
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()

  # 2. Build CELab
  checkout = api.path['checkout']
  goenv = {'GOPATH': goroot}

  with api.context(cwd=checkout, env=goenv):
    api.python('install deps', 'build.py', ['deps', '--install', '--verbose'])
    api.python('build', 'build.py', ['build', '--verbose'])

  # 3. Upload binaries for CI builds
  if api.buildbucket.build.builder.bucket == 'ci':
    today = api.time.utcnow().date()
    gs_dest = '%s/%s/%s' % (
      api.buildbucket.builder_name,
      today.strftime('%Y/%m/%d'),
      api.buildbucket.build.number)
    api.gsutil.upload(
      source=checkout.join("out", 'linux_amd64', 'bin', '**'),
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
      api.test('basic_ci') +
      api.buildbucket.ci_build(project='celab', bucket='ci', git_repo=CELAB_REPO)
  )
