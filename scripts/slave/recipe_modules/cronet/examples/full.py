# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze
from recipe_engine.recipe_api import Property

DEPS = [
  'chromium',
  'cronet',
  'recipe_engine/runtime',
  'recipe_engine/properties',
]

BUILDERS = freeze({
  'local_test': {
    'recipe_config': 'main_builder',
    'run_tests': True,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
    },
    'use_goma': False,
  },
  'gn_test': {
    'recipe_config': 'main_builder',
    'run_tests': True,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
    },
    'chromium_apply_config': ['gn'],
  },
  'mb_test': {
    'recipe_config': 'main_builder',
    'run_tests': True,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'chromium_apply_config': ['mb'],
  },
})


PROPERTIES = {
  'buildername': Property(),
}


def RunSteps(api, buildername):
  builder_config = BUILDERS.get(buildername, {})
  recipe_config = builder_config['recipe_config']
  kwargs = builder_config.get('kwargs', {})
  chromium_apply_config = builder_config.get('chromium_apply_config')

  cronet = api.cronet
  cronet.init_and_sync(recipe_config, kwargs,
                       chromium_apply_config=chromium_apply_config)

  use_goma = builder_config.get('use_goma', True)
  cronet.build(use_goma=use_goma)

  cronet.upload_package(kwargs['BUILD_CONFIG'])
  cronet.sizes('sample-perf-id')
  cronet.run_tests()
  cronet.run_perf_tests('sample-perf-id')

def GenTests(api):
  for bot_id in BUILDERS.iterkeys():
    props = api.properties.generic(
      buildername=bot_id,
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      repository='https://chromium.googlesource.com/chromium/src',
      branch='master',
      project='src',
      got_revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      got_revision_cp='refs/heads/master@{#291141}',
      git_revision='a' * 40
    )
    # Test regular bot.
    yield api.test(bot_id) + props
    # Test experimental bot.
    yield (
        api.runtime(is_luci=True, is_experimental=True) +
        api.test(bot_id + "_experimental") +
        props
    )
