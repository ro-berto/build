# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium_checkout',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/runtime',
    'recipe_engine/step',
]


def RunSteps(api):
  bot_config = api.chromium_tests.create_bot_config_object(
      'chromium.linux', 'Linux Builder')

  api.chromium_tests.configure_build(bot_config)

  api.chromium_checkout.ensure_checkout(bot_config)

  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
    'working_dir: %r' % (api.chromium_checkout.working_dir,),
    'affected_files: %r' % (
        api.chromium_checkout.get_files_affected_by_patch(),),
  ]


def GenTests(api):
  yield api.test('full')

  def verify_checkout_dir(check, step_odict, expected_path):
    step = step_odict['git diff to analyze patch']
    check(step['cwd'] == str(expected_path))
    return {}

  def try_build():
    return api.buildbucket.try_build(
        project='chromium',
        builder='linux',
        git_repo='https://chromium.googlesource.com/chromium/src')

  yield (
      api.test('buildbot_annotated_run') +
      try_build() +
      api.platform('win', 64) +
      api.properties(
          buildername='example_buildername',
          path_config='buildbot') +
      api.post_process(verify_checkout_dir, api.path['start_dir'].join('src'))
  )

  yield (
      api.test('buildbot_remote_run') +
      try_build() +
      api.properties(
          buildername='example_buildername',
          path_config='kitchen') + # not a typo... T_T
      api.post_process(verify_checkout_dir,
                       api.path['builder_cache'].join('linux', 'src'))
  )

  yield (
      api.test('buildbot_remote_run_kitchen') +
      try_build() +
      api.properties(
          buildername='example_buildername',
          path_config='generic') +
      api.post_process(verify_checkout_dir,
                       api.path['builder_cache'].join('linux', 'src'))
  )

  yield (
      api.test('luci') +
      try_build() +
      api.runtime(is_luci=True, is_experimental=False) +
      api.properties(
          buildername='does not matter') +
      api.post_process(verify_checkout_dir,
                       api.path['cache'].join('builder', 'src'))
  )
