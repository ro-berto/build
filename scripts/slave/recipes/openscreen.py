# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe for building and running tests for Open Screen stand-alone."""

DEPS = [
  'depot_tools/depot_tools',
  'depot_tools/git',
  'depot_tools/osx_sdk',
  'depot_tools/tryserver',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

BUILD_CONFIG = 'Default'
# TODO: Remove 'hello' when 'gn_all' successfully builds.
BUILD_TARGET = ['hello', 'gn_all', 'demo', 'unittests']
OPENSCREEN_REPO = 'https://chromium.googlesource.com/openscreen'


def _GetHostToolLabel(platform):
  if platform.is_linux and platform.bits == 64:
    return 'linux64'
  elif platform.is_mac:
    return 'mac'
  raise ValueError('unknown or unsupported platform')  # pragma: no cover


def RunSteps(api):
  build_root = api.path['start_dir']
  openscreen_root = build_root.join('openscreen')
  repository = api.properties['repository']

  api.git.checkout(
      repository, dir_path=openscreen_root,
      ref=api.tryserver.gerrit_change_fetch_ref, recursive=True)
  api.goma.ensure_goma()
  checkout_path = api.path['checkout']
  output_path = checkout_path.join('out', BUILD_CONFIG)
  with api.context(cwd=checkout_path):
    api.step('install build tools',
             [checkout_path.join('tools', 'install-build-tools.sh'),
              _GetHostToolLabel(api.platform)])

    is_debug = str(api.properties.get('debug', False)).lower()
    is_asan = str(api.properties.get('is_asan', False)).lower()
    api.step('gn gen',
             [checkout_path.join('gn'), 'gen', output_path,
              '--args=is_debug={} is_asan={}'.format(is_debug, is_asan)
              ])

    # NOTE: The following just runs Ninja without setting up the Mac toolchain
    # if this is being run on a non-Mac platform.
    with api.osx_sdk('mac'):
      ninja_cmd = [api.depot_tools.ninja_path, '-C', output_path,
                   '-j', api.goma.recommended_goma_jobs] + BUILD_TARGET
      api.goma.build_with_goma(
          name='compile',
          ninja_command=ninja_cmd,
          ninja_log_outdir=output_path)
    api.step('Run unit tests', [output_path.join('unittests')])


def GenTests(api):
  yield (
      api.test('linux64_debug') +
      api.platform('linux', 64) +
      api.buildbucket.try_build('openscreen', 'try') +
      api.properties(
          repository=OPENSCREEN_REPO,
          debug=True,
          is_asan=True
      )
  )
  yield (
      api.test('mac_debug') +
      api.platform('mac', 64) +
      api.buildbucket.try_build('openscreen', 'try') +
      api.properties(
          repository=OPENSCREEN_REPO,
          debug=True,
          is_asan=False
      )
  )
