# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/cipd',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/python',
  'recipe_engine/time',
  'zip',
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


def _get_ctl_binary_name(api):
  suffix = '.exe' if api.platform.is_win else ''
  return "cel_ctl" + suffix


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
  packages = {}
  packages['infra/go/${platform}'] = 'version:1.11.2'
  packages['infra/tools/protoc/${platform}'] = 'protobuf_version:v3.6.1'
  packages['infra/third_party/cacert'] = 'date:2017-01-18'
  packages_root = api.path['start_dir'].join('packages')
  api.cipd.ensure(packages_root, packages)

  add_paths = [
    go_root.join('bin'),
    packages_root,
    packages_root.join('bin'),
  ]

  # Build CELab
  cert_file = packages_root.join('cacert.pem')
  goenv = {"GOPATH": go_root, "GIT_SSL_CAINFO": cert_file}
  with api.context(cwd=checkout, env=goenv, env_suffixes={'PATH': add_paths}):
    api.python('install deps', 'build.py', ['deps', '--install', '--verbose'])
    api.python('build', 'build.py', ['build', '--verbose'])

  # Upload binaries (cel_ctl and resources/*) for CI builds
  if api.buildbucket.build.builder.bucket == 'ci':
    output_dir = _get_bin_directory(api, checkout)
    cel_ctl = _get_ctl_binary_name(api)
    zip_out = api.path['start_dir'].join('cel.zip')
    pkg = api.zip.make_package(output_dir, zip_out)
    pkg.add_file(output_dir.join(cel_ctl))
    pkg.add_directory(output_dir.join('resources'))
    pkg.zip('zip archive')

    today = api.time.utcnow().date()
    gs_dest = '%s/%s/%s/cel.zip' % (
      api.buildbucket.builder_name,
      today.strftime('%Y/%m/%d'),
      api.buildbucket.build.id)
    api.gsutil.upload(
      source=zip_out,
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
