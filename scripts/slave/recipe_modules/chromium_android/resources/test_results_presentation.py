#! /usr/bin/env python
# Copyright 2016 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import logging
import os
import sys

RESULT_DETAILS_TEMPLATE = """
<!DOCTYPE html>
<html>
  <head>
    <style>
      table, th, td {
        border: 1px solid black;
        border-collapse: collapse;
      }
      th, td {
        padding: 5px;
      }
    </style>
  </head>
  <body>
    <table style="width:100%%">
      <tr>
        <th>test_name</th>
        <th>status</th>
        <th>elapsed_time_in_ms</th>
        <th>output_snippet</th>
      </tr>
      %s
    </table>
  </body>
</html>
"""

ROW_TEMPLATE = """
    <tr align="center">
      <td>%s</td>
      <td>%s</td>
      <td>%s</td>
      <td>%s</td>
    </tr>
"""

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
    results_list.sort(key=lambda x: x['name'])
    return results_to_html(results_list)

def results_to_html(results):
  rows = ''
  for result in results:
    rows += (ROW_TEMPLATE % (result['name'],
                             result['status'],
                             result['duration'],
                             result['output_snippet']))
  return RESULT_DETAILS_TEMPLATE % rows

def main():
  logging.basicConfig(level=logging.INFO)
  parser = argparse.ArgumentParser()
  parser.add_argument('--json-file', help='Path of json file.')
  parser.add_argument('--html-file', help='Path to store html file.')
  args = parser.parse_args()
  if os.path.exists(args.json_file):
    result_html_string = result_details(args.json_file)

    with open(args.html_file, 'w') as html:
      html.write(result_html_string)
  else:
    raise exception('Json file of result details is not found.')

if __name__ == '__main__':
  sys.exit(main())