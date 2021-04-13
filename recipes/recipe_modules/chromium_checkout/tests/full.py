# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/step',
]


def RunSteps(api):
  _, bot_config = api.chromium_tests.lookup_builder(
      chromium.BuilderId.create_for_group('chromium.linux', 'Linux Builder'))

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
    check(step.cwd == str(expected_path))
    return {}

  def try_build():
    return api.chromium.try_build(builder='builder')

  yield api.test(
      'win',
      try_build(),
      api.platform('win', 64),
      api.post_process(verify_checkout_dir, api.path['cache'].join(
          'builder', 'src')),
  )

  yield api.test(
      'linux',
      try_build(),
      api.post_process(verify_checkout_dir, api.path['cache'].join(
          'builder', 'src')),
  )
