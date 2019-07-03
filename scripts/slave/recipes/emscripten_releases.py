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


step_test_data = { "linux": {
  "build_steps": [
    {
      "name": "Build Wabt",
      "command": ["waterfall/src/build.py", "--no-sync",
                  "--no-test", "--build-include=wabt"]
    }
  ],
  "test_steps": [
    {
      "name": "Emscripten testsuite (upstream)",
      "command": ["waterfall/src/build.py", "--no-sync",
                  "--no-build", "--test-include=emtest"]
    },
    {
      "name": "Emscripten testsuite (asm2wasm)",
      "command": ["waterfall/src/build.py", "--no-sync",
                  "--no-build", "--test-include=emtest-asm"]
    }
  ]
}}

def RunSteps(api):
  api.gclient.set_config('emscripten_releases')
  goma_dir = api.goma.ensure_goma()
  env = {
      'BUILDBOT_MASTERNAME': 'emscripten-releases',
      'BUILDBOT_BUILDERNAME': api.buildbucket.builder_name,
      'BUILDBOT_REVISION': api.buildbucket.gitiles_commit.id,
      'BUILDBOT_BUILDNUMBER': api.buildbucket.build.number,
      'BUILDBOT_BUCKET': api.buildbucket.build.builder.bucket,
      'GOMA_DIR': goma_dir,
  }
  api.goma.start()

  cache_dir = api.path['builder_cache']
  sync_dir = cache_dir.join('emscripten-releases')
  api.file.ensure_directory('Ensure sync dir', sync_dir)
  build_dir = cache_dir.join('emscripten-releases', 'build')
  install_dir = api.path['start_dir'].join('install')
  waterfall_build = sync_dir.join('waterfall', 'src', 'build.py')
  dir_flags = ['--sync-dir=%s' % sync_dir,
               '--build-dir=%s' % build_dir,
               '--prebuilt-dir=%s' % sync_dir,
               '--v8-dir=%s' % cache_dir.join('v8'),
               '--install-dir=%s' % install_dir]
  build_only_flags = dir_flags + ['--no-sync', '--no-test']

  api.file.ensure_directory('Ensure install dir', install_dir)
  with api.context(cwd=cache_dir):
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()

  # Get list of build.py build and test steps
  bot_steps = api.file.read_json('Read steps from JSON',
                                 sync_dir.join('bots.json'),
                                 test_data=step_test_data)

  builder = api.buildbucket.builder_name
  assert builder in ('linux', 'mac', 'win')

  # Depot tools on path is for ninja
  with api.depot_tools.on_path():
    with api.context(env=env):
      try:
        for step in bot_steps[builder]['build_steps']:
          script = sync_dir.join(step['command'][0])
          args = step['command'][1:]
          api.python(step['name'], script, dir_flags + args)
      except api.step.StepFailure as e:
        # If any of these builds fail, testing won't be meaningful.
        exit_status = e.retcode
        raise
      else:
        exit_status = 0
      finally:
        api.goma.stop(build_exit_status=exit_status)

      # Upload the results before running the test.
      api.python('Upload archive', waterfall_build,
                 build_only_flags + ['--build-include=archive'])

      with api.step.defer_results():
        for step in bot_steps[builder]['test_steps']:
          script = sync_dir.join(step['command'][0])
          args = step['command'][1:]
          api.python(step['name'], script, dir_flags + args)


def GenTests(api):
  def test(name):
    return (
        api.test(name) +
        api.properties(path_config='kitchen') +
        api.buildbucket.ci_build(
            project='emscripten-releases',
            builder='linux',
            build_number=42,
        ) +
        api.runtime(is_luci=True, is_experimental=False)
    )

  yield test('linux')

  yield (
      test('linux_buildfail') +
      api.step_data('Build Wabt', retcode=1) +
      api.post_process(Filter('postprocess_for_goma.upload_log'))
  )

  yield (
      # Check that if the first test fails, the second runs but the
      # overall result is failure.
      test('linux_emtest_fail') +
      api.step_data('Emscripten testsuite (upstream)', retcode=1) +
      api.post_process(Filter('Emscripten testsuite (asm2wasm)',
                              '$result'))
  )
