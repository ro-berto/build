# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import collections
import json


def perform_bisect(api):  # pragma: no cover
  bisect_config = api.m.properties.get('bisect_config')
  assert isinstance(bisect_config, collections.Mapping)
  bisector = api.create_bisector(bisect_config)
  with api.m.step.nest('Gathering reference values'):
    _gather_reference_range(api, bisector)
  if (not bisector.failed and bisector.check_improvement_direction() and
      bisector.check_initial_confidence()):
    if bisector.check_reach_adjacent_revision(bisector.good_rev):
      # Only show this step if bisect has reached adjacent revisions.
      with api.m.step.nest(str('Check bisect finished on revision ' +
                               bisector.good_rev.revision_string)):
        if bisector.check_bisect_finished(bisector.good_rev):
          bisector.bisect_over = True
    if not bisector.bisect_over:
      _bisect_main_loop(bisector)
  else:
    bisector.bisect_over = True
  bisector.print_result_debug_info()
  bisector.print_result()


def _gather_reference_range(api, bisector):  # pragma: no cover
  bisector.good_rev.start_job()
  bisector.bad_rev.start_job()
  bisector.wait_for_all([bisector.good_rev, bisector.bad_rev])
  if bisector.good_rev.failed:
    bisector.surface_result('REF_RANGE_FAIL')
    api.m.halt('Testing the "good" revision failed')
    bisector.failed = True
  elif bisector.bad_rev.failed:
    bisector.surface_result('REF_RANGE_FAIL')
    api.m.halt('Testing the "bad" revision failed')
    bisector.failed = True
    api.m.halt('Testing the "good" revision failed')
  else:
    bisector.compute_relative_change()


def _bisect_main_loop(bisector):  # pragma: no cover
  """This is the main bisect loop.

  It gets an evenly distributed number of revisions in the candidate range,
  then it starts them in parallel and waits for them to finish.
  """
  while not bisector.bisect_over:
    # TODO(simonhatch): Refactor this since get_revision_to_eval() returns a
    # a single revision now.
    # crbug.com/546695
    revisions_to_check = bisector.get_revision_to_eval()
    # TODO: Add a test case to remove this pragma
    if not revisions_to_check:
      bisector.bisect_over = True
      break

    completed_revisions = []
    with bisector.api.m.step.nest(str('Working on revision ' +
                                      revisions_to_check[0].revision_string)):
      nest_step_result = bisector.api.m.step.active_result
      partial_results = bisector.partial_results().splitlines()
      nest_step_result.presentation.logs['Partial Results'] = partial_results
      for r in revisions_to_check:
        r.start_job()
      completed_revisions = _wait_for_revisions(bisector, revisions_to_check)

    for completed_revision in completed_revisions:
      if not bisector.check_reach_adjacent_revision(completed_revision):
        continue
      # Only show this step if bisect has reached adjacent revisions.
      with bisector.api.m.step.nest(
          str('Check bisect finished on revision ' +
              completed_revisions[0].revision_string)):
        if bisector.check_bisect_finished(completed_revision):
          bisector.bisect_over = True


def _wait_for_revisions(bisector, revisions_to_check):  # pragma: no cover
  """Wait for possibly multiple revision evaluations.

  Waits for the first of such revisions to finish, it then checks if any of the
  other revisions in progress has become superfluous and has them aborted.

  If such revision completes the bisect process it sets the flag so that the
  main loop stops.
  """
  completed_revisions = []
  while revisions_to_check:
    completed_revision = bisector.wait_for_any(revisions_to_check)
    if completed_revision in revisions_to_check:
      revisions_to_check.remove(completed_revision)
    else:
      bisector.api.m.step.active_result.presentation.status = (
          bisector.api.m.step.WARNING)
      bisector.api.m.step.active_result.presentation.logs['WARNING'] = (
          ['Tried to remove revision not in list'])
    if not (completed_revision.aborted or completed_revision.failed):
      completed_revisions.append(completed_revision)
      bisector.abort_unnecessary_jobs()
  return completed_revisions
