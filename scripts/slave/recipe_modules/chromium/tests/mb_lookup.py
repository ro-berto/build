# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARD=api.properties.get('target_cros_board'))

  gn_args = api.chromium.mb_lookup('test_mastername', 'test_buildername')
  expected_gn_args = api.properties.get('expected_gn_args')
  assert gn_args == expected_gn_args, (
      'expected:\n%s\n\nactual:\n%s' % (expected_gn_args, gn_args))

_MB_LOOKUP_OUTPUT_TEMPLATE = '''

Writing """\\
%s""" to _path_/args.gn

/fake-path/chromium/src/buildtools/linux64/gn gen _path_
'''

def GenTests(api):
  gn_args = '\n'.join((
      'goma_dir = "/b/build/slave/cache/goma_client"',
      'target_cpu = "x86"',
      'target_sysroot = "//build/linux"',
      'use_goma = true',
  ))
  expected_step_text = [
      '<br/>'.join(('target_cpu = "x86"', 'use_goma = true')),
      '<br/>'.join((
          'goma_dir = "/b/build/slave/cache/goma_client"',
          'target_sysroot = "//build/linux"'))
  ]

  yield (
      api.test('basic')
      + api.properties(expected_gn_args=gn_args)
      + api.step_data(
          'lookup GN args',
          stdout=api.raw_io.output_text(_MB_LOOKUP_OUTPUT_TEMPLATE % gn_args))
      + api.post_process(post_process.StepTextContains, 'lookup GN args',
                         expected_step_text)
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('cros_board')
      + api.properties(target_platform='chromeos',
                       target_cros_board='x86-generic')
      + api.properties(expected_gn_args=gn_args)
      + api.step_data(
          'lookup GN args',
          stdout=api.raw_io.output_text(_MB_LOOKUP_OUTPUT_TEMPLATE % gn_args))
      + api.post_process(post_process.StepTextContains, 'lookup GN args',
                         expected_step_text)
      + api.post_process(post_process.DropExpectation)
  )

  output = '\n'.join(('output', 'not', 'in', '"mb lookup"', 'format'))
  yield (
      api.test('bad mb output')
      + api.step_data('lookup GN args',
                      stdout=api.raw_io.output_text(output))
      + api.post_process(post_process.StepTextContains, 'lookup GN args',
                         ['Failed to extract GN args'])
      + api.post_process(post_process.LogContains, 'lookup GN args',
                         'mb lookup output', [output])
      + api.post_process(post_process.StatusCodeIn, 1)
      + api.post_process(post_process.ResultReasonRE,
                         'Failed to extract GN args')
      + api.post_process(post_process.DropExpectation)
  )
