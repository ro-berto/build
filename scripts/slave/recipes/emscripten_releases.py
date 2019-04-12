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
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/runtime',
    'recipe_engine/step'
]

def RunSteps(api):
  api.gclient.set_config('emscripten_releases')
  goma_dir = api.goma.ensure_goma()
  env = {
      'GOMA_DIR': goma_dir,
  }
  api.goma.start()
  sync_dir = api.path['builder_cache'].join('sync')
  api.file.ensure_directory('Ensure sync dir', sync_dir)
  build_dir = api.path['builder_cache'].join('build')
  waterfall_build = sync_dir.join('waterfall', 'src', 'build.py')
  dir_flags = ['--sync-dir=%s' % sync_dir,
               '--build-dir=%s' % build_dir,
               '--prebuilt-dir=%s' % sync_dir]
  with api.context(cwd=sync_dir):
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()

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
