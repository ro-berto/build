#! /usr/bin/env python
# Copyright 2016 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import collections
import itertools
import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(
    CURRENT_DIR, '..', '..', '..', '..', '..'))
sys.path.append(os.path.join(BASE_DIR, 'third_party', 'markupsafe'))
sys.path.append(os.path.join(BASE_DIR, 'third_party', 'jinja2'))
import jinja2
JINJA_ENVIRONMENT = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname(__file__)),
    autoescape = True)


def result_details(json_path, cs_base_url, master_name):
  """Get result details from json path and then convert results to html."""
  with open(json_path) as json_file:
    json_object = json.loads(json_file.read())
    results_list = []
    if not 'per_iteration_data' in json_object:
      return 'Error: json file missing per_iteration_data.'
    results_dict = collections.defaultdict(list)
    for testsuite_run in json_object['per_iteration_data']:
      for test, test_runs in testsuite_run.iteritems():
        results_dict[test].extend(test_runs)
    return results_to_html(results_dict, cs_base_url, master_name)


def code_search(test, cs_base_url):
  search = test.replace('#', '.')
  return '%s/?q=%s&type=cs' % (cs_base_url, search)


def status_class(status):
  status = status.lower()
  if status not in ('success', 'skipped'):
    return 'failure %s' % status
  return status


def create_logs(result):
  link_list = []
  for name, link in result.get('links', {}).iteritems():
    link_list.append({
      'data': name,
      'link': link,
      'target': '_blank',
    })

  if link_list:
    return {'link': link_list, 'class': 'center'}
  else:
    return {'data': '(no logs)', 'class': 'center'}


def create_test_row_data(results_dict, cs_base_url):
  """Format test data for injecting into HTML table."""

  tests_list = []
  for test_name, test_results in results_dict.iteritems():
    test_runs = []
    for index, result in enumerate(test_results):
      if index == 0:
        test_run = [
            {'link': [{'data': test_name,
                       'link': code_search(test_name, cs_base_url),
                       'target': '_blank'}],
             'rowspan': len(test_results),
             'first_row_of_the_block': True,
             'class': 'left ' + test_name,
            }]
      else:
        test_run = []
      # class: The class of html element.
      # link: href link of the element.
      # target: The page to open link (new tab or same page).
      test_run.extend([
          {'data': result['status'],
           'class': 'center ' + status_class(result['status'])},
          {'data': result['elapsed_time_ms'], 'class': 'center'},
          create_logs(result),
          {'data': result['output_snippet'],
           'class': 'left', 'is_pre': True}
          ])
      test_runs.append(test_run)
    tests_list.append(test_runs)
  return tests_list


def create_suite_row_data(results_dict):
  """Format test suite data for injecting into HTML table."""

  # class: The class of html element.
  # link: href link of the element.
  # target: The page to open link (new tab or same page).
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

  for test_name, test_results in results_dict.iteritems():
    # TODO(mikecase): This logic doesn't work if there are multiple test runs.
    # That is, if 'per_iteration_data' has multiple entries.
    # Since we only care about the result of the last test run.
    result = test_results[-1]

    suite_name = (test_name.split('#')[0] if '#' in test_name
                  else test_name.split('.')[0])
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
    suite_row[TIME]['data'] += result['elapsed_time_ms']
    suites_summary[TIME]['data'] += result['elapsed_time_ms']

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


def results_to_html(results_dict, cs_base_url, master_name):
  """Convert list of test results into html format."""

  test_row_blocks = create_test_row_data(results_dict, cs_base_url)
  suite_row_blocks, suites_summary = create_suite_row_data(results_dict)

  test_table_values = {
    'table_id' : 'test-table',
    'table_headers' : [('text', 'test_name'),
                       ('flaky', 'status'),
                       ('number', 'elapsed_time_ms'),
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
  parser = argparse.ArgumentParser()
  parser.add_argument('--json-file', help='Path of json file.', required=True)
  parser.add_argument('--cs-base-url', help='Base url for code search.',
                      default='http://cs.chromium.org')
  parser.add_argument('--master-name', help='Master name in urls.')

  args = parser.parse_args()
  if os.path.exists(args.json_file):
    result_html_string = result_details(args.json_file, args.cs_base_url,
                                        args.master_name)
    print result_html_string.encode('UTF-8')
  else:
    raise IOError('--json-file %s not found.' % args.json_file)


if __name__ == '__main__':
  sys.exit(main())