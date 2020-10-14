# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
  'isolate',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'swarming_client',
]

PROPERTIES = {
  'buildnumber': Property(
    kind=int, help="Number for the build.", default=100),
}


def RunSteps(api):
  # 'isolate_tests' step needs swarming checkout.
  api.swarming_client.checkout('master')

  # Code coverage for isolate_server property.
  api.isolate.isolate_server = 'https://isolateserver-dev.appspot.com'
  assert api.isolate.isolate_server == 'https://isolateserver-dev.appspot.com'

  # Code coverage for namespace property.
  api.isolate.namespace = 'default-gzip'
  assert api.isolate.namespace == 'default-gzip'

  # That would read a list of files to search for, generated in GenTests.
  step_result = api.step('read test spec', ['cat'], stdout=api.json.output())
  expected_targets = step_result.stdout

  build_path = api.isolate.repo_resource()
  # Generates code coverage for find_isolated_tests corner cases.
  # TODO(vadimsh): This step doesn't actually make any sense when the recipe
  # is running for real.
  api.isolate.find_isolated_tests(build_path, expected_targets)

  # Code coverage for 'isolate_tests'. 'isolated_test' doesn't support discovery
  # of isolated targets in build directory, so skip if 'expected_targets' is
  # None.
  if expected_targets is not None:
    api.isolate.isolate_tests(
        build_path, expected_targets)


def GenTests(api):

  def make_test(name, expected_targets, discovered_targets):

    missing = set(expected_targets or []) - set(discovered_targets or [])
    output = api.test(
        name,
        api.step_data(
            'read test spec', stdout=api.json.output(expected_targets)),
        api.override_step_data('find isolated tests',
                               api.isolate.output_json(discovered_targets)),
    )

    # See comment around 'if expected_targets is not None' above.
    if expected_targets:
      output += api.override_step_data(
          'isolate tests', api.isolate.output_json(expected_targets, missing))

    return output

  # Expected targets == found targets.
  yield make_test('basic', ['test1', 'test2'], ['test1', 'test2'])
  # No expectations, just discovering what's there returned by default mock.
  yield make_test('discover', None, None)
  # Found more than expected.
  yield make_test('extra', ['test1', 'test2'], ['test1', 'test2', 'extra_test'])
  # Didn't find something.
  yield (make_test('missing', ['test1', 'test2'], ['test1']) +
         api.properties.generic(buildername='Windows Swarm Test'))
  # No expectations, and nothing has been found, produces warning.
  yield make_test('none', None, [])
