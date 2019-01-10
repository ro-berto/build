#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import sys
import urllib
import urllib2


def _GetDashboardJson(options):
  """Produce a dict in the Dashboard JSON v1 format."""
  # https://chromium.googlesource.com/catapult/+/master/dashboard/docs/data-format.md

  with options.results_file as f:
    chart_json = json.load(f)

  return {
      'master': options.perf_dashboard_machine_group,
      'bot': options.perf_id,
      'test_suite_name': options.name,
      'point_id': options.commit_position,
      'supplemental': {
          'a_build_uri': '[%s](%s)' % ('Build status', options.build_url),
      },
      'versions': {
          'webrtc_git':options.got_webrtc_revision
      },
      'chart_data': chart_json,
  }


def _SendResultsJson(url, results_json):
  """Make a HTTP POST with the given JSON to the Performance Dashboard.

  Args:
    url: URL of Performance Dashboard instance, e.g.
        "https://chromeperf.appspot.com".
    results_json: JSON string that contains the data to be sent.
  """
  # When data is provided to urllib2.Request, a POST is sent instead of GET.
  # The data must be in the application/x-www-form-urlencoded format.
  data = urllib.urlencode({'data': results_json})
  req = urllib2.Request(url + '/add_point', data)
  return urllib2.urlopen(req)


def _CreateParser():
  parser = argparse.ArgumentParser()
  parser.add_argument('--perf-dashboard-machine-group', required=True)
  parser.add_argument('--perf-id', required=True)
  parser.add_argument('--name', required=True)
  parser.add_argument('--got-webrtc-revision', required=True)
  parser.add_argument('--commit-position', type=int, required=True)
  parser.add_argument('--build-url', required=True)
  parser.add_argument('--results-url', required=True)
  parser.add_argument('--results-file', type=argparse.FileType(), required=True)
  parser.add_argument('--output-json-file', type=argparse.FileType('w'))
  return parser


def main(args):
  parser = _CreateParser()
  options = parser.parse_args(args)

  dashboard_json = _GetDashboardJson(options)
  if options.output_json_file:
    with options.output_json_file as output_file:
      json.dump(dashboard_json, output_file)
  _SendResultsJson(options.results_url, json.dumps(dashboard_json))


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
