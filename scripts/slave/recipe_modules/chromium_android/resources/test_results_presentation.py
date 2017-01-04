#! /usr/bin/env python
# Copyright 2016 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import itertools
import json
import logging
import os
import sys

# Load jinja2.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(
    CURRENT_DIR, '..', '..', '..', '..', '..'))
sys.path.append(os.path.join(BASE_DIR, 'third_party', 'markupsafe'))
sys.path.append(os.path.join(BASE_DIR, 'third_party', 'jinja2'))
import jinja2
JINJA_ENVIRONMENT = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname(__file__)),
    autoescape = True)

# Get result details from json path and then convert results to html.
def result_details(json_path, cs_base_url, master_name):
  with open(json_path) as json_file:
    json_object = json.loads(json_file.read())
    results_list = []
    if not 'per_iteration_data' in json_object:
      return 'Error: json file missing per_iteration_data.'
    test_results_dict = {}
    for testsuite_run in json_object['per_iteration_data']:
      for test, test_runs in testsuite_run.iteritems():
        test_results_dict[test] = [
            {
                'name': test,
                'status': tr['status'],
                'duration': tr['elapsed_time_ms'],
                'output_snippet': tr['output_snippet'],
                'tombstones': (tr['tombstones_url']
                    if 'tombstones_url' in tr else ''),
                'logcat': tr['logcat_url'] if 'logcat_url' in tr else '',
            } for tr in test_runs]
    return results_to_html(test_results_dict, cs_base_url, master_name)

def code_search(test, cs_base_url):
  search = test.replace('#', '.')
  return '%s/?q=%s&type=cs' % (cs_base_url, search)

def status_class(status):
  status = status.lower()
  if status not in ('success', 'skipped'):
    return 'failure %s' % status
  return status

def create_logs(result):
  link = []
  if result['logcat']:
    logcat = {}
    logcat['data'] = 'logcat'
    logcat['link'] = result['logcat']
    logcat['target'] = '_blank'
    link.append(logcat)
  if result['tombstones'] and result['status'] == 'CRASH':
    tombstones = {}
    tombstones['data'] = 'tombstones'
    tombstones['link'] = result['tombstones']
    tombstones['target'] = '_blank'
    link.append(tombstones)
  if link:
    return {'link': link, 'class': 'center'}
  else:
    return {'data': '(no logs)', 'class': 'center'}

def create_test_row_data(results_dict, cs_base_url):
  tests_list = []
  for test in results_dict:
    test_runs = []
    for index, result in enumerate(results_dict[test]):
      if index == 0:
        test_run = [
            {'link': [{'data': result['name'],
                       'link': code_search(result['name'], cs_base_url),
                       'target': '_blank'}],
             'rowspan': len(results_dict[test]),
             'first_row_of_the_block': True,
             'class': 'left ' + result['name'],
            }]
      else:
        test_run = []
      # class: The class of html element.
      # link: href link of the element.
      # target: The openning page, whether existing or new, of link.
      test_run.extend([
          {'data': result['status'],
           'class': 'center ' + status_class(result['status'])},
          {'data': result['duration'], 'class': 'center'},
          create_logs(result),
          {'data': result['output_snippet'],
           'class': 'left', 'is_pre': True}
          ])
      test_runs.append(test_run)
    tests_list.append(test_runs)
  return tests_list

def create_suite_row_data(results_dict):
  # Summary of all suites.
  # class: The class of html element.
  # link: href link of the element.
  # target: The openning page, whether existing or new, of link.
  suites_summary = [{'link': [{'data': 'TOTAL',
                               'link': ('?suite=%s' % 'TOTAL'),
                               'target': '_self'}],
                     'class': 'center'},
                    {'data': 0, 'class': 'center'},
                    {'data': 0, 'class': 'center'},
                    {'data': 0, 'class': 'center'},
                    {'data': 0, 'class': 'center'}]

  suite_row_dict = {}
  # 'suite_row' is [name, success_count, fail_count, all_count, time].
  SUCCESS_COUNT = 1
  FAIL_COUNT = 2
  ALL_COUNT = 3
  TIME = 4

  for result_name in results_dict:
    # Since we only care about the result of the last test run.
    result = results_dict[result_name][-1]

    # Constructing suite_row_dict and suites_summary
    test_case_path = result['name']
    suite_name = (test_case_path.split('#')[0] if '#' in test_case_path
                  else test_case_path.split('.')[0])
    if suite_name in suite_row_dict:
      suite_row = suite_row_dict[suite_name]
    else:
      suite_row = [{'link': [{'data': suite_name,
                             'link': ('?suite=%s' % suite_name),
                             'target': '_self'}],
                    'class': 'left'},
                   {'data': 0, 'class': 'center'},
                   {'data': 0, 'class': 'center'},
                   {'data': 0, 'class': 'center'},
                   {'data': 0, 'class': 'center'}]
    suite_row_dict[suite_name] = suite_row

    suite_row[ALL_COUNT]['data'] += 1
    suites_summary[ALL_COUNT]['data'] += 1
    if result['status'] == 'SUCCESS':
      suite_row[SUCCESS_COUNT]['data'] += 1
      suites_summary[SUCCESS_COUNT]['data'] += 1
    elif result['status'] != 'SKIPPED':
      suite_row[FAIL_COUNT]['data'] += 1
      suites_summary[FAIL_COUNT]['data'] += 1
    suite_row[TIME]['data'] += result['duration']
    suites_summary[TIME]['data'] += result['duration']

  for suite in suite_row_dict.values():
    if suite[FAIL_COUNT]['data'] > 0:
      suite[FAIL_COUNT]['class'] += ' failure'
    else:
      suite[FAIL_COUNT]['class'] += ' success'
  if suites_summary[FAIL_COUNT]['data'] > 0:
    suites_summary[FAIL_COUNT]['class'] += ' failure'
  else:
    suites_summary[FAIL_COUNT]['class'] += ' success'
  return [[suite_row] for suite_row in suite_row_dict.values()], suites_summary

# Convert list of test results into html format.
def results_to_html(results, cs_base_url, master_name):
  test_row_blocks = create_test_row_data(results, cs_base_url)
  suite_row_blocks, suites_summary = create_suite_row_data(results)

  test_table_values = {
    'table_id' : 'test-table',
    'table_headers' : [('text', 'test_name'),
                       ('flaky', 'status'),
                       ('number', 'duration'),
                       ('text', 'logs'),
                       ('text', 'output_snippet'),
                      ],
    'table_row_blocks' : test_row_blocks,
  }

  suite_table_values = {
    'table_id' : 'suite-table',
    'table_headers' : [('text', 'suite_name'),
                       ('number', 'number_success_tests'),
                       ('number', 'number_fail_tests'),
                       ('number', 'all_tests'),
                       ('number', 'elapsed_time_ms'),
                      ],
    'table_row_blocks' : suite_row_blocks,
    'summary' : suites_summary,
  }

  main_template = JINJA_ENVIRONMENT.get_template(
      os.path.join('template', 'main.html'))
  return main_template.render(
      {'tb_values': [suite_table_values, test_table_values],
       'master_name': master_name})

def main():
  logging.basicConfig(level=logging.INFO)
  parser = argparse.ArgumentParser()
  parser.add_argument('--json-file', help='Path of json file.', required=True)
  parser.add_argument('--cs-base-url', help='Base url for code search.',
                      default='http://cs.chromium.org')
  parser.add_argument('--master-name', help='Master name in urls.')

  args = parser.parse_args()
  if os.path.exists(args.json_file):
    result_html_string = result_details(args.json_file, args.cs_base_url,
                                        args.master_name)
    print result_html_string
  else:
    raise Exception('Json file of result details is not found.')

if __name__ == '__main__':
  sys.exit(main())