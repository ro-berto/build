# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
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
  api.bot_update.ensure_checkout(no_shallow=True)
  if ClusterfuzzHasIssues(api):
    raise api.step.StepFailure('Clusterfuzz had issues.')


def GenTests(api):
  yield (
      api.test('clusterfuzz_no_issues') +
      api.properties.generic(mastername='client.v8.fyi',
                             buildername='Auto-roll - release process')
  )

  yield (
      api.test('clusterfuzz_issues') +
      api.properties.generic(mastername='client.v8.fyi',
                             buildername='Auto-roll - release process') +
      api.override_step_data('check clusterfuzz', api.json.output([1, 2]))
  )
