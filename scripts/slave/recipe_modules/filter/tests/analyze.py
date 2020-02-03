# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'filter',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium_chromeos'),
      **api.properties.get('chromium_config_kwargs', {
          'TARGET_PLATFORM': 'chromeos',
          'TARGET_CROS_BOARD': 'x86-generic',
      }))
  if api.properties.get('gn', False):
    api.chromium.apply_config('gn')
  else:
    api.chromium.apply_config('mb')

  api.filter.analyze(
      api.properties.get('affected_files', ['file1', 'file2']),
      ['test1', 'test2'], ['compile1', 'compile2'],
      'config.json',
      mb_mastername='test_mastername',
      mb_buildername='test_buildername',
      mb_config_path='path/to/custom_mb_config.pyl')


def GenTests(api):
  yield api.test(
      'custom_mb_config_path',
      api.properties(config='cros'),
      api.post_process(post_process.StepCommandContains, 'analyze',
                       ['--config-file', 'path/to/custom_mb_config.pyl']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cros_no_mb',
      api.properties(config='cros', gn=True),
      api.post_process(post_process.MustRun, 'system_python'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mac',
      api.platform('mac', 64),
      api.properties(
          chromium_config='chromium',
          chromium_config_kwargs={'TARGET_PLATFORM': 'mac'}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'windows-exclusion',
      api.properties(
          chromium_config='chromium',
          chromium_config_kwargs={'TARGET_PLATFORM': 'win'},
          affected_files=[
              r'path\\to\\changed\\file1', r'path\\to\\changed\\file2'
          ]),
      api.platform('win', 64),
      api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
              'base': {
                  'exclusions': ['path/to/changed/.*'],
              },
              'chromium': {
                  'exclusions': [],
              }
          })),
      api.post_process(post_process.MustRun, 'analyze_matched_exclusion'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'empty-affected-file',
      api.properties(
          chromium_config='chromium',
          chromium_config_kwargs={'TARGET_PLATFORM': 'linux'},
          affected_files=[r'path/to/changed/file1', r'']),
      api.platform('linux', 64),
      api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
              'base': {
                  'exclusions': ['path/to/changed/.*'],
              },
              'chromium': {
                  'exclusions': [],
              }
          })),
      api.post_process(post_process.MustRun, 'analyze_matched_exclusion'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
