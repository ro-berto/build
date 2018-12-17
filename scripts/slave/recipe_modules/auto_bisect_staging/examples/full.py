# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

DEPS = [
    'auto_bisect_staging',
    'chromium',
    'chromium_tests',
    'recipe_engine/json',
    'depot_tools/gclient',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

"""This file is a recipe demonstrating the auto_bisect_staging recipe module.

For more information about recipes, see: https://goo.gl/xKnjz6
"""


def RunSteps(api):
  # Dupe of bisection/desktop_bisect recipe.
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)])
  api.chromium_tests.configure_build(bot_config)
  api.gclient.apply_config('perf')
  api.gclient.c.got_revision_mapping.pop('catapult', None)
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)
  api.path.c.dynamic_paths['catapult'] = (
      api.auto_bisect_staging.working_dir.join('catapult'))
  api.path.c.dynamic_paths['bisect_results'] = api.path['start_dir'].join(
      'bisect_results')
  api.auto_bisect_staging.start_try_job(
      api, update_step=update_step, bot_db=bot_db,
      do_not_nest_wait_for_revision=True)

def GenTests(api):
  yield (
      api.test('basic_linux_bisect')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': 123.0,
              'gs_bucket': 'chrome-perf',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester',
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
              'gsutil_exists': 10 * [False]
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [12, 13, 16, 7],
              'test_results': 5 * [{'retcode': 0}],
              'gsutil_exists': [True],
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
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [12, 13, 16, 7],
              'test_results': 5 * [{'retcode': 0}],
          }]))
  yield (
      api.test('basic_buildbot_bisect')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('./src/out/Release/cc_perftests '
                    '--test-launcher-print-test-stdio=always --verbose'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'calc_draw_props_time/touch_region_heavy',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
              'gsutil_exists': 10 * [False]
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [12, 13, 16, 7],
              'test_results': 5 * [{'retcode': 0}],
              'gsutil_exists': [True],
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
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [12, 13, 16, 7],
              'test_results': 5 * [{'retcode': 0}],
          }]))
  yield (
      api.test('basic_resource_sizes_bisect')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('./src/build/android/test_runner.py perf '
                    '--print-step "resource_sizes MonochromePublic.apk" '
                    '--adb-path {ADB_PATH}'
                    '--verbose --output-chartjson-data={OUTPUT_FILE}'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'calc_draw_props_time/touch_region_heavy',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
              'gsutil_exists': 10 * [False]
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [12, 13, 16, 7],
              'test_results': 5 * [{'retcode': 0}],
              'gsutil_exists': [True],
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
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [12, 13, 16, 7],
              'test_results': 5 * [{'retcode': 0}],
          }]))
  yield (
      api.test('v8_roll_bisect_bis')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 21, 22, 1],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [19, 20, 21, 22, 1],
              'test_results': 5 * [{'retcode': 0}],
              "DEPS": ("vars={'v8_revision': '001'};"
                       "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                       "'src/third_party/WebKit': 'webkit.git@010'}"),
          },
          {
              'depot':'v8',
              'hash': '002',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 5 * [{'retcode': 0}],
              'gsutil_exists': 10 * [False],
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
              'depot':'v8',
              'hash': '003',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 5 * [{'retcode': 0}],
              'DEPS_change': 'True',
              "DEPS": ("vars={'v8_revision': '004'};"
                       "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                       "'src/third_party/WebKit': 'webkit.git@010'}"),
              'DEPS_interval': {'v8': '002 003 004'.split()},
          }]))
  yield (
      api.test('v8_roll_bisect')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 21, 22, 1],
              'test_results': 5 * [{'retcode': 0}],
              "DEPS": ("vars={'v8_revision': '001'};"
                       "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                       "'src/third_party/WebKit': 'webkit.git@010'}"),
          },
          {
              'depot':'v8',
              'hash': '002',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 5 * [{'retcode': 0}],
              'gsutil_exists': 10 * [False],
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
              'depot':'v8',
              'hash': '003',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 5 * [{'retcode': 0}],
              'DEPS_change': 'True',
              "DEPS": ("vars={'v8_revision': '004'};"
                       "deps = {'src/v8': 'v8.git@' + Var('v8_revision'),"
                       "'src/third_party/WebKit': 'webkit.git@010'}"),
              'DEPS_interval': {'v8': '002 003 004'.split()},
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 5 * [{'retcode': 0}],
          }]))
  yield (
      api.test('retest_bisect')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': 10 * [0] + [1],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': 20 * [0] + [7],
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': 10 * [0] + [7],
          }]))
  yield (
      api.test('bad_config')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314016',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': 'crbug.com/123123',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          }))
  yield (
      api.test('return_code')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'return_code',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314014',
              'bad_revision': '314017',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': '0a1b2c3d4f0a1b2c3d4f0a1b2c3d4f0a1b2c3d4f',
              'commit_pos': '314014',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [20, 19, 23, 7],
              'test_results': 5 * [{'retcode': 1}],
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [20, 19, 23, 7],
              'test_results': 5 * [{'retcode': 1}],
          }]))
  yield (
      api.test('return_code_fail')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'return_code',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314014',
              'bad_revision': '314017',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': '0a1b2c3d4f0a1b2c3d4f0a1b2c3d4f0a1b2c3d4f',
              'commit_pos': '314014',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [20, 19, 23, 7],
              'test_results': 5 * [{'retcode': 0}],
          }]))
  yield (
      api.test('basic_bisect_other_direction')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [12, 13, 14, 7],
              'test_results': 5 * [{'retcode': 0}],
              'cl_info': {
                  'author': 'DummyAuthor',
                  'email': 'dummy@nowhere.com',
                  'subject': 'Some random CL',
                  'date': '01/01/2015',
                  'body': ('A long description for a CL.\n'
                           'Containing multiple lines'),
              },
          }]))
  yield (
      api.test('no_repro')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314016',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 5 * [{'retcode': 0}],
          },
          ]))
  yield (
      api.test('gathering_references_no_values')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314016',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [],
              'test_results': 5 * [{'retcode': 1}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [],
              'test_results': 5 * [{'retcode': 1}],
          },
          ]))
  yield (
      api.test('failed_build')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314016',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'gsutil_exists': 2 * [False],
              'test_results': 5 * [{'retcode': 0}],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'SUCCESS'}}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          ]))
  yield (
      api.test('failed_buildbucket_get')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314016',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'gsutil_exists': 2 * [False],
              'test_results': 5 * [{'retcode': 0}],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'SUCCESS'}}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'gsutil_exists': 10 * [False],
              'build_status': ['ERROR'],
          },
          ]))
  yield (
      api.test('no_values')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'test_results': 21 * [{'retcode': 0}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'parsed_values': [404],
              'test_results': 21 * [{'retcode': 0}],
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 21 * [{'retcode': 0}],
          }]))
  yield (
      api.test('failed_build_inconclusive_1')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314017',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'gsutil_exists': 2 * [False],
              'test_results': 5 * [{'stdout': 'benchmark text', 'retcode': 0}],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'SUCCESS'}}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314016',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314017',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 21 * [{'stdout': 'benchmark text', 'retcode': 0}],
          },
          ]))
  yield (
      api.test('failed_build_inconclusive_11')
      + api.properties(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          bot_id='dummybot',
          buildnumber=571,
          bisect_config={
              'test_type': 'perf',
              'command':
                  ('src/tools/perf/run_benchmark -v --browser=release '
                   '--output-format=valueset smoothness.tough_scrolling_cases'),
              'good_revision': '314015',
              'bad_revision': '314027',
              'metric': 'mean_input_event_latency/mean_input_event_latency',
              'bug_id': '-1',
              'gs_bucket': 'chrome-perf',
              'dummy_builds': 'True',
              'dummy_tests': 'True',
              'dummy_job_names': 'True',
              'bypass_stats_check': 'True',
              'skip_gclient_ops': 'True',
              'recipe_tester_name': 'linux_perf_tester'
          })
      + api.auto_bisect_staging([
          {
              'hash': 'a6298e4afedbf2cd461755ea6f45b0ad64222222',
              'commit_pos': '314015',
              'parsed_values': [19, 20, 23, 1],
              'gsutil_exists': 2 * [False],
              'test_results': 5 * [{'stdout': 'benchmark text', 'retcode': 0}],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'SUCCESS'}}],
          },
          {
              'hash': 'ab16ab16ab16ab16ab16ab16ab16ab16ab16ab16',
              'commit_pos': '314016',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': 'bc17bc17bc17bc17bc17bc17bc17bc17bc17bc17',
              'commit_pos': '314017',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': 'cd18cd18cd18cd18cd18cd18cd18cd18cd18cd18',
              'commit_pos': '314018',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': 'de19de19de19de19de19de19de19de19de19de19',
              'commit_pos': '314019',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': 'ef20ef20ef20ef20ef20ef20ef20ef20ef20ef20',
              'commit_pos': '314020',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': 'f021f021f021f021f021f021f021f021f021f021',
              'commit_pos': '314021',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': '0122012201220122012201220122012201220122',
              'commit_pos': '314022',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': '1223122312231223122312231223122312231223',
              'commit_pos': '314023',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': '2324232423242324232423242324232423242324',
              'commit_pos': '314024',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': '3425342534253425342534253425342534253425',
              'commit_pos': '314025',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': 'dcdcdc0ff1122212323134879ddceeb1240b0988',
              'commit_pos': '314026',
              'gsutil_exists': 10 * [False],
              'build_status': [{'build': {'status': 'SCHEDULED'}},
                               {'build': {'status': 'COMPLETED',
                                          'result': 'FAILED'}}],
          },
          {
              'hash': '00316c9ddfb9d7b4e1ed2fff9fe6d964d2111111',
              'commit_pos': '314027',
              'parsed_values': [12, 13, 14, 15, 7],
              'test_results': 21 * [{'stdout': 'benchmark text', 'retcode': 0}],
          },
          ]))
