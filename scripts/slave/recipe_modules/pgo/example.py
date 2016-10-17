# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Example of using the PGO recipe module."""

# Recipe module dependencies.
DEPS = [
  'chromium',
  'pgo',
  'recipe_engine/platform',
  'recipe_engine/properties',
]

from recipe_engine.recipe_api import Property
from recipe_engine.types import freeze


TEST_BUILDERS = freeze({
  'chromium_pgo.test' : {
    'builders': {
      'Test builder': {
        'recipe_config': 'chromium',
        'chromium_config_instrument': 'chromium_pgo_instrument',
        'chromium_config_optimize': 'chromium_pgo_optimize',
        'gclient_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'patch_root': 'src',
        'testing': { 'platform': 'win' },
      },
    },
  }
})


def RunSteps(api):
  _, bot_config = api.chromium.configure_bot(TEST_BUILDERS, [])
  api.pgo.compile_pgo(bot_config)


def GenTests(api):
  def _sanitize_nonalpha(text):
    return ''.join(c if c.isalnum() else '_' for c in text)

  # Don't use api.chromium.gen_tests_for_builders because that looks at a
  # builder's name to set the platform, but we want to set 'win'.
  for mastername in TEST_BUILDERS:
    for buildername in TEST_BUILDERS[mastername]['builders']:
      yield (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(mastername=mastername, buildername=buildername) +
        api.platform('win', 64)
      )

