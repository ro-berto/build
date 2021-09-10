# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'builder_group',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/runtime',
    'test_results',
]

PROPERTIES = {
    'warning': Property(
        default=False, kind=bool,
        help='Whether a failure should be treated as a warning.'),
    'server_config': Property(
        default=None,
        help='Name of the server config to use.')
}

def RunSteps(api, warning, server_config):
  if server_config:
    api.test_results.set_config(server_config)

  gtest_results = {
      'disabled_tests': [
          'Disabled.Test',
      ],
      'per_iteration_data': [{
          'Skipped.Test': [
              {'status': 'SKIPPED', 'elapsed_time_ms': 0},
          ],
      }],
  }
  api.test_results.upload(
      api.json.input(gtest_results),
      chrome_revision=2,
      test_type='example-test-type',
      downgrade_error_to_warning=warning,
      builder_name_suffix='sample-suffix')


def GenTests(api):
  builder_data = sum([
      api.buildbucket.ci_build(builder='ExampleBuilder', build_number=123),
      api.builder_group.for_current('example.group'),
  ], api.empty_test_data())

  for config in ('no_server', 'public_server', 'staging_server'):
    yield api.test(
        'upload_success_%s' % config,
        builder_data,
        api.properties(server_config=config),
    )

  yield api.test(
      'upload_success_experimental',
      builder_data,
      api.runtime(is_experimental=True),
  )

  yield api.test(
      'upload_and_degrade_to_warning',
      builder_data,
      api.step_data('Upload to test-results [example-test-type]', retcode=1),
      api.properties(warning=True),
  )

  yield api.test(
      'upload_without_degrading_failures',
      builder_data,
      api.step_data('Upload to test-results [example-test-type]', retcode=1),
      api.properties(warning=False),
  )
