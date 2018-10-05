# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe for building and running tests for Open Screen stand-alone."""

DEPS = [
  'depot_tools/depot_tools',
  'depot_tools/git',
  'goma',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

BUILD_CONFIG = 'Default'
BUILD_TARGET = ['hello']
OPENSCREEN_REPO = 'https://chromium.googlesource.com/openscreen'


def RunSteps(api):
  build_root = api.path['start_dir']
  openscreen_root = build_root.join('openscreen')
  repository = api.properties['repository']
  api.git.checkout(repository, dir_path=openscreen_root, recursive=True)
  api.goma.ensure_goma()
  checkout_path = api.path['checkout']
  output_path = checkout_path.join('out', BUILD_CONFIG)
  with api.context(cwd=checkout_path):
    api.step('install build tools',
             [checkout_path.join('tools', 'install-build-tools.sh')])
    api.step('gn gen', [checkout_path.join('gn'), 'gen', output_path])
    ninja_cmd = [api.depot_tools.ninja_path, '-C', output_path,
                 '-j', api.goma.recommended_goma_jobs] + BUILD_TARGET
    api.goma.build_with_goma(
        name='compile',
        ninja_command=ninja_cmd,
        ninja_log_outdir=output_path)


def GenTests(api):
  yield (
      api.test('linux64_debug') +
      api.platform('linux', 64) +
      api.properties(repository=OPENSCREEN_REPO))
