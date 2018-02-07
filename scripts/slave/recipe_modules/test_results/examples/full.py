# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
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
  for config in ('no_server', 'public_server', 'staging_server'):
    yield (
        api.test('upload_success_%s' % config) +
        api.properties(
            mastername='example.master',
            buildername='ExampleBuilder',
            buildnumber=123,
            server_config=config))

  for config in ('no_server', 'public_server', 'staging_server'):
    yield (
        api.test('upload_success_buildbucket_%s' % config) +
        api.properties(
            mastername='example.master',
            buildername='ExampleBuilder',
            buildnumber=123,
            buildbucket={'build':{'id':2345}},
            server_config=config))

  yield (
      api.test('upload_success_experimental') +
      api.runtime(is_luci=True, is_experimental=True) +
      api.properties(
          mastername='example.master',
          buildername='ExampleBuilder',
          buildnumber=123))

  yield (
      api.test('upload_and_degrade_to_warning') +
      api.step_data('Upload to test-results [example-test-type]', retcode=1) +
      api.properties(
          mastername='example.master',
          buildername='ExampleBuilder',
          buildnumber=123,
          warning=True))

  yield (
      api.test('upload_without_degrading_failures') +
      api.step_data('Upload to test-results [example-test-type]', retcode=1) +
      api.properties(
          mastername='example.master',
          buildername='ExampleBuilder',
          buildnumber=123,
          warning=False))
