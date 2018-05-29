# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from recipe_engine.types import freeze

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'recipe_engine/properties',
]

BUILDERS = freeze({
  'luci.chromium.ci': {
    'builders': {
      'linux-code-coverage-generation': {
        'chromium_config': 'chromium_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
      },
    },
  },
})

# Sample targets that are used to test code coverage reports generation.
SAMPLE_TARGETS = ['base_unittests', 'url_unittests']
SAMPLE_FUZZER_TARGETS = ['pdfium_fuzzer']


def RunSteps(api):
  _, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])
  api.bot_update.ensure_checkout(patch_root=bot_config.get('root_override'))

  api.chromium.ensure_goma()
  api.chromium.runhooks()


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test
