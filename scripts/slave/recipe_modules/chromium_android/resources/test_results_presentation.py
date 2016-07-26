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
jinja_environment = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname(__file__)))

# Get result details from json path and then convert results to html.
def result_details(json_path):
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
                'output_snippet' : tr['output_snippet']
            } for tr in test_runs])
    return results_to_html(results_list)

# Convert list of test results into html format.
def results_to_html(results):
  suite_row_dict = {}
  test_row_list = []
  for result in results:
    test_row_list.append([result['name'],
                      result['status'],
                      result['duration'],
                      result['output_snippet']])

    suite_name = result['name'][:result['name'].index('#')]

    # 'suite_row' is [name, success_count, fail_count, all_count, time].
    SUCCESS_COUNT = 1
    FAIL_COUNT = 2
    ALL_COUNT = 3
    TIME = 4

    if suite_name in suite_row_dict:
      suite_row = suite_row_dict[suite_name]  
    else:
      suite_row = [suite_name, 0, 0, 0, 0]
      suite_row_dict[suite_name] = suite_row

    suite_row[ALL_COUNT] += 1
    if result['status'] == 'SUCCESS':
      suite_row[SUCCESS_COUNT] += 1
    elif result['status'] == 'FAILURE':
      suite_row[FAIL_COUNT] += 1
    suite_row[TIME] += result['duration']

  test_table_values = {
    'table_id' : 'test_table',
    'table_headers' : [('text', 'test_name'),
                       ('text', 'status'),
                       ('number', 'duration'),
                       ('text', 'output_snippet'),
                      ],
    'table_rows' : test_row_list,
  }

  suite_table_values = {
    'table_id' : 'suite_table',
    'table_headers' : [('text', 'suite_name'),
                       ('number', 'number_success_tests'),
                       ('number', 'number_fail_tests'),
                       ('number', 'all_tests'),
                       ('number', 'elapsed_time_ms'),
                      ],
    'table_rows' : suite_row_dict.values(),
  }

  main_template = jinja_environment.get_template(
      os.path.join('template', 'main.html'))
  return main_template.render(
      {'tb_values': [suite_table_values, test_table_values]})

def main():
  logging.basicConfig(level=logging.INFO)
  parser = argparse.ArgumentParser()
  parser.add_argument('--json-file', help='Path of json file.', required=True)
  parser.add_argument('--html-file', help='Path to store html file.',
                      required=True)
  args = parser.parse_args()
  if os.path.exists(args.json_file):
    result_html_string = result_details(args.json_file)

    with open(args.html_file, 'w') as html:
      html.write(result_html_string)
  else:
    raise exception('Json file of result details is not found.')

if __name__ == '__main__':
  sys.exit(main())