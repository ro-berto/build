# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'chromium_checkout',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/properties',
  'recipe_engine/runtime',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.chromium_checkout.ensure_checkout({})
  with api.context(cwd=api.chromium_checkout.get_checkout_dir({})):
    api.chromium.mb_analyze(
        'test_mastername',
        'test_buildername',
        {
            'files': ['base/test/launcher/test_launcher.cc'],
            'test_targets': ['base_unittests'],
            'additional_compile_targets': ['chrome']
        })


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='test_mastername',
          buildername='test_buildername',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.post_process(post_process.MustRun, 'analyze') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )
