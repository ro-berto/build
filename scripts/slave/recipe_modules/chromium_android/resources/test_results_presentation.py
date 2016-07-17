#! /usr/bin/env python
# Copyright 2016 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import logging
import os
import sys

RESULT_DETAILS_TEMPLATE = """<!DOCTYPE html>
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
      th {
        cursor:pointer;
      }
    </style>
    <script type="text/javascript">
      // Default is sort by test name.
      var previousClickedColumn = 0;
      var previousClickedIsAsc = true;

      function sort_table(tbody, col, type) {
        var rows = tbody.rows,
            arr = new Array();
        // fill the array with values from the table
        for (var i = 0; i < rows.length; i++) {
            var cells = rows[i].cells;
            arr[i] = new Array();
            for (var j = 0; j < cells.length; j++) {
                arr[i][j] = cells[j].innerHTML;
            }
        }
        var asc = (col == previousClickedColumn) ? ((previousClickedIsAsc) ? -1 : 1) : 1; 
        // sort the array by the specified column number (col) and order (asc)
        arr.sort(function (a, b) {
            if (type == "number") {
                var avalue = Number(a[col]);
                var bvalue = Number(b[col]);
            } else if (type == "text") {
                var avalue = a[col];
                var bvalue = b[col];
            }
            return (avalue == bvalue) ? 0 : ((avalue > bvalue) ? asc : -1 * asc);
        });
        // replace existing rows with new rows created from the sorted array
        for (var i = 0; i < rows.length; i++) {
            rows[i].innerHTML = "<td>" + arr[i].join("</td><td>") + "</td>";
        }
        previousClickedColumn = col;
        previousClickedIsAsc = (asc == 1) ? true : false;
      }
    </script>
  </head>
  <body>
    <table style="width:100%%">
      <tr>
        <th onclick="sort_table(tests, 0, 'text');">test_name</th>
        <th onclick="sort_table(tests, 1, 'text');">status</th>
        <th onclick="sort_table(tests, 2, 'number');">elapsed_time_in_ms</th>
        <th onclick="sort_table(tests, 3, 'text');">output_snippet</th>
      </tr>
      <tbody id="tests">
      %s
      </tbody>
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