# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'goma',
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
  if api.runtime.is_luci:
    checkout_root = api.path['builder_cache']
  else:
    # TODO(sergiyb): Remove this branch after migrating to LUCI.
    checkout_root = api.path['start_dir']
  with api.context(cwd=checkout_root):
    result = api.bot_update.ensure_checkout()
  got_revision = result.presentation.properties['got_waterfall_revision']
  goma_dir = api.goma.ensure_goma()
  env = {
      'BUILDBOT_MASTERNAME': api.properties['mastername'],
      'BUILDBOT_BUILDERNAME': api.properties['buildername'],
      'BUILDBOT_REVISION': api.properties['revision'],
      'BUILDBOT_GOT_WATERFALL_REVISION': got_revision,
      'GOMA_DIR': goma_dir,
  }

  api.goma.start()
  exit_status = -1
  try:
    depot_tools_path = checkout_root.join('depot_tools')
    with api.context(cwd=api.path['checkout'], env=env,
                     env_prefixes={'PATH': [depot_tools_path]}):
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
  yield (
    api.test('linux') +
    api.properties(
      mastername = 'client.wasm.llvm',
      buildername = 'linux',
      bot_id = 'TestBot',
      revision = 'abcd',
    ))

  yield (
    api.test('linux_fail') +
    api.properties(
      mastername = 'client.wasm.llvm',
      buildername = 'linux',
      bot_id = 'TestBot',
      revision = 'abcd',
    ) + api.step_data('annotated steps', retcode=1))

  yield (
    api.test('luci') +
    api.properties(
      mastername = 'client.wasm.llvm',
      buildername = 'linux',
      bot_id = 'TestBot',
      revision = 'abcd',
      path_config='kitchen',
    ) +
    api.runtime(is_luci=True, is_experimental=False)
  )
