# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools

DEPS = [
  'chromium',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARD=api.properties.get('target_cros_board'))

  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)

  if api.properties.get('use_explicit_isolate_map_path'):
    api.chromium.c.project_generator.isolate_map_paths = [
        api.path['checkout'].join(
            'testing', 'buildbot', 'gn_isolate_map.pyl')]
  api.chromium.run_mb(
      mastername='test_mastername',
      buildername='test_buildername',
      phase='test_phase',
      isolated_targets=['base_unittests_run'],
      android_version_code=3,
      android_version_name='example',
      gn_args_presenter=functools.partial(
          api.chromium.default_gn_args_presenter,
          **api.properties.get('presenter_kwargs', {})))


def GenTests(api):
  yield api.test('basic')

  yield (
      api.test('cros_board') +
      api.properties(
          target_platform='chromeos',
          target_cros_board='x86-generic')
  )

  yield (
      api.test('win') +
      api.properties(chromium_apply_config=['msvs2015', 'win_analyze'])
  )

  yield (
      api.test('mac') +
      api.platform('mac', 64) +
      api.properties(target_platform='mac')
  )

  yield (
      api.test('explicit_mb') +
      api.properties(
          use_explicit_isolate_map_path=True,
          chromium_apply_config=['chromium_official'])
  )

  yield (
      api.test('gn_args_location') +
      api.properties(presenter_kwargs={'location': 'text'})
  )

  yield (
      api.test('many_gn_args') +
      api.step_data(
          'GN args',
          api.raw_io.output_text(
              '\n'.join('arg%02d = "value%d' % (i, i) for i in xrange(30))))
  )
