# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/buildbucket',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'v8',
]

CLUSTERFUZZ = 'https://cluster-fuzz.appspot.com/testcase?key=%d'
SHOW_MAX_ISSUES = 10


def ClusterfuzzHasIssues(api):
  step_test_data = lambda: api.json.test_api.output([])
  step_result = api.python(
      'check clusterfuzz',
      api.path['checkout'].join(
          'tools', 'release', 'check_clusterfuzz.py'),
      ['--key-file=/creds/generic/generic-v8-autoroller_cf_key',
       '--results-file', api.json.output(add_json_log=False)],
      # Note: Output is suppressed for security reasons.
      stdout=api.raw_io.output_text('out'),
      stderr=api.raw_io.output_text('err'),
      step_test_data=step_test_data,
  )
  results = step_result.json.output
  if results:
    step_result.presentation.text = 'Found %s issues.' % len(results)
    for result in results[:SHOW_MAX_ISSUES]:
      step_result.presentation.links[str(result)] = CLUSTERFUZZ % int(result)
    step_result.presentation.status = api.step.FAILURE
    return True
  return False


def RunSteps(api):
  api.gclient.set_config('v8')
  api.v8.checkout()
  if ClusterfuzzHasIssues(api):
    raise api.step.StepFailure('Clusterfuzz had issues.')


def GenTests(api):
  yield (
      api.test('clusterfuzz_no_issues') +
      api.properties.generic(mastername='client.v8.fyi',
                             path_config='kitchen') +
      api.buildbucket.ci_build(
        project='v8',
        git_repo='https://chromium.googlesource.com/v8/v8',
        builder='Auto-roll - release process',
        revision='',  # same as unspecified
      )
  )

  yield (
      api.test('clusterfuzz_issues') +
      api.properties.generic(mastername='client.v8.fyi',
                             path_config='kitchen') +
      api.override_step_data('check clusterfuzz', api.json.output([1, 2])) +
      api.buildbucket.ci_build(
        project='v8',
        git_repo='https://chromium.googlesource.com/v8/v8',
        builder='Auto-roll - release process',
        revision='',  # same as unspecified
      )
  )
