# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import DropExpectation

DEPS = [
  'recipe_engine/buildbucket',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'v8',
]

def RunSteps(api):
  api.v8.apply_bot_config({'triggers': ['v8_triggered_bot']})
  api.v8.checkout()
  api.v8.load_static_test_configs()
  api.v8.compile(
      test_spec=api.v8.TEST_SPEC.from_python_literal(
          {'TestBuilder': {'tests': [{'name': 'v8testing'}]}},
          ['TestBuilder'],
      ),
      out_dir=api.properties.get('out_dir'),
  )
  api.v8.maybe_trigger()


def GenTests(api):
  def test(name, **kwargs):
    return (
        api.test(name) +
        api.properties.generic(
          path_config='kitchen',
          **kwargs
        ) +
        api.runtime(is_luci=True, is_experimental=False)
    )

  yield test('basic')

  yield (
      test('custom_out_dir', out_dir='out-ref') +
      api.v8.check_in_any_arg('compile', 'v8/out-ref/Release') +
      api.v8.check_in_any_arg('isolate tests', 'v8/out-ref/Release') +
      api.post_process(DropExpectation)
  )

  yield (
      test('correct_user_agent_for_cq_triggered_trybots') +
      api.buildbucket.try_build(
        project='v8',
        git_repo='https://chromium.googlesource.com/v8/v8',
        tags=api.buildbucket.tags(user_agent='cq')) +
      api.v8.check_in_any_arg('trigger', 'user_agent:cq') +
      api.post_process(DropExpectation)
  )
