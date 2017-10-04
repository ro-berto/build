# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_checkout',
    'chromium_tests',
    'recipe_engine/platform',
    'recipe_engine/properties',
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
  for path_config in ('buildbot', 'kitchen'):
    yield (
        api.test(path_config) +
        api.platform('win', 64) +
        api.properties(
            buildername='example_buildername',
            path_config=path_config)
    )

  yield (
      api.test('webrtc') +
      api.platform('win', 64) +
      api.properties(
          buildername='example_buildername',
          patch_repository_url='https://webrtc.googlesource.com/src')
  )
