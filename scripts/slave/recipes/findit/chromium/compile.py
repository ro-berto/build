# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine.config import List
from recipe_engine.config import Single
from recipe_engine.recipe_api import Property


DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'filter',
    'findit',
    'depot_tools/gclient',
    'depot_tools/git',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
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
    'compile_targets': Property(
        kind=List(basestring), default=None,
        help='The failed compile targets, eg: browser_tests, '
             'obj/path/to/source.o, gen/path/to/generated.cc, etc.'),
    'buildbucket': Property(
        default=None,
        help='The buildbucket property in which we can find build id. '
             'We need to use build id to get compile_targets.'),
    'use_analyze': Property(
        kind=Single(bool, empty_val=False, required=False), default=True,
        help='Use analyze to filter out affected targets.'),
    'suspected_revisions': Property(
        kind=List(basestring), default=[],
        help='A list of suspected revisions from heuristic analysis.'),
    'use_bisect': Property(
        kind=Single(bool, empty_val=False, required=False), default=True,
        help='Use bisect to skip more revisions. '
             'Effective only when compile_targets is given.'),
    'compile_on_good_revision': Property(
        kind=Single(bool, empty_val=False, required=False), default=True,
        help='Run compile on good revision as well if the first revision '
             'in range is the suspected culprit.'),
}


class CompileResult(object):
  SKIPPED = 'skipped'  # No compile is needed.
  PASSED = 'passed'  # Compile passed.
  FAILED = 'failed'  # Compile failed.
  INFRA_FAILED = 'infra_failed'  # Infra failed.


def _run_compile_at_revision(api, target_mastername, target_buildername,
                             revision, compile_targets, use_analyze):
  with api.step.nest('test %s' % str(revision)):
    # Checkout code at the given revision to recompile.
    bot_config = api.chromium_tests.create_bot_config_object(
        target_mastername, target_buildername)
    bot_update_step, bot_db = api.chromium_tests.prepare_checkout(
        bot_config, root_solution_revision=revision)

    compile_targets = sorted(set(compile_targets or []))
    if not compile_targets:
      # If compile targets are not specified, retrieve them from the build spec.
      _, tests_including_triggered = api.chromium_tests.get_tests(
          bot_config, bot_db)
      compile_targets = api.chromium_tests.get_compile_targets(
          bot_config, bot_db, tests_including_triggered)

      # Use dependency "analyze" to filter out those that are not impacted by
      # the given revision. This is to reduce the number of targets to be
      # compiled.
      if use_analyze:
        changed_files = api.findit.files_changed_by_revision(revision)

        _, compile_targets = api.filter.analyze(
            changed_files,
            test_targets=[],
            additional_compile_targets=compile_targets,
            config_file_name='trybot_analyze_config.json',
            mb_mastername=target_mastername,
            mb_buildername=target_buildername,
            additional_names=None)
    else:
      # Use ninja to filter out none-existing targets.
      compile_targets = api.findit.existing_targets(
          compile_targets, target_mastername, target_buildername)

    if not compile_targets:
      # No compile target exists, or is impacted by the given revision.
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


def _is_flaky_compile(compile_result, revision_being_checked, last_revision):
  # If compile on the last revision in range passed, the original build should
  # succeed as well, thus the compile failure in original build is flaky.
  return (compile_result == CompileResult.PASSED and
          revision_being_checked == last_revision)


def RunSteps(api, target_mastername, target_buildername,
             good_revision, bad_revision, compile_targets,
             buildbucket, use_analyze, suspected_revisions, use_bisect,
             compile_on_good_revision):
  if not compile_targets:
    # compile_targets could be saved in build parameter.

    # If the recipe is run by swarmbucket, the property 'buildbucket' will be
    # a dict instead of a string containing json.
    if isinstance(buildbucket, dict):
      buildbucket_json = buildbucket
    else:
      buildbucket_json = json.loads(buildbucket)
    build_id = buildbucket_json['build']['id']
    get_build_result = api.buildbucket.get_build(build_id)
    compile_targets = json.loads(
        get_build_result.stdout['build']['parameters_json']).get(
            'additional_build_parameters', {}).get('compile_targets')

  bot_config = api.chromium_tests.create_bot_config_object(
      target_mastername, target_buildername)
  api.chromium_tests.configure_build(
      bot_config, override_bot_type='builder_tester')

  api.chromium.apply_config('goma_failfast')

  (checked_out_revision, cached_revision) = api.findit.record_previous_revision(
      api, bot_config)
  # Sync to bad revision, and retrieve revisions in the regression range.
  api.chromium_tests.prepare_checkout(
      bot_config,
      root_solution_revision=bad_revision)

  # Retrieve revisions in the regression range. The returned revisions are in
  # order from oldest to newest.
  all_revisions = api.findit.revisions_between(good_revision, bad_revision)

  # If suspected revisions are provided, divide the entire regression range into
  # a list of smaller sub-ranges. Because only a failure immediately following a
  # pass could identify the culprit, we rerun compile at the revision right
  # before a suspected revision and then at the suspected revision itself. So a
  # sub-range starts at the revision right before a suspected revision.
  #
  # Normally, heuristic analysis provides only 1 suspected revision and there
  # will be 2 sub-ranges. Example (previous build cycle passed at r0):
  #   Entire regression range: [r1, r2, r3, r4, ..., r10]
  #   Suspected revisions: [r5]
  # Then the sub-ranges are:
  #   sub-range1: r4 and [r5, r6, ..., r10]
  #   sub-range2: None and [r1, r2, r3]
  # In this example, compile is run at r4 first, and there will be a few cases:
  #   1) if r4 passes, the culprit is in [r5, r6, ..., r10]. Compile should be
  #      rerun in order from r5 to r10.
  #      1.1) if a failure occurs at rN (5<=N<=10), rN is the actual culprit
  #           because it is the first failure after a series of pass.
  #      1.2) if no failure occurs, the compile failure is a flaky one. This
  #           sometimes happens and the compile log shows no error while the
  #           step ran into an exception.
  #   2) if r4 fails, the culprit is either r4 itself or one of [r1, r2, r3].
  #      Compile should be rerun in order from r1 to r3. No compile is run at
  #      r0, because it is the last known good revision.
  #      2.1) if a failure occurs at rN (1<=N<=3), rN is the actual culprit.
  #      2.2) if no failure occurs, r4 is the actual culprit instead.
  #
  # Occasionally, heuristic analysis provides 2+ suspected revisions (e.g. there
  # are conflicting commits). In this case, there will be 3+ sub-ranges.
  # For the above example, if the suspected revisions are [r5, r8], there will
  # be three sub-ranges:
  #   sub-range1: r7 and [r8, r9, r10]
  #   sub-range2: r4 and [r5, r6]
  #   sub-range3: None and [r1, r2, r3]
  # Sub-ranges with newer revisions are tested first (sub-range1 -> sub-range2
  # -> sub-range3), because it is more likely that a newer revision is the
  # beginning of the compile breakage.
  suspected_revision_index = [
      all_revisions.index(r)
      for r in set(suspected_revisions) if r in all_revisions]
  if suspected_revision_index:
    # For consecutive suspected revisions, make them all in the same sub-range
    # by removing the newer revisions, but keep the oldest one.
    suspected_revision_index = [i for i in suspected_revision_index
                                if i - 1 not in suspected_revision_index]

    sub_ranges = []
    remaining_revisions = all_revisions[:]
    for index in sorted(suspected_revision_index, reverse=True):
      if index > 0:
        # try job will not run linearly, sets use_analyze to False.
        use_analyze = False
        sub_ranges.append(remaining_revisions[index - 1:])
        remaining_revisions = remaining_revisions[:index - 1]
    # None is a placeholder for the last known good revision.
    sub_ranges.append([None] + remaining_revisions)
  else:
    # Treat the entire regression range as a single sub-range.
    # None is a placeholder for the last known good revision.
    sub_ranges = [[None] + all_revisions]

  compile_results = {}
  try_job_metadata = {
      'regression_range_size': len(all_revisions),
      'sub_ranges': sub_ranges[:],
      'use_bisect': use_bisect,
  }
  report = {
      'result': compile_results,
      'metadata': try_job_metadata,
      'previously_checked_out_revision': checked_out_revision,
      'previously_cached_revision': cached_revision,
  }

  culprit_candidate = None
  revision_being_checked = None
  found = False
  flaky_compile = False
  try:
    while not found and sub_ranges and not flaky_compile:
      # Sub-ranges with newer revisions are tested first.
      revision_before_suspect = sub_ranges[0][0]
      remaining_revisions = sub_ranges[0][1:]
      sub_ranges.pop(0)

      if revision_before_suspect is not None:
        revision_being_checked = revision_before_suspect
        compile_result = _run_compile_at_revision(
            api, target_mastername, target_buildername,
            revision_being_checked, compile_targets, use_analyze)
        compile_results[revision_being_checked] = compile_result
        if compile_result == CompileResult.FAILED:
          # The first revision of this sub-range already failed, thus either it
          # is the culprit or the culprit is in a sub-range with older
          # revisions.
          culprit_candidate = revision_being_checked
          continue

      # If the first revision in the current sub-range passed, the culprit is
      # either in the remaining revisions of the current sub-range or is the
      # first revision of last checked sub-range.

      if compile_targets and use_bisect:
        # Could bisect only when failed compile targets are given.
        # Could not use analyze if bisect.
        use_analyze = False
        while remaining_revisions:
          if remaining_revisions[0] in suspected_revisions:
            # In this case, we test the suspected revision before real bisect.
            index = 0
          else:
            index = len(remaining_revisions) / 2
          revision_being_checked = remaining_revisions[index]
          compile_result = _run_compile_at_revision(
              api, target_mastername, target_buildername,
              revision_being_checked, compile_targets, use_analyze)
          compile_results[revision_being_checked] = compile_result
          if compile_result == CompileResult.FAILED:
            # This failed revision is the new candidate to suspect.
            culprit_candidate = revision_being_checked
            remaining_revisions = remaining_revisions[:index]
          elif _is_flaky_compile(
              compile_result, revision_being_checked, all_revisions[-1]):
            # The last revision in range passed on compile, bail out.
            flaky_compile = True
            break
          else:  # Compile passed, or skipped for non-existent compile targets.
            # TODO(http://crbug.com/610526): If compile failures is due to
            # "unknown targets", bisect won't work due to skipped compile.
            remaining_revisions = remaining_revisions[index + 1:]
      else:
        for revision in remaining_revisions:
          if all_revisions.index(revision) == 0:
            # Make sure compile the first revision in range to reduce
            # false positives.
            use_analyze_for_this_revision = False
          else:
            use_analyze_for_this_revision = use_analyze
          revision_being_checked = revision
          compile_result = _run_compile_at_revision(
              api, target_mastername, target_buildername,
              revision, compile_targets, use_analyze_for_this_revision)
          compile_results[revision] = compile_result
          if compile_result == CompileResult.FAILED:
            # First failure after a series of pass.
            culprit_candidate = revision
            break
          elif _is_flaky_compile(
              compile_result, revision_being_checked, all_revisions[-1]):
            # The last revision in range passed on compile, bail out.
            flaky_compile = True
            break

      if culprit_candidate is not None:
        # If linear or binary search finished without exceptions, and the
        # suspected revision was set for a failure of compile rerun, then the
        # culprit is found. If an exception occurs, the suspected revision might
        # not be correct even it is set.
        if compile_on_good_revision and culprit_candidate == all_revisions[0]:
          # The culprit is the first one in the regression range, we need to run
          # compile on last good to reduce false positives.
          compile_result = _run_compile_at_revision(
              api, target_mastername, target_buildername,
              good_revision, compile_targets, use_analyze)
          compile_results[good_revision] = compile_result
          # If compile failed on last good revision, the original failure could
          # have been a flaky compile.
          found = compile_result != CompileResult.FAILED
        else:
          found = True

  except api.step.InfraFailure:
    compile_results[revision_being_checked] = CompileResult.INFRA_FAILED
    report['metadata']['infra_failure'] = True
    raise
  finally:
    report['last_checked_out_revision'] = api.properties.get('got_revision')
    if found:
      report['culprit'] = culprit_candidate

    # Report the result.
    step_result = api.python.succeeding_step(
        'report', [json.dumps(report, indent=2)], as_log='report')

    if found:
      step_result.presentation.step_text = (
          '<br/>Culprit: <a href="https://crrev.com/%s">%s</a>' % (
              culprit_candidate, culprit_candidate))

  return report


def GenTests(api):
  def props(compile_targets=None, use_analyze=False,
            good_revision=None, bad_revision=None,
            suspected_revisions=None, use_bisect=False, buildbucket=None):
    properties = {
        'path_config': 'kitchen',
        'mastername': 'tryserver.chromium.linux',
        'buildername': 'linux_variable',
        'bot_id': 'build1-a1',
        'buildnumber': '1',
        'target_mastername': 'chromium.linux',
        'target_buildername': 'Linux Builder',
        'good_revision': good_revision or 'r0',
        'bad_revision': bad_revision or 'r1',
        'use_analyze': use_analyze,
        'use_bisect': use_bisect,
    }
    if compile_targets:
      properties['compile_targets'] = compile_targets
    if suspected_revisions:
      properties['suspected_revisions'] = suspected_revisions
    if buildbucket:
      properties['buildbucket'] = buildbucket
    return api.properties(**properties) + api.platform.name('linux')

  def simulated_buildbucket_output(additional_build_parameters):
    buildbucket_output = {
        'build':{
          'parameters_json': json.dumps(additional_build_parameters)
        }
    }

    return api.buildbucket.step_data(
        'buildbucket.get',
        stdout=api.raw_io.output_text(json.dumps(buildbucket_output)))

  def base_unittests_additional_compile_target():
    return api.override_step_data(
        'test r1.read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Builder': {
                'additional_compile_targets': [
                    'base_unittests',
                ],
            }
        }))

  yield (
      api.test('compile_specified_targets') +
      props(compile_targets=['target_name']) +
      api.override_step_data('test r1.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             }))
  )

  yield (
      api.test('compile_specified_targets_from_parameter') +
      props(buildbucket=json.dumps({'build': {'id': 'id1'}})) +
      simulated_buildbucket_output({
          'additional_build_parameters': {
              'compile_targets': ['target_name']
      }}) +
      api.override_step_data('test r1.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             }))
  )

  yield (
      api.test('compile_none_existing_targets') +
      props(compile_targets=['gen/a/b/source.cc']) +
      api.override_step_data('test r1.check_targets',
                             api.json.output({
                                 'found': [],
                                 'not_found': ['gen/a/b/source.cc'],
                             }))
  )


  yield (
      api.test('compile_default_targets') +
      props(buildbucket=json.dumps({'build': {'id': 'id1'}})) +
      simulated_buildbucket_output({
          'additional_build_parameters': {
              'compile_targets': None
      }}) +
      api.override_step_data('test r1.read test spec (chromium.linux.json)',
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
      props(buildbucket=json.dumps({'build': {'id': 'id1'}})) +
      simulated_buildbucket_output({}) +
      base_unittests_additional_compile_target() +
      api.override_step_data('test r1.compile', retcode=0)
  )

  yield (
      api.test('compile_succeeded_non_json_buildbucket') +
      props(buildbucket={'build': {'id': 'id1'}}) +
      simulated_buildbucket_output({}) +
      base_unittests_additional_compile_target() +
      api.override_step_data('test r1.compile', retcode=0)
  )

  yield (
      api.test('compile_failed') +
      props(buildbucket=json.dumps({'build': {'id': 'id1'}})) +
      simulated_buildbucket_output({}) +
      base_unittests_additional_compile_target() +
      api.override_step_data('test r1.compile', retcode=1)
  )

  yield (
      api.test('failed_compile_upon_infra_failure_goma_setup_failure') +
      props(compile_targets=['target_name']) +
      api.override_step_data('test r1.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data(
          'test r1.preprocess_for_goma.start_goma', retcode=1) +
      api.step_data(
          'test r1.preprocess_for_goma.goma_jsonstatus',
          api.json.output(
              data={
                  'notice': [
                      {
                          "compile_error": "COMPILER_PROXY_UNREACHABLE",
                      },
                  ],
              }))
  )

  yield (
      api.test('failed_compile_upon_infra_failure_goma_ping_failure') +
      props(compile_targets=['target_name']) +
      api.override_step_data('test r1.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data(
          'test r1.preprocess_for_goma.start_goma', retcode=1) +
      api.step_data(
          'test r1.preprocess_for_goma.goma_jsonstatus',
          api.json.output(
              data={
                  'notice': [
                      {
                          'infra_status': {
                              'ping_status_code': 408,
                          },
                      },
                  ],
              }))
  )

  yield (
      api.test('failed_compile_upon_infra_failure_goma_build_error') +
      props(compile_targets=['target_name']) +
      api.override_step_data('test r1.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data(
          'test r1.compile', retcode=1) +
      api.step_data(
          'test r1.postprocess_for_goma.goma_jsonstatus',
          api.json.output(
              data={
                  'notice': [
                      {
                          'infra_status': {
                              'ping_status_code': 200,
                              'num_user_error': 1,
                          },
                      },
                  ],
              }))
  )

  yield (
      api.test('compile_skipped') +
      props(use_analyze=True,
            buildbucket=json.dumps({'build': {'id': 'id1'}}),
            good_revision='r0',
            bad_revision='r2') +
      simulated_buildbucket_output({}) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 3))))) +
      api.path.exists(api.path['builder_cache'].join('linux','src')) +
      api.override_step_data('record previously checked-out revision',
                             api.raw_io.output('')) +
      api.override_step_data('record previously cached revision',
                             api.raw_io.output('')) +
      api.override_step_data(
          'test r2.analyze',
          api.json.output({
              'status': 'No dependencies',
              'compile_targets': [],
              'test_targets': [],
          })
      )
  )

  yield (
      api.test('previous_revision_directory_does_not_exist') +
      props(use_analyze=True,
            buildbucket=json.dumps({'build': {'id': 'id1'}}),
            good_revision='r0',
            bad_revision='r2') +
      simulated_buildbucket_output({}) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 3))))) +
      api.override_step_data(
          'test r2.analyze',
          api.json.output({
              'status': 'No dependencies',
              'compile_targets': [],
              'test_targets': [],
          })
      )
  )

  yield (
      api.test('previous_revision_error_code') +
      props(use_analyze=True,
            buildbucket=json.dumps({'build': {'id': 'id1'}}),
            good_revision='r0',
            bad_revision='r2') +
      simulated_buildbucket_output({}) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 3))))) +
      api.path.exists(api.path['builder_cache'].join('linux','src')) +
      api.override_step_data('record previously checked-out revision',
                             api.raw_io.output('SegmentationFault'),
                             retcode=255) +
      api.override_step_data('record previously cached revision',
                             api.raw_io.output('SegmentationFault'),
                             retcode=255) +
      api.override_step_data(
          'test r2.analyze',
          api.json.output({
              'status': 'No dependencies',
              'compile_targets': [],
              'test_targets': [],
          })
      )
  )
  yield (
      api.test('previous_revision_bad_output') +
      props(use_analyze=True,
            buildbucket=json.dumps({'build': {'id': 'id1'}}),
            good_revision='r0',
            bad_revision='r2') +
      simulated_buildbucket_output({}) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 3))))) +
      api.path.exists(api.path['builder_cache'].join('linux','src')) +
      api.override_step_data('record previously checked-out revision',
                             api.raw_io.output('SegmentationFault')) +
      api.override_step_data('record previously cached revision',
                             api.raw_io.output('SegmentationFault')) +
      api.override_step_data(
          'test r2.analyze',
          api.json.output({
              'status': 'No dependencies',
              'compile_targets': [],
              'test_targets': [],
          })
      )
  )
  yield (
      api.test('previous_revision_valid') +
      props(use_analyze=True,
            buildbucket=json.dumps({'build': {'id': 'id1'}}),
            good_revision='r0',
            bad_revision='r2') +
      simulated_buildbucket_output({}) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 3))))) +
      api.path.exists(api.path['builder_cache'].join('linux','src')) +
      api.override_step_data(
          'test r2.analyze',
          api.json.output({
              'status': 'No dependencies',
              'compile_targets': [],
              'test_targets': [],
          })
      )
  )

  yield (
      api.test('compile_affected_targets_only') +
      props(use_analyze=True,
            buildbucket=json.dumps({'build': {'id': 'id1'}}),
            good_revision='r0',
            bad_revision='r2') +
      simulated_buildbucket_output({}) +
      api.override_step_data(
        'git commits in range',
        api.raw_io.stream_output(
          '\n'.join('r%d' % i for i in reversed(range(1, 3))))) +
      api.override_step_data('test r2.read test spec (chromium.linux.json)',
                             api.json.output({
                                 'Linux Builder': {
                                     'additional_compile_targets': [
                                         'a', 'a_run',
                                         'b', 'b_run',
                                     ],
                                 }
                             })) +
      api.override_step_data(
          'test r2.analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['a', 'a_run'],
              'test_targets': ['a', 'a_run'],
          })
      )
  )

  # Entire regression range: (r1, r6]
  # Suspected_revisions: [r4]
  # Expected smaller ranges: [r3, [r4, r5, r6]], [None, [r2]]
  # Actual culprit: r4
  # Should only run compile on r3, and then r4.
  yield (
      api.test('find_culprit_in_middle_of_a_sub_range') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r6',
            suspected_revisions=['r4']) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 7))))) +
      api.override_step_data('test r3.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r4.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r4.compile', retcode=1)
  )

  # Entire regression range: (r1, r6]
  # Suspected_revisions: [r4, r5]
  # Expected smaller ranges: [r3, [r4, r5, r6]], [None, [r2]]
  # Actual culprit: r3
  # Should only run compile on r3, and then r2.
  yield (
      api.test('find_culprit_at_first_revision_of_a_sub_range') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r6',
            suspected_revisions=['r4']) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 7))))) +
      api.override_step_data('test r3.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r3.compile', retcode=1) +
      api.override_step_data('test r2.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             }))
  )

  # Entire regression range: (r1, r10]
  # Suspected_revisions: [r4, r8]
  # Expected smaller ranges:
  #     [r7, [r8, r9, r10]], [r3, [r4, r5, r6]], [None, [r2]]
  # Actual culprit: r4
  # Should only run compile on r7(failed), then r3(pass) and r4(failed).
  yield (
      api.test('find_culprit_in_second_sub_range') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r6',
            suspected_revisions=['r4', 'r8']) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 11))))) +
      api.override_step_data('test r7.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r7.compile', retcode=1) +
      api.override_step_data('test r3.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r4.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r4.compile', retcode=1)
  )

  # Entire regression range: (r1, r5]
  # Suspected_revisions: [r2]
  # Expected smaller ranges:
  #     [None, r2, r3, r4, r5]
  # Actual culprit: r2
  # Should only run compile on r2(failed).
  yield (
      api.test('find_culprit_as_first_revision_of_entire_range') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r5',
            suspected_revisions=['r2']) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 6))))) +
      api.override_step_data('test r1.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r1.compile', retcode=0) +
      api.override_step_data('test r2.check_targets',
                             api.json.output({
                               'found': ['target_name'],
                               'not_found': [],
                             })) +
      api.override_step_data('test r2.compile', retcode=1)
  )

  # Entire regression range: (r1, r5]
  # Suspected_revisions: [r5]
  # Expected smaller ranges:
  #     [None, r2, r3], [r4, r5]
  # Compile on r5 passed, should bail out right away.
  yield (
      api.test('last_revision_pass_not_bisect') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r5',
            suspected_revisions=['r5']) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 6))))) +
      api.override_step_data('test r4.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r4.compile', retcode=0) +
      api.override_step_data('test r5.check_targets',
                             api.json.output({
                               'found': ['target_name'],
                               'not_found': [],
                             })) +
      api.override_step_data('test r5.compile', retcode=0)
  )

  # Entire regression range: (r1, r10]
  # Suspected_revisions: [r7]
  # Expected smaller ranges:
  #     [None, r2, r3, r4, r5], [r6, r7, r8, r9, r10]
  # Compile on r10 passed, should bail out right away.
  yield (
      api.test('last_revision_pass_bisect') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r10',
            suspected_revisions=['r7'],
            use_bisect=True) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 11))))) +
      api.override_step_data('test r6.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r6.compile', retcode=0) +
      api.override_step_data('test r7.check_targets',
                             api.json.output({
                               'found': ['target_name'],
                               'not_found': [],
                             })) +
      api.override_step_data('test r7.compile', retcode=0) +
      api.override_step_data('test r9.check_targets',
                             api.json.output({
                               'found': ['target_name'],
                               'not_found': [],
                             })) +
      api.override_step_data('test r9.compile', retcode=0) +
      api.override_step_data('test r10.check_targets',
                             api.json.output({
                               'found': ['target_name'],
                               'not_found': [],
                             })) +
      api.override_step_data('test r10.compile', retcode=0)
  )

  # Entire regression range: (r1, r5]
  # Suspected_revisions: [r2]
  # compile on r1 failed
  # No reliable results
  yield (
      api.test('first_revision_of_entire_range_failed_but_is_not_culprit') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r5',
            suspected_revisions=['r2']) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 6))))) +
      api.override_step_data('test r1.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r1.compile', retcode=1) +
      api.override_step_data('test r2.check_targets',
                             api.json.output({
                               'found': ['target_name'],
                               'not_found': [],
                             })) +
      api.override_step_data('test r2.compile', retcode=1)
  )

  # Entire regression range: (r1, r10]
  # Actual culprit: r5
  # Should only run compile on r6(failed), then r4(pass) and r5(failed).
  yield (
      api.test('find_culprit_using_bisect') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r10',
            use_bisect=True) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 11))))) +
      api.override_step_data('test r6.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r6.compile', retcode=1) +
      api.override_step_data('test r4.check_targets',
                             api.json.output({
                                 'found': [],
                                 'not_found': ['target_name'],
                             })) +
      api.override_step_data('test r5.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r5.compile', retcode=1)
  )

  # Entire regression range: (r1, r8]
  # Suspected_revisions: [r5]
  # Expected smaller ranges:
  #     [r4, r5, r6, r7, r8], [None, r2, r3]
  # Actual culprit: r5
  # Should only run compile on r4(pass), and r5(failed).
  yield (
      api.test('check_suspected_revision_before_bisect') +
      props(compile_targets=['target_name'],
            good_revision='r1',
            bad_revision='r8',
            suspected_revisions=['r5'],
            use_bisect=True) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(2, 9))))) +
      api.override_step_data('test r4.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r5.check_targets',
                             api.json.output({
                                 'found': ['target_name'],
                                 'not_found': [],
                             })) +
      api.override_step_data('test r5.compile', retcode=1)
  )
