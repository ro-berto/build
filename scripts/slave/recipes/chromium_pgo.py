# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'archive',
  'chromium',
  'pgo',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]


PGO_BUILDERS = freeze({
  'chromium.fyi': {
    'builders': {
      'Chromium Win PGO Builder': {
        'recipe_config': 'chromium',
        'chromium_config_instrument': 'chromium_pgo_instrument',
        'chromium_config_optimize': 'chromium_pgo_optimize',
        'gclient_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': { 'platform': 'win' },
      },
      'Chromium Win x64 PGO Builder': {
        'recipe_config': 'chromium',
        'chromium_config_instrument': 'chromium_pgo_instrument',
        'chromium_config_optimize': 'chromium_pgo_optimize',
        'gclient_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win_pgo': {
        'recipe_config': 'chromium',
        'chromium_config_instrument': 'chromium_pgo_instrument',
        'chromium_config_optimize': 'chromium_pgo_optimize',
        'gclient_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': { 'platform': 'win' },
      },
    },
  },
})


def RunSteps(api):
  _, bot_config = api.chromium.configure_bot(PGO_BUILDERS, [])
  api.pgo.compile_pgo(bot_config)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(PGO_BUILDERS):
    yield test
