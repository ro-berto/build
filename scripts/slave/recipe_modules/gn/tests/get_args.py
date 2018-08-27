# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools

from recipe_engine import post_process

DEPS = [
    'gn',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

_DEFAULT_ARGS = (
    'goma_dir = "/b/build/slave/cache/goma_client"\n'
    'target_cpu = "x86"\n'
    'use_goma = true\n')

_OUTPUT_TEMPLATE = '''

Writing """\\
%s""" to _path_/args.gn

/fake-path/chromium/src/buildtools/linux64/gn gen _path_
'''

def _test_args(api, args=None):
  args = args or _DEFAULT_ARGS
  if not args[-1] == '\n':
    args += '\n'
  output = _OUTPUT_TEMPLATE % args
  return (api.properties(expected_args=args)
          + api.step_data('lookup GN args', stdout=api.raw_io.output_text(output)))

def RunSteps(api):
  args = api.gn.get_args(
      mb_path=api.path['checkout'].join('tools', 'mb'),
      mb_config_path=api.path['checkout'].join('tools', 'mb', 'mb_config.pyl'),
      mastername='test-master',
      buildername='test-builder',
      location=api.properties.get('location'),
      max_text_lines=api.properties.get('max_text_lines'))
  assert args == api.properties.get('expected_args'), \
      'expected:\n%s\nactual:\n%s' % (api.properties.get('expected_args'), args)

def GenTests(api):
  yield (
      api.test('basic')
      + _test_args(api)
      + api.post_process(post_process.StepTextContains, 'lookup GN args', [
          ('target_cpu = "x86"<br/>'
           'use_goma = true<br/>'),
          'goma_dir = "/b/build/slave/cache/goma_client"'])
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('present_to_logs')
      + _test_args(api)
      + api.properties(location=api.gn.LOGS)
      + api.post_process(
          post_process.LogContains,
          'lookup GN args',
          'gn_args',
          [
              ('target_cpu = "x86"\n'
               'use_goma = true\n'),
              'goma_dir = "/b/build/slave/cache/goma_client"\n',
          ]
      )
      + api.post_process(post_process.DropExpectation)
  )

  args = '\n'.join('arg%02d = "value%d"' % (i, i) for i in xrange(10))
  yield (
      api.test('many_args')
      + _test_args(api, args)
      + api.properties(max_text_lines=5)
      + api.post_process(post_process.LogContains, 'lookup GN args', 'gn_args',
                         [args])
      + api.post_process(post_process.StepTextContains, 'lookup GN args',
                         ['exceeds limit', 'presented in logs instead'])
      + api.post_process(post_process.DropExpectation)
  )

  args = '\n'.join('arg%02d = "value%d"' % (i, i) for i in xrange(10))
  yield (
      api.test('present_to_text')
      + _test_args(api, args)
      + api.properties(location=api.gn.TEXT, max_text_lines=5)
      + api.post_process(post_process.StepTextContains, 'lookup GN args',
                         [args.replace('\n', '<br/>')])
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('args_with_imports')
      + _test_args(api, (
          'import("//build/args/headless.gn")\n'
          'goma_dir = "/b/build/slave/cache/goma_client"\n'
          'target_cpu = "x86"\n'
          'use_goma = true\n'))
      + api.post_process(post_process.StepTextContains, 'lookup GN args', [
          ('import("//build/args/headless.gn")<br/>'
           'target_cpu = "x86"<br/>'
           'use_goma = true<br/>'),
          'goma_dir = "/b/build/slave/cache/goma_client"'])
      + api.post_process(post_process.DropExpectation)
  )

  output = 'output\nnot\nin\n"mb lookup"\nformat\n'
  yield (
      api.test('bad mb output')
      + api.step_data('lookup GN args',
                      stdout=api.raw_io.output_text(output))
      + api.properties(expected_args=None)
      + api.post_process(post_process.StepTextContains, 'lookup GN args',
                         ['Failed to extract GN args'])
      + api.post_process(post_process.LogEquals, 'lookup GN args',
                         'mb lookup output', output)
      + api.post_process(post_process.StatusCodeIn, 1)
      + api.post_process(post_process.ResultReasonRE,
                         'Failed to extract GN args')
      + api.post_process(post_process.DropExpectation)
  )
