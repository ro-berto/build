# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'isolate',
  'path',
]


def GenSteps(api):
  # Code coverage for isolate_server property.
  api.isolate.isolate_server = 'https://isolateserver-dev.appspot.com'
  assert api.isolate.isolate_server == 'https://isolateserver-dev.appspot.com'

  # Generates code coverage for find_isolated_tests corner cases.
  # TODO(vadimsh): This step doesn't actually make any sense when the recipe
  # is running for real via run_recipe.py.
  yield api.isolate.find_isolated_tests(
      api.path['build'], ['test1', 'test2'])


def GenTests(api):
  # Expected targets == found targets.
  yield api.test('basic')

  # Found more than expected.
  yield (
      api.test('extra') +
      api.override_step_data('find isolated tests',
          api.isolate.output_json(['test1', 'test2', 'extra_test'])))

  # Didn't find something.
  yield (
      api.test('missing') +
      api.override_step_data('find isolated tests',
          api.isolate.output_json(['test1'])))
