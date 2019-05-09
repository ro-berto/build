# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze
from recipe_engine.recipe_api import Property

DEPS = [
  'cronet',
  'recipe_engine/buildbucket',
  'recipe_engine/path',
  'recipe_engine/properties',
]

BUILDERS = freeze({
  'local_test': {
    'recipe_config': 'main_builder_mb',
    'run_tests': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
      'REPO_URL': 'https://chromium.googlesource.com/chromium/src.git',
      'REPO_NAME': 'src',
    },
    'cronet_kwargs': {
      'report_sizes': True,
      'PERF_ID': 'android_cronet_local_test_builder',
    },
    'use_goma': False,
  },
  'Android Cronet Marshmallow 64bit Perf': {
    'recipe_config': 'arm64_builder_mb',
    'run_tests': False,
    'run_perf_tests': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
      'REPO_NAME': 'src',
    },
    'cronet_kwargs': {
      'report_sizes': False,
      'PERF_ID': 'android_cronet_m64_perf',
    },
    'chromium_apply_config': ['cronet_official'],
  },
})


def RunSteps(api):
  builder_config = BUILDERS.get(api.buildbucket.builder_name, {})
  recipe_config = builder_config['recipe_config']
  kwargs = builder_config.get('kwargs', {})
  cronet_kwargs = builder_config.get('cronet_kwargs', {})

  api.cronet.init_and_sync(
      recipe_config, kwargs,
      chromium_apply_config=builder_config.get('chromium_apply_config'))

  use_goma = builder_config.get('use_goma', True)
  api.cronet.build(use_goma=use_goma)

  if cronet_kwargs.get('report_sizes') and cronet_kwargs.get('PERF_ID'):
    api.cronet.sizes(cronet_kwargs['PERF_ID'])
  if builder_config.get('run_tests'):
    api.cronet.run_tests()
  if builder_config.get('run_perf_tests'):
    api.cronet.run_perf_tests(cronet_kwargs['PERF_ID'])


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  for bot_id in BUILDERS.keys():
    props = api.properties.generic(
      buildername=bot_id,
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      repository='https://chromium.googlesource.com/chromium/src',
      branch='master',
      project='src',
      got_revision_cp='refs/heads/master@{#291141}',
      git_revision='a' * 40,
    )
    yield api.test(_sanitize_nonalpha(bot_id)) + props
