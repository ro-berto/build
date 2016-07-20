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
      var previousClickedColumn;
      var previousClickedIsAsc;

      function sortByColumn(head, index) {
        var tbody = head.parentNode.parentNode.nextElementSibling;
        var rows = tbody.rows,
            arr = new Array();

        // Fill the array with values from the table.
        for (var i = 0; i < rows.length; i++) {
          var cells = rows[i].cells;
          arr[i] = new Array();
          for (var j = 0; j < cells.length; j++) {
            arr[i][j] = cells[j].innerHTML;
          }
        }

        // Determine whether to ascend or descend.
        if (previousClickedColumn != undefined) {
          var asc = (index == previousClickedColumn) ? ((previousClickedIsAsc) ? -1 : 1) : 1;
        } else {
          var asc = 1;
        }

        // Sort the array by the specified column number (col) and order (asc).
        arr.sort(function (a, b) {
          if (head.className == "number") {
            var avalue = Number(a[index]);
            var bvalue = Number(b[index]);
          } else if (head.className == "text") {
            var avalue = a[index];
            var bvalue = b[index];
          }
          return (avalue == bvalue) ? 0 : ((avalue > bvalue) ? asc : -1 * asc);
        });

        // Replace existing rows with new rows created from the sorted array.
        for (var i = 0; i < rows.length; i++) {
          rows[i].innerHTML = "<td>" + arr[i].join("</td><td>") + "</td>";
        }

        // Make previous arrow invisible.
        if (previousClickedColumn != undefined) {
          if (previousClickedIsAsc == 1) {
            head.parentNode.getElementsByClassName("up")[previousClickedColumn].style.display = 'none';
          } else {
            head.parentNode.getElementsByClassName("down")[previousClickedColumn].style.display = 'none';
          }
        }

        // Make current arrow visible.
        if (asc == 1) {
          head.getElementsByClassName("up")[0].style.display = "inline";
        } else {
          head.getElementsByClassName("down")[0].style.display = "inline";
        }

        previousClickedColumn = index;
        previousClickedIsAsc = (asc == 1) ? true : false;
      }
    </script>
  </head>
  <body>
    <table id="test_details" style="width:100%%">
      <thead class="heads">
        <tr>
          <th class="text">
              test_name
              <span class="up" style="display:none;"> &#8593</span>
              <span class="down" style="display:none;"> &#8595</span>
          </th>

          <th class="text">
              status
              <span class="up" style="display:none;"> &#8593</span>
              <span class="down" style="display:none;"> &#8595</span>
          </th>

          <th class="number">
              elapsed_time_in_ms
              <span class="up" style="display:none;"> &#8593</span>
              <span class="down" style="display:none;"> &#8595</span>
          </th>

          <th class="text">
              output_snippet
              <span class="up" style="display:none;"> &#8593</span>
              <span class="down" style="display:none;"> &#8595</span>
          </th>
        </tr>
      </thead>
      <tbody class="body">
      %s
      </tbody>
    </table>
  </body>
  <script>
    Array.prototype.slice.call(document.getElementsByTagName('th')).forEach(
        function(head, index) {
            head.addEventListener(
                "click",
                function() { sortByColumn(head, index); },
                false
            );
        }
    );
  </script>
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