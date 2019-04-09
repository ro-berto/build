# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/python',
    'recipe_engine/step'
]

def RunSteps(api):
  api.gclient.set_config('emscripten_releases')
  api.bot_update.ensure_checkout()
  sync_dir = api.path['start_dir'].join('sync')
  build_dir = api.path['cache'].join('builder', 'build')
  waterfall_build = api.path['start_dir'].join('waterfall', 'src', 'build.py')
  dir_flags = ['--sync-dir=%s' % sync_dir,
               '--build-dir=%s' % build_dir]
  # The bot_update call above handles the sources in DEPS. All that's left for
  # this sync step is updating the prebuilt host toolchain (eg. clang) and CMake
  # TODO: Consider CIPD packages for these, or whatever mechanism other
  # recipes use.
  api.python('Sync Buildtools', waterfall_build,
             dir_flags + ['--no-build', '--no-test',
              '--sync-include=tools-clang,host-toolchain,cmake'])
  # Depot tools on path is for ninja
  with api.depot_tools.on_path():
    api.python('Build Wabt', waterfall_build,
               dir_flags + ['--no-sync', '--no-test',
               '--build-include=wabt'])

def GenTests(api):
  yield api.test('basic')
