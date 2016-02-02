# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine.config import List
from recipe_engine.config import Single
from recipe_engine.recipe_api import Property


DEPS = [
    'chromium',
    'chromium_tests',
    'findit',
    'depot_tools/gclient',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]


PROPERTIES = {
    'target_mastername': Property(
        kind=str, help='The target master to match compile config to.'),
    'target_buildername': Property(
        kind=str, help='The target builder to match compile config to.'),
    'good_revision': Property(
        kind=str, help='The last known good chromium revision.'),
    'bad_revision': Property(
        kind=str, help='The first known bad chromium revision.'),
    'requested_compile_targets': Property(
        kind=List(basestring), default=None, param_name='compile_targets',
        help='The failed compile targets, eg: browser_tests'),
    'use_analyze': Property(
        kind=Single(bool, empty_val=False, required=False), default=True,
        help='Use analyze to filter out affected targets.'),
}


class CompileResult(object):
  SKIPPED = 'skipped'  # No compile is needed.
  PASSED = 'passed'  # Compile passed.
  FAILED = 'failed'  # Compile failed.


def _run_compile_at_revision(api, target_mastername, target_buildername,
                             revision, compile_targets, use_analyze):
  with api.step.nest('test %s' % str(revision)):
    # Checkout code at the given revision to recompile.
    bot_config = api.chromium_tests.create_bot_config_object(
        target_mastername, target_buildername)
    bot_update_step, bot_db = api.chromium_tests.prepare_checkout(
        bot_config, root_solution_revision=revision)

    # TODO(http://crbug.com/560991): if compile targets are provided, check
    # whether they exist and then use analyze to compile the impacted ones by
    # the given revision.
    compile_targets = sorted(set(compile_targets or []))
    if not compile_targets:
      _, tests_including_triggered = api.chromium_tests.get_tests(
          bot_config, bot_db)
      compile_targets = api.chromium_tests.get_compile_targets(
          bot_config, bot_db, tests_including_triggered)

      if use_analyze:
        changed_files = api.findit.files_changed_by_revision(revision)

        _, compile_targets = api.chromium_tests.analyze(
            changed_files,
            test_targets=[],
            additional_compile_targets=compile_targets,
            config_file_name='trybot_analyze_config.json',
            mb_mastername=target_mastername,
            mb_buildername=target_buildername,
            additional_names=None)

        if not compile_targets:
          # No compile target is impacted by the given revision.
          return CompileResult.SKIPPED

    try:
      api.chromium_tests.compile_specific_targets(
          bot_config,
          bot_update_step,
          bot_db,
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
             good_revision, bad_revision,
             requested_compile_targets, use_analyze):
  bot_config = api.chromium_tests.create_bot_config_object(
      target_mastername, target_buildername)
  api.chromium_tests.configure_build(
      bot_config, override_bot_type='builder_tester')

  # Sync to bad revision, and retrieve revisions in the regression range.
  api.chromium_tests.prepare_checkout(
      bot_config,
      root_solution_revision=bad_revision)
  revisions_to_check = api.findit.revisions_between(good_revision, bad_revision)

  compile_results = {}
  try_job_metadata = {
      'regression_range_size': len(revisions_to_check)
  }
  report = {
      'result': compile_results,
      'metadata': try_job_metadata,
  }

  try:
    for current_revision in revisions_to_check:
      last_revision = None
      compile_result = _run_compile_at_revision(
          api, target_mastername, target_buildername,
          current_revision, requested_compile_targets, use_analyze)

      compile_results[current_revision] = compile_result
      last_revision = current_revision
      if compile_result == CompileResult.FAILED:
        # TODO(http://crbug.com/560991): if compile targets are specified,
        # compile may fail because those targets are added in a later revision.
        break  # Found the culprit, no need to check later revisions.
  finally:
    # Report the result.
    # TODO(http://crbug.com/563807): use api.python.succeeding_step instead.
    step_result = api.python.inline(
        'report', 'import sys; sys.exit(0)', add_python_log=False)

    if (not requested_compile_targets and
        compile_results and
        last_revision and
        compile_results.get(last_revision) == CompileResult.FAILED):
      step_result.presentation.step_text = '<br/>Culprit: %s' % last_revision

    step_result.presentation.logs.setdefault('result', []).append(
        json.dumps(report, indent=2))

    # Set the result as a build property too, so that it will be reported back
    # to Buildbucket and Findit will pull from there instead of buildbot master.
    step_result.presentation.properties['result'] = report

  return report


def GenTests(api):
  def props(compile_targets=None, use_analyze=False):
    properties = {
        'mastername': 'tryserver.chromium.linux',
        'buildername': 'linux_variable',
        'slavename': 'build1-a1',
        'buildnumber': '1',
        'target_mastername': 'chromium.linux',
        'target_buildername': 'Linux Builder',
        'good_revision': 'r0',
        'bad_revision': 'r1',
        'use_analyze': use_analyze,
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

  yield (
      api.test('compile_skipped') +
      props(use_analyze=True) +
      api.override_step_data(
          'test r1.analyze',
          api.json.output({
              'status': 'No dependencies',
              'compile_targets': [],
              'test_targets': [],
          })
      )
  )

  yield (
      api.test('compile_affected_targets_only') +
      props(use_analyze=True) +
      api.override_step_data('test r1.read test spec',
                             api.json.output({
                                 'Linux Builder': {
                                     'additional_compile_targets': [
                                         'a', 'a_run',
                                         'b', 'b_run',
                                     ],
                                 }
                             })) +
      api.override_step_data(
          'test r1.analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['a', 'a_run'],
              'test_targets': ['a', 'a_run'],
          })
      )
  )
