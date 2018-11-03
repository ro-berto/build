# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import DropExpectation

DEPS = [
  'recipe_engine/properties',
  'v8',
]

def RunSteps(api):
  api.v8.apply_bot_config({})
  api.v8.checkout()
  api.v8.load_static_test_configs()
  api.v8.compile(
      test_spec=api.v8.TEST_SPEC.from_python_literal(
          {'TestBuilder': {'tests': [{'name': 'v8testing'}]}},
          ['TestBuilder'],
      ),
      out_dir=api.properties.get('out_dir'),
  )


def GenTests(api):
  def test(name, **kwargs):
    return (
        api.test(name) +
        api.properties.generic(
          path_config='kitchen',
          **kwargs
        )
    )

  yield test('basic')

  yield (
      test('custom_out_dir', out_dir='out-ref') +
      api.v8.check_in_any_arg('compile', 'v8/out-ref/Release') +
      api.v8.check_in_any_arg('isolate tests', 'v8/out-ref/Release') +
      api.post_process(DropExpectation)
  )
