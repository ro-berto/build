# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import collections
import json

DEPS = [
    'auto_bisect',
    'properties',
    'test_utils',
    'chromium_tests',
    'raw_io',
]

AVAILABLE_BOTS = 1 # Change this for n-secting instead of bi-.

def GenSteps(api):
  _ensure_checkout(api)
  # HORRIBLE hack to get buildbot web ui to let us pass stuff as properties
  bisect_config_b32_string = api.properties.get('bcb32')
  if bisect_config_b32_string is not None:
    bisect_config = bisect_config_b32_string.replace('0', '=')
    bisect_config = base64.b32decode(bisect_config)
    bisect_config = json.loads(bisect_config)
  else:
    bisect_config = api.properties.get('bisect_config')
  assert isinstance(bisect_config, collections.Mapping)
  bisector = api.auto_bisect.create_bisector(bisect_config)
  _gather_reference_range(bisector)
  _ensure_checkout(api)
  if (not bisector.failed and bisector.check_improvement_direction() and
      bisector.check_regression_confidence()):
    _bisect_main_loop(bisector)
  else: #pragma: no cover
    bisector.bisect_over = True
  bisector.print_result()


def GenTests(api):
  basic_test = api.test('basic')
  encoded_config_test = api.test('encoded_config_test')
  basic_test += api.properties.generic(mastername='tryserver.chromium.perf',
                                       buildername='linux_perf_bisect_builder')
  encoded_config_test += api.properties.generic(
      mastername='tryserver.chromium.perf',
      buildername='linux_perf_bisect_builder')
  bisect_config = {
      'test_type': 'perf',
      'command': 'tools/perf/run_benchmark -v '
                  '--browser=release page_cycler.intl_ar_fa_he',
      'good_revision': '306475',
      'bad_revision': 'src@a6298e4afedbf2cd461755ea6f45b0ad64222222',
      'metric': 'warm_times/page_load_time',
      'repeat_count': '2',
      'max_time_minutes': '5',
      'truncate_percent': '25',
      'bug_id': '425582',
      'gs_bucket': 'chrome-perf',
      'builder_host': 'master4.golo.chromium.org',
      'builder_port': '8341',
      'dummy_regression_confidence': '95',
      'poll_sleep': 0,
      'dummy_builds': True,
  }
  basic_test += api.properties(bisect_config=bisect_config)
  encoded_config_test += api.properties(bcb32=base64.b32encode(json.dumps(
      bisect_config)).replace('=', '0'))
  # This data represents fake results for a basic scenario, the items in it are
  # passed to the `_gen_step_data_for_revision` that patches the necessary steps
  # with step_data instances.
  test_data = [
      {
          'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
           'commit_pos': '306478',
           'test_results': {'results':{
               'mean': 20,
               'std_err': 1,
               'values': [19, 20, 21],
           }}
      },
      {
          'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
           'commit_pos': '306477',
           'test_results': {'results':{
               'mean': 15,
               'std_err': 1,
               'values': [14, 15, 16],
           }}
      },
      {
          'hash': 'fc6dfc7ff5b1073408499478969261b826441144',
          'commit_pos': '306476',
           'test_results': {'results':{
               'mean': 70,
               'std_err': 2,
               'values': [68, 70, 72],
           }}
      },
      {
          'hash': 'e28dc0d49c331def2a3bbf3ddd0096eb51551155',
          'commit_pos': '306475',
           'test_results': {'results':{
               'mean': 80,
               'std_err': 10,
               'values': [70, 70, 80, 90, 90],
           }}
      },
  ]

  for revision_data in test_data:
    for step_data in _get_step_data_for_revision(api, revision_data):
      basic_test += step_data
      encoded_config_test += step_data

  yield basic_test
  yield encoded_config_test



def _get_step_data_for_revision(api, revision_data):
  """Generator that produces step patches for fake results."""
  commit_pos = revision_data['commit_pos']
  commit_hash = revision_data['hash']
  test_results = revision_data['test_results']

  step_name ='resolving commit_pos ' + commit_pos
  yield api.step_data(step_name, stdout=api.raw_io.output(commit_hash))

  step_name ='resolving hash ' + commit_hash
  commit_pos_str = 'refs/heads/master@{#%s}' % commit_pos
  yield api.step_data(step_name, stdout=api.raw_io.output(commit_pos_str))

  step_name ='gsutil Get test results for build ' + commit_hash
  yield api.step_data(step_name, stdout=api.raw_io.output(json.dumps(
      test_results)))

  step_name = 'Get test status for build ' + commit_hash
  yield api.step_data(step_name, stdout=api.raw_io.output('Complete'))

  step_name ='gsutil Get test status url for build ' + commit_hash
  yield api.step_data(step_name, stdout=api.raw_io.output('dummy/url'))


def _ensure_checkout(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  api.chromium_tests.sync_and_configure_build(mastername, buildername)


def _gather_reference_range(bisector):
  bisector.good_rev.start_job()
  bisector.bad_rev.start_job()
  bisector.wait_for_all([bisector.good_rev, bisector.bad_rev])


def _bisect_main_loop(bisector):
  """This is the main bisect loop.

  It gets an evenly distributed number of revisions in the candidate range,
  then it starts them in parallel and waits for them to finish.
  """
  while not bisector.bisect_over:
    revisions_to_check = bisector.get_revisions_to_eval(AVAILABLE_BOTS)
    #TODO: Add a test case to remove this pragma
    if not revisions_to_check: #pragma: no cover
      bisector.bisect_over = True
      break
    for r in revisions_to_check:
      r.start_job()
    _wait_for_revisions(bisector, revisions_to_check)


def _wait_for_revisions(bisector, revisions_to_check):
  """Wait for possibly multiple revision evaluations.

  Waits for the first of such revisions to finish, it then checks if any of the
  other revisions in progress has become superfluous and has them aborted.

  If such revision completes the bisect process it sets the flag so that the
  main loop stops.
  """
  while revisions_to_check:
    completed_revision = bisector.wait_for_any(revisions_to_check)
    revisions_to_check.remove(completed_revision)
    if not completed_revision.aborted:
      if bisector.check_bisect_finished(completed_revision):
        bisector.bisect_over = True
      bisector.abort_unnecessary_jobs()
