# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.engine_types import freeze
from recipe_engine.recipe_api import Property
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'cronet',
    'chromium',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/properties',
]

BUILDERS = freeze({
  'local_test': {
    'recipe_config': 'main_builder_mb',
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
      'REPO_URL': 'https://chromium.googlesource.com/chromium/src.git',
      'REPO_NAME': 'src',
    },
    'cronet_kwargs': {
      'PERF_ID': 'android_cronet_local_test_builder',
    },
    'use_goma': False,
  },
  'android-cronet-marshmallow-arm64-perf-rel': {
    'recipe_config': 'arm64_builder_mb',
    'run_perf_tests': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
      'REPO_NAME': 'src',
    },
    'cronet_kwargs': {
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
  raw_result = api.cronet.build(use_goma=use_goma)
  if raw_result.status != common_pb.SUCCESS:
    return raw_result

  if builder_config.get('run_perf_tests'):
    return api.cronet.run_perf_tests(cronet_kwargs['PERF_ID'])


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  for builder in BUILDERS.keys():
    yield api.test(
        _sanitize_nonalpha(builder),
        api.chromium.ci_build(
            builder=builder,
            builder_group='chromium.android',
        ),
    )

  yield api.test(
      'compile_failure',
      api.chromium.ci_build(
          builder='local_test',
          builder_group='chromium.android',
      ),
      api.step_data('compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
