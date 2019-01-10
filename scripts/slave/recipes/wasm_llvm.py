# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/runtime',
  'recipe_engine/step',
]


def RunSteps(api):
  api.gclient.set_config('wasm_llvm')
  api.gclient.apply_config('depot_tools')
  checkout_root = api.path['builder_cache']
  with api.context(cwd=checkout_root):
    # We trigger builds on WASM infrastructure based on commits in llvm repository, which means
    # that the repository and revision properties are set to llvm repository URL and corresponding
    # commit in it. However, that repository is checked out by the annotated script below, which
    # does not integrate with bot_update/gclient and that results in errors when the latter tries
    # to apply that revision. Hence we need to instruct it to ignore input commit specified in
    # properties.
    result = api.bot_update.ensure_checkout(ignore_input_commit=True)
  got_revision = result.presentation.properties['got_waterfall_revision']
  goma_dir = api.goma.ensure_goma()
  env = {
      'BUILDBOT_MASTERNAME': api.properties['mastername'],
      'BUILDBOT_BUILDERNAME': api.buildbucket.builder_name,
      'BUILDBOT_REVISION': api.buildbucket.gitiles_commit.id,
      'BUILDBOT_BUILDNUMBER': api.buildbucket.build.number,
      'BUILDBOT_GOT_WATERFALL_REVISION': got_revision,
      'GOMA_DIR': goma_dir,
  }

  api.goma.start()
  exit_status = -1
  try:
    depot_tools_path = checkout_root.join('depot_tools')
    with api.context(cwd=api.path['checkout'], env=env,
                     env_suffixes={'PATH': [depot_tools_path]}):
      api.python('annotated steps',
                 api.path['checkout'].join('src', 'build.py'),
                 allow_subannotations=True)
    exit_status = 0
  except api.step.StepFailure as e:
    exit_status = e.retcode
    raise e
  finally:
    api.goma.stop(build_exit_status=exit_status)


def GenTests(api):
  def test(name, **kwargs):
    return (
        api.test(name) +
        api.properties(
          mastername='client.wasm.llvm',
          path_config='kitchen',
          **kwargs
        ) +
        api.buildbucket.ci_build(
          project='wasm',
          bucket='ci',
          builder='linux',
          build_number=123456,
        ) +
        api.runtime(is_luci=True, is_experimental=False)
    )

  yield test('linux')

  yield (
      test('linux_fail') +
      api.step_data('annotated steps', retcode=1)
  )
