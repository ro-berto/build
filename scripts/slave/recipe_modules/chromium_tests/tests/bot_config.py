# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_config
from RECIPE_MODULES.build.chromium_tests import bot_spec

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  # Test failed normalization of bot specs
  spec = {'bot_type': bot_spec.TESTER}
  builders = {
      'fake-master': {
          'builders': {
              'fake-builder': spec,
          },
      },
  }
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_config.BotConfig(builders, [('fake-master', 'fake-builder')])
  message = (
      'Tester-only bot must specify a parent builder while creating spec for '
      "('fake-master', 'fake-builder'): {!r}".format(spec))
  api.assertions.assertEqual(message, caught.exception.message)


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
