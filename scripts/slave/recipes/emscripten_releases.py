# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'goma',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/runtime',
    'recipe_engine/step'
]

def RunSteps(api):
  api.gclient.set_config('emscripten_releases')
  api.bot_update.ensure_checkout()
  goma_dir = api.goma.ensure_goma()
  env = {
      'GOMA_DIR': goma_dir,
  }
  api.goma.start()
  sync_dir = api.path['start_dir'].join('sync')
  build_dir = api.path['builder_cache'].join('build')
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
    with api.context(env=env):
      try:
        api.python('Build Wabt', waterfall_build,
                   dir_flags + ['--no-sync', '--no-test',
                                '--build-include=wabt'])
        api.python('Build Binaryen', waterfall_build,
                   dir_flags + ['--no-sync', '--no-test',
                                '--build-include=binaryen'])
      except api.step.StepFailure as e:
        # If any of these builds fail, testing won't be meaningful.
        exit_status = e.retcode
        raise
      else:
        exit_status = 0
      finally:
        api.goma.stop(build_exit_status=exit_status)


def GenTests(api):
  def test(name):
    return (
        api.test(name) +
        api.properties(path_config='kitchen') +
        api.runtime(is_luci=True, is_experimental=False)
    )

  yield test('linux')

  yield (
      test('linux_fail') +
      api.step_data('Build Wabt', retcode=1) +
      api.post_process(Filter('postprocess_for_goma.upload_log'))
  )
