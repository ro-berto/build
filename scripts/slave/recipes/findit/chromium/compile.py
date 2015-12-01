# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine.config import List
from recipe_engine.recipe_api import Property


DEPS = [
  'chromium',
  'chromium_tests',
  'gclient',
  'json',
  'path',
  'properties',
  'python',
  'step',
]


PROPERTIES = {
    'target_mastername': Property(
        kind=str, help='The target master to match compile config to.'),
    'target_buildername': Property(
        kind=str, help='The target builder to match compile config to.'),
    'root_solution_revisions': Property(
        kind=List(basestring),
        help='The Chromium revisions to be tested for compile failure, '
             'ordered from older revisions to newer revisions.'),
    'requested_compile_targets': Property(
        kind=List(basestring), default=None, param_name='compile_targets',
        help='The failed compile targets, eg: browser_tests'),
}


class CompileResult(object):
  SKIPPED = 'skipped'  # No compile is needed.
  PASSED = 'passed'  # Compile passed.
  FAILED = 'failed'  # Compile failed.


def _run_compile_at_revision(api, target_mastername, target_buildername,
                             revision, compile_targets):
  with api.step.nest('test %s' % str(revision)):
    # Checkout code at the given revision to recompile.
    bot_update_step, master_dict, test_spec = \
        api.chromium_tests.prepare_checkout(
            target_mastername,
            target_buildername,
            root_solution_revision=revision)

    # TODO(http://crbug.com/560991): if compile targets are provided, check
    # whether they exist and then use analyze to compile the impacted ones by
    # the given revision.
    compile_targets = sorted(set(compile_targets or []))
    if not compile_targets:
      compile_targets, _ = api.chromium_tests.get_compile_targets_and_tests(
            target_mastername,
            target_buildername,
            master_dict,
            test_spec,
            override_bot_type='builder_tester')

    try:
      api.chromium_tests.compile_specific_targets(
          target_mastername,
          target_buildername,
          bot_update_step,
          master_dict,
          compile_targets,
          tests_including_triggered=[],
          mb_mastername=target_mastername,
          mb_buildername=target_buildername,
          override_bot_type='builder_tester')
      return CompileResult.PASSED
    except api.step.InfraFailure:
      raise
    except api.step.StepFailure:
      return CompileResult.FAILED


def RunSteps(api, target_mastername, target_buildername,
             root_solution_revisions, requested_compile_targets):
  api.chromium_tests.configure_build(
      target_mastername, target_buildername, override_bot_type='builder_tester')

  results = []
  try:
    for current_revision in root_solution_revisions:
      compile_result = _run_compile_at_revision(
          api, target_mastername, target_buildername,
          current_revision, requested_compile_targets)

      results.append([current_revision, compile_result])
      if compile_result == CompileResult.FAILED:
        # TODO(http://crbug.com/560991): if compile targets are specified,
        # compile may fail because those targets are added in a later revision.
        break # Found the culprit, no need to check later revisions.
  finally:
    # Report the result.
    # TODO(http://crbug.com/563807): use api.python.succeeding_step instead.
    step_result = api.python.inline(
        'report', 'import sys; sys.exit(0)', add_python_log=False)
    if (not requested_compile_targets and
        results and results[-1][1] == CompileResult.FAILED):
      step_result.presentation.step_text = '<br/>Culprit: %s' % results[-1][0]
    step_result.presentation.logs.setdefault('result', []).append(
        json.dumps(results, indent=2))

    # Set the result as a build property too, so that it will be reported back
    # to Buildbucket and Findit will pull from there instead of buildbot master.
    step_result.presentation.properties['result'] = results

  return results


def GenTests(api):
  def props(compile_targets=None):
    properties = {
        'mastername': 'tryserver.chromium.linux',
        'buildername': 'linux_variable',
        'slavename': 'build1-a1',
        'buildnumber': '1',
        'target_mastername': 'chromium.linux',
        'target_buildername': 'Linux Builder',
        'root_solution_revisions': ['r1'],
    }
    if compile_targets:
      properties['compile_targets'] = compile_targets
    return api.properties(**properties)

  yield (
      api.test('compile_specified_targets') +
      props(compile_targets=['target_name'])
  )

  yield (
      api.test('compile_default_targets') +
      props() +
      api.override_step_data('test r1.read test spec',
                             api.json.output({
                                'Linux Builder': {
                                   'additional_compile_targets': [
                                       'base_unittests',
                                   ],
                                }
                             }))
  )

  yield (
      api.test('compile_succeeded') +
      props() +
      api.override_step_data('test r1.compile', retcode=1)
  )

  yield (
      api.test('compile_failed') +
      props() +
      api.override_step_data('test r1.compile', retcode=1)
  )

  yield (
      api.test('failed_compile_upon_infra_failure') +
      props(compile_targets=['target_name']) +
      api.override_step_data(
          'test r1.compile',
          api.json.output({
              'notice': [
                  {
                      'infra_status': {
                          'ping_status_code': 408,
                      },
                  },
              ],
          }),
          retcode=1)
  )
