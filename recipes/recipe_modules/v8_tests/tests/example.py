# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine.post_process import Filter

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/runtime',
    'v8_tests',
]

def RunSteps(api):
  api.v8_tests.set_config('v8')
  api.v8_tests.set_up_swarming()
  api.v8_tests.read_cl_footer_flags()
  api.v8_tests.load_static_test_configs()
  tests = api.v8_tests.extra_tests_from_properties()
  api.v8_tests.runtests(tests)


def GenTests(api):
  # Minimal v8-side test spec for simulating most recipe features.
  test_spec = json.dumps({
    "tests": [
      {"name": "v8testing"},
      {"name": "test262", "test_args": ["--extra-flags=--flag"]},
    ],
  }, indent=2)
  parent_test_spec = api.v8_tests.example_parent_test_spec_properties(
      'v8_foobar_rel_ng_triggered', test_spec)
  buider_spec = parent_test_spec.get('parent_test_spec', {})
  swarm_hashes = api.v8_tests._make_dummy_swarm_hashes(
      test[0] for test in buider_spec.get('tests', []))

  yield (
      api.test('basic') +
      api.buildbucket.try_build() +
      api.properties(swarm_hashes=swarm_hashes, **parent_test_spec)
  )

  yield (
      api.test('cl_with_resultdb_footer') +
      api.buildbucket.try_build() +
      api.properties(swarm_hashes=swarm_hashes, **parent_test_spec) +
      api.step_data('parse description',
                    api.json.output({'V8-Recipe-Flags': ['resultdb']})) +
      api.post_process(Filter(
          'parse description', 'trigger tests.[trigger] Check', 'Check'))
  )
