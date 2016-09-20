#! /usr/bin/env python
# Copyright 2016 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
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
    for testsuite_run in json_object['per_iteration_data']:
      for test, test_runs in testsuite_run.iteritems():
        results_list.extend([
            {
                'name': test,
                'status': tr['status'],
                'duration': tr['elapsed_time_ms'],
                'output_snippet': tr['output_snippet'],
                'tombstones': tr['tombstones'] if 'tombstones' in tr else '',
            } for tr in test_runs])
    return results_to_html(results_list, cs_base_url, master_name)

def code_search(test, cs_base_url):
  search = test.replace('#', '.')
  return '%s/?q=%s&type=cs' % (cs_base_url, search)

def create_test_row_data(results, cs_base_url):
  tombstones_data = []
  test_row_list = []
  for result in results:
    add_tombstone = result['status'] == 'CRASH' and result['tombstones']
    tombstones_name = '%s_tombstones' % result['name']
    if add_tombstone:
      tombstones_data.append(
          {
            'id': tombstones_name,
            'data': result['tombstones']
          })
    test_case = ([
        {'data': result['name'], 'class': 'left',
         'link': code_search(result['name'], cs_base_url)},
        {'data': result['status'], 
         'class': 'center ' + result['status'].lower(),
         'action': add_tombstone,
         'action_argument': tombstones_name,
         'title': 'Show tombstones of this crashed test case.'},
        {'data': result['duration'], 'class': 'center'},
        {'data': result['output_snippet'], 
         'class': 'left', 'is_pre': True}
        ])
    test_row_list.append(test_case)
  return test_row_list, tombstones_data

def create_suite_row_data(results):
  # Summary of all suites.
  suites_summary = [{'data': 'TOTAL', 'class' : 'center',
                     'action': True},
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

  for result in results:
    # Constructing suite_row_dict and suites_summary
    test_case_path = result['name']
    suite_name = (test_case_path.split('#')[0] if '#' in test_case_path
                  else test_case_path.split('.')[0])
    if suite_name in suite_row_dict:
      suite_row = suite_row_dict[suite_name]
    else:
      suite_row = [{'data': suite_name, 'class' : 'left',
                    'action': True},
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
    elif result['status'] == 'FAILURE':
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
  return suite_row_dict.values(), suites_summary

# Convert list of test results into html format.
def results_to_html(results, cs_base_url, master_name):
  test_row_list, tombstones_data = create_test_row_data(results, cs_base_url)
  suite_row_list, suites_summary = create_suite_row_data(results)

  test_table_values = {
    'table_id' : 'test-table',
    'table_headers' : [('text', 'test_name'),
                       ('text', 'status'),
                       ('number', 'duration'),
                       ('text', 'output_snippet'),
                      ],
    'table_rows' : test_row_list,
  }

  suite_table_values = {
    'table_id' : 'suite-table',
    'table_headers' : [('text', 'suite_name'),
                       ('number', 'number_success_tests'),
                       ('number', 'number_fail_tests'),
                       ('number', 'all_tests'),
                       ('number', 'elapsed_time_ms'),
                      ],
    'table_rows' : suite_row_list,
    'summary' : suites_summary,
  }

  main_template = JINJA_ENVIRONMENT.get_template(
      os.path.join('template', 'main.html'))
  return main_template.render(
      {'tb_values': [suite_table_values, test_table_values],
       'master_name': master_name,
       'hidden_data': tombstones_data})

def main():
  logging.basicConfig(level=logging.INFO)
  parser = argparse.ArgumentParser()
  parser.add_argument('--json-file', help='Path of json file.', required=True)
  parser.add_argument('--html-file', help='Path to store html file.',
                      required=True)
  parser.add_argument('--cs-base-url', help='Base url for code search.',
                      default='http://cs.chromium.org')
  parser.add_argument('--master-name', help='Master name in urls.')

  args = parser.parse_args()
  if os.path.exists(args.json_file):
    result_html_string = result_details(args.json_file, args.cs_base_url,
                                        args.master_name)
    with open(args.html_file, 'w') as html:
      html.write(result_html_string)
  else:
    raise Exception('Json file of result details is not found.')

if __name__ == '__main__':
  sys.exit(main())