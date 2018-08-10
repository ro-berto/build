# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools

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

def _test_args(api, args=None):
  args = args or _DEFAULT_ARGS
  return (api.properties(expected_args=args)
          + api.step_data('read GN args', api.raw_io.output_text(args)))

def RunSteps(api):
  args = api.gn.get_args(
      api.path['checkout'].join('out', 'Release'),
      presenter=functools.partial(
          api.gn.default_args_presenter,
          **api.properties.get('presenter_kwargs', {})))
  assert args == api.properties.get('expected_args'), \
      'expected:\n%s\nactual:%s' % (api.properties.get('expected_args'), args)

def GenTests(api):
  yield (
      api.test('basic')
      + _test_args(api)
  )

  yield (
      api.test('present_to_logs')
      + _test_args(api)
      + api.properties(presenter_kwargs={'location': 'logs'})
  )

  yield (
      api.test('many_args')
      + _test_args(api, '\n'.join('arg%02d = "value%d"' % (i, i) for i in xrange(10)))
      + api.properties(presenter_kwargs={'text_limit': 5})
  )

  yield (
      api.test('present_to_text')
      + _test_args(api, '\n'.join('arg%02d = "value%d"' % (i, i) for i in xrange(10)))
      + api.properties(presenter_kwargs={'location': 'text', 'text_limit': 5})
  )

  yield (
      api.test('args_with_imports')
      + _test_args(api, (
          'import("//build/args/headless.gn")\n'
          'goma_dir = "/b/build/slave/cache/goma_client"\n'
          'target_cpu = "x86"\n'
          'use_goma = true\n'))
  )
