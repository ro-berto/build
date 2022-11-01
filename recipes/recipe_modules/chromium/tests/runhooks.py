# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/runtime',
]


def RunSteps(api):
  api.chromium.set_config(
      'chromium',
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARDS=api.properties.get('target_cros_boards'))
  api.chromium.apply_config('mb')

  api.chromium.runhooks()


def GenTests(api):
  yield api.test('basic')

  yield api.test(
      'chromeos',
      api.properties(
          target_platform='chromeos', target_cros_boards='x86-generic'),
  )

  yield api.test(
      'clobber',
      api.properties(clobber='1'),
  )

  # TODO(b/256012263): Remove this when the fix has rolled in.
  yield api.test(
      'clobber_cros_cache_bug',
      api.properties(clobber='1'),
      api.path.exists(api.path['checkout'].join('build', 'cros_cache')),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mac',
      api.platform.name('mac'),
      api.properties(target_platform='mac'),
  )
