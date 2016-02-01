# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

DEPS = [
    'auto_bisect',
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

"""This file is a recipe demonstrating the auto_bisect recipe module.

For more information about recipes, see: https://goo.gl/xKnjz6
"""


def RunSteps(api):
  fake_checkout_path = api.path.mkdtemp('fake_checkout')
  api.path['checkout'] = fake_checkout_path
  bisector = api.auto_bisect.create_bisector(api.properties['bisect_config'])

  # Request builds and tests for initial range and wait.
  bisector.good_rev.start_job()
  bisector.bad_rev.start_job()
  bisector.wait_for_all([bisector.good_rev, bisector.bad_rev])

  if bisector.good_rev.failed or bisector.bad_rev.failed:
    return

  assert bisector.check_improvement_direction()
  assert bisector.check_initial_confidence()
  revisions_to_check = bisector.get_revision_to_eval()
  assert len(revisions_to_check) == 1
  revisions_to_check[0].start_job()
  bisector.wait_for_any(revisions_to_check)
  bisector.check_bisect_finished(revisions_to_check[0])

  # Evaluate inserted DEPS-modified revisions.
  revisions_to_check = bisector.get_revision_to_eval()
  if revisions_to_check:
    revisions_to_check[0].start_job()
    # Only added for coverage.
    revisions_to_check[0].read_deps(bisector.get_perf_tester_name())
    api.auto_bisect.query_revision_info(revisions_to_check[0].commit_hash)
  else:
    raise api.step.StepFailure('Expected revisions to check.')
  # TODO(robertocn): Add examples for the following operations:
  #  Abort unnecessary jobs
  #  Print results (may be done in a unit test)

  # Test runner for classic bisect script; calls bisect script in recipe
  # wrapper with extra_src and path_to_config to override default behavior.
  if api.properties.get('mastername'):
    # TODO(akuegel): Load the config explicitly instead of relying on the
    # builders.py entries in chromium_tests.
    mastername = api.properties.get('mastername')
    buildername = api.properties.get('buildername')
    bot_config = api.chromium_tests.create_bot_config_object(
        mastername, buildername)
    api.chromium_tests.configure_build(bot_config)
    api.chromium_tests.prepare_checkout(bot_config)
    api.auto_bisect.run_bisect_script('dummy_extra_src', '/dummy/path/')


def GenTests(api):
  dummy_gs_location = ('gs://chrome-perf/bisect-results/'
                       'a6298e4afedbf2cd461755ea6f45b0ad64222222-test.results')
  wait_for_any_output = {
      'completed': [
          {
              'type': 'gs',
              'location': dummy_gs_location
          }
      ]
  }

  basic_test = _make_test(api, _get_basic_test_data(), 'basic')
  basic_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(wait_for_any_output))
  yield basic_test

  failed_build_test = _make_test(
      api, _get_ref_range_only_test_data(), 'failed_build_test')
  failed_build_test_step_data = {
      'failed':
      [
          {
              'builder': 'linux_perf_tester',
              'job_name': 'a6298e4afedbf2cd461755ea6f45b0ad64222222-test',
              'master': 'tryserver.chromium.perf',
              'type': 'buildbot',
              'job_url': 'http://tempuri.org/log',
          }
      ],
  }
  failed_build_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(failed_build_test_step_data), retcode=1)
  yield failed_build_test

  missing_metric_test = _make_test(
      api, _get_ref_range_only_missing_metric_test_data(),
      'missing_metric_test')
  missing_metric_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(wait_for_any_output))
  yield missing_metric_test

  windows_test = _make_test(
      api, _get_basic_test_data(), 'windows_bisector', platform='windows')
  windows_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(wait_for_any_output))
  yield windows_test

  winx64_test = _make_test(
      api, _get_basic_test_data(), 'windows_x64_bisector', platform='win_x64')
  winx64_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(wait_for_any_output))
  yield winx64_test

  mac_test = _make_test(
      api, _get_basic_test_data(), 'mac_bisector', platform='mac')
  mac_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(wait_for_any_output))
  yield mac_test

  android_test = _make_test(
      api, _get_basic_test_data(), 'android_bisector', platform='android')
  android_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(wait_for_any_output))
  yield android_test

  android_arm64_test = _make_test(
      api, _get_basic_test_data(), 'android_arm64_bisector',
      platform='android_arm64')
  android_arm64_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(wait_for_any_output))
  yield android_arm64_test

  failed_data = _get_basic_test_data()
  failed_data[0].pop('DEPS')
  failed_data[1]['test_results']['results']['errors'] = ['Dummy error.']
  failed_data[1].pop('DEPS_change')
  failed_data[1].pop('DEPS')
  failed_data[1].pop('DEPS_interval')
  failed_data[0].pop('git_diff')
  failed_data[0].pop('cl_info')
  yield _make_test(api, failed_data, 'failed_test')

  yield _make_test(api, _get_reversed_basic_test_data(), 'reversed_basic')

  bad_git_hash_data = _get_basic_test_data()
  bad_git_hash_data[1]['interned_hashes'] = {'003': '12345', '002': 'Bad Hash'}

  bisect_script_test = _make_test(
      api, _get_basic_test_data(), 'basic_bisect_script')
  bisect_script_test += api.step_data(
      'Waiting for revision 314015 and 1 other revision(s). (2)',
      stdout=api.json.output(wait_for_any_output))

  bisect_script_test += api.properties(mastername='tryserver.chromium.perf',
                                       buildername='linux_perf_bisect',
                                       slavename='dummyslave')
  yield bisect_script_test


def _get_ref_range_only_test_data():
  return [
      {
          'refrange': True,
          'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
          'commit_pos': '314015',
      },
      {
          'refrange': True,
          'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
          'commit_pos': '314017',
          'test_results': {
              'results': {
                  'values': [14, 15, 16],
              },
              'retcodes': [0],
          }
      },
  ]


def _get_ref_range_only_missing_metric_test_data():
  return [
      {
          'refrange': True,
          'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
          'commit_pos': '314015',
          'test_results': {
              'results': {
                  'values': [],
              },
              'retcodes': [0],
          }
      },
      {
          'refrange': True,
          'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
          'commit_pos': '314017',
          'test_results': {
              'results': {
                  'values': [],
              },
              'retcodes': [0],
          }
      },
  ]


def _get_basic_test_data():
  return [
      {
          'refrange': True,
          'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
          'commit_pos': '314015',
          'test_results': {
              'results': {
                  'values': [19, 20, 21],
              },
              'retcodes': [0],
          },
          "DEPS": ("vars={'v8_revision': '001'};"
                   "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                   "'src/third_party/WebKit': 'webkit.git@010'}"),
          'git_diff': {
              '002': 'Dummy .diff contents 001 - 002',
              '003': 'Dummy .diff contents 001 - 003',
          },
          'cl_info': {
              'author': 'DummyAuthor',
              'email': 'dummy@nowhere.com',
              'subject': 'Some random CL',
              'date': '01/01/2015',
              'body': ('A long description for a CL.\n'
                       'Containing multiple lines'),
          },
      },
      {
          'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
          'commit_pos': '314016',
          'test_results': {
              'results': {
                  'values': [14, 15, 16],
              },
              'retcodes': [0],
          },
          'DEPS_change': 'True',
          "DEPS": ("vars={'v8_revision': '004'};"
                   "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                   "'src/third_party/WebKit': 'webkit.git@010'}"),
          'DEPS_interval': {'v8': '002 003 004'.split()},
      },
      {
          'refrange': True,
          'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
          'commit_pos': '314017',
          'test_results': {
              'results': {
                  'values': [14, 15, 16],
              },
              'retcodes': [0],
          }
      },
  ]


def _get_reversed_basic_test_data():
  return [
      {
          'refrange': True,
          'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
          'commit_pos': '314015',
          'test_results': {
              'results': {
                  'values': [19, 20, 21],
              },
              'retcodes': [0],
          },
          'cl_info': {
              'author': 'DummyAuthor',
              'email': 'dummy@nowhere.com',
              'subject': 'Some random CL',
              'date': '01/01/2015',
              'body': ('A long description for a CL.\n'
                       'Containing multiple lines'),
          },
      },
      {
          'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
          'commit_pos': '314016',
          'test_results': {
              'results': {
                  'values': [19, 20, 21],
              },
              'retcodes': [0],
          },
          "DEPS": ("vars={'v8_revision': '001'};"
                   "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                   "'src/third_party/WebKit': 'webkit.git@010'}"),
          'git_diff': {
              '002': 'Dummy .diff contents 001 - 002',
              '003': 'Dummy .diff contents 001 - 003',
          },
      },
      {
          'refrange': True,
          'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
          'commit_pos': '314017',
          'test_results': {
              'results': {
                  'values': [14, 15, 16],
              },
              'retcodes': [0],
          },
          'DEPS_change': 'True',
          "DEPS": ("vars={'v8_revision': '004'};"
                   "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                   "'src/third_party/WebKit': 'webkit.git@010'}"),
          'DEPS_interval': {'v8': '002 003 004'.split()},
      },
  ]


def _make_test(api, test_data, test_name, platform='linux'):
  basic_test = api.test(test_name)
  basic_test += _get_revision_range_step_data(api, test_data)
  for revision_data in test_data:
    for step_data in _get_step_data_for_revision(api, revision_data):
      basic_test += step_data
  if 'win_x64' in platform:
    basic_test += api.properties(bisect_config=_get_config({
        'command': ('src/tools/perf/run_benchmark -v --browser=release_x64'
                    ' smoothness.tough_scrolling_cases'),
        'recipe_tester_name': 'chromium_rel_win7_x64'}))
  elif 'win' in platform:
    basic_test += api.properties(bisect_config=_get_config(
        {'recipe_tester_name': 'chromium_rel_win7'}))
  elif 'mac' in platform:
    basic_test += api.properties(bisect_config=_get_config(
        {'recipe_tester_name': 'chromium_rel_mac'}))
  elif 'android_arm64' in platform:
    basic_test += api.properties(bisect_config=_get_config({
        'command': ('src/tools/perf/run_benchmark -v --browser=android-chromium'
                    ' smoothness.tough_scrolling_cases'),
        'recipe_tester_name': 'android-nexus9'}))
  elif 'android' in platform:
    basic_test += api.properties(bisect_config=_get_config({
        'command': ('src/tools/perf/run_benchmark -v --browser=android-chromium'
                    ' smoothness.tough_scrolling_cases'),
        'recipe_tester_name': 'android-nexus7'}))
  else:
    basic_test += api.properties(bisect_config=_get_config())
  return basic_test


def _get_revision_range_step_data(api, range_data):
  """Adds canned output for fetch_intervening_revisions.py."""
  min_rev = range_data[0]['hash']
  max_rev = range_data[-1]['hash']
  output = [[r['hash'], r['commit_pos']] for r in range_data[1:-1]]
  step_name = ('Expanding revision range.for revisions %s:%s' %
               (min_rev, max_rev))
  return api.step_data(step_name, stdout=api.json.output(output))


def _get_config(params=None):
  """Returns a sample bisect config dict with some fields overridden."""
  example_config = {
      'test_type': 'perf',
      'command': (
          'src/tools/perf/run_benchmark -v --browser=release smoothness.'
          'tough_scrolling_cases'),
      'good_revision': '314015',
      'bad_revision': '314017',
      'metric': 'mean_input_event_latency/mean_input_event_latency',
      'repeat_count': '2',
      'max_time_minutes': '5',
      'bug_id': '',
      'gs_bucket': 'chrome-perf',
      'builder_host': 'master4.golo.chromium.org',
      'builder_port': '8341',
      'dummy_builds': 'True',
      'skip_gclient_ops': 'True',
      'recipe_tester_name': 'linux_perf_tester'
  }
  if params:
    example_config.update(params)
  return example_config


def _get_step_data_for_revision(api, revision_data, include_build_steps=True):
  """Generator that produces step patches for fake results."""
  commit_pos = revision_data['commit_pos']
  commit_hash = revision_data['hash']
  test_results = revision_data.get('test_results')

  if 'refrange' in revision_data:
    parent_step = 'Resolving reference range.'
    step_name = parent_step + 'resolving commit_pos ' + commit_pos
    yield api.step_data(step_name,
                        stdout=api.raw_io.output('hash:' + commit_hash))

    step_name = parent_step + 'resolving hash ' + commit_hash
    commit_pos_str = 'refs/heads/master@{#%s}' % commit_pos
    yield api.step_data(step_name, stdout=api.raw_io.output(commit_pos_str))

  if include_build_steps:
    if test_results:
      step_name = 'gsutil Get test results for build ' + commit_hash
      yield api.step_data(step_name, stdout=api.json.output(test_results))

    if revision_data.get('DEPS', False):
      step_name = 'fetch file %s:DEPS' % commit_hash
      yield api.step_data(step_name, stdout=api.raw_io.output(
          revision_data['DEPS']))

    if 'git_diff' in revision_data:
      for deps_rev, diff_file in revision_data['git_diff'].iteritems():
        step_name = 'Generating patch for %s:DEPS to %s'
        step_name %= (commit_hash, deps_rev)
        yield api.step_data(step_name, stdout=api.raw_io.output(diff_file))

    if 'DEPS_change' in revision_data:
      step_name = 'Checking DEPS for ' + commit_hash
      yield api.step_data(step_name, stdout=api.raw_io.output('DEPS'))

    if 'DEPS_interval' in revision_data:
      for depot_name, interval in revision_data['DEPS_interval'].iteritems():
        for item in reversed(interval[:-1]):
          step_name = 'Hashing modified DEPS file with revision ' + item
          file_hash = 'f412e8458'
          yield api.step_data(step_name, stdout=api.raw_io.output(file_hash))
        step_name = 'Expanding revision range for revision %s on depot %s'
        step_name %= (interval[-1], depot_name)
        stdout = api.json.output([(r, 0) for r in interval[:-1]])
        yield api.step_data(step_name, stdout=stdout)

    if 'cl_info' in revision_data:
      step_name = 'Reading culprit cl information.'
      stdout = api.json.output(revision_data['cl_info'])
      yield api.step_data(step_name, stdout=stdout)
