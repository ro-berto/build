#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions for adding results to perf dashboard."""

import calendar
import datetime
import httplib
import json
import os
import urllib
import urllib2

from slave import slave_utils

# The paths in the results dashboard URLs for sending and viewing results.
SEND_RESULTS_PATH = '/add_point'
RESULTS_LINK_PATH = '/report?masters=%s&bots=%s&tests=%s&rev=%s'
# CACHE_DIR/CACHE_FILENAME will be created in options.build_dir to cache
# results which need to be retried.
CACHE_DIR = 'results_dashboard'
CACHE_FILENAME = 'results_to_retry'


#TODO(xusydoc): set fail_hard to True when bots stabilize. See crbug.com/222607.
def SendResults(logname, lines, system, test_name, url, masterid,
                buildername, buildnumber, build_dir, supplemental_columns,
                fail_hard=False):
  """Send results to the Chrome Performance Dashboard.

  Try to send any data from the cache file (which contains any data that wasn't
  successfully sent in a previous run), as well as the data from the arguments
  provided in this run.

  Args:
    logname: Summary log file name. Contains the chart name.
    lines: List of log-file lines. Each line should be valid JSON, and should
        include the properties 'traces' and 'rev'.
    system: A string such as 'linux-release', which comes from perf_id. This
        is used to identify the bot in the Chrome Performance Dashboard.
    test_name: Test name, which will be used as the first part of the slash
        -separated test path on the Dashboard. (Note: If there are no slashes
        in this name, then this is the test suite name. If you want to have
        nested tests under one test suite, you could use a slash here.)
    url: Performance Dashboard URL (including schema).
    masterid: ID of buildbot master, e.g. 'chromium.perf'
    buildername: Builder name, e.g. 'Linux QA Perf (1)'
    buildnumber: Build number (a string containing the number).
    build_dir: Directory name, where the cache dir shall be.
    supplemental_columns: Dict of supplemental data to upload.
    fail_hard: Whether a fatal error will cause this step of the buildbot
        run to be annotated with "@@@STEP_EXCEPTION@@@".

  Returns: None
  """
  if not logname.endswith('-summary.dat'):
    return

  new_results_line = _GetResultsJson(logname, lines, system, test_name, url,
                                     masterid, buildername, buildnumber,
                                     supplemental_columns)
  # Write the new request line to the cache, in case of errors.
  cache_filename = _GetCacheFileName(build_dir)
  cache = open(cache_filename, 'ab')
  cache.write('\n' + new_results_line)
  cache.close()

  # Send all the results from this run and the previous cache to the dashboard.
  cache = open(cache_filename, 'rb')
  cache_lines = cache.readlines()
  cache.close()
  errors = []
  lines_to_retry = []
  fatal_error = False
  for index, line in enumerate(cache_lines):
    line = line.strip()
    if not line:
      continue
    error = _SendResultsJson(url, line)
    if error:
      if index != len(cache_lines) - 1:
        # The very last item in the cache_lines list is the new results line.
        # If this line is not the new results line, then this results line
        # has already been tried before; now it's fatal.
        fatal_error = True
      lines_to_retry = [l.strip() for l in cache_lines[index:] if l.strip()]
      errors.append(error)
      break

  # Write any failing requests to the cache file.
  cache = open(cache_filename, 'wb')
  cache.write('\n'.join(set(lines_to_retry)))
  cache.close()

  # Print any errors, and if there was a fatal error, it should be an exception.
  for error in errors:
    print error
  if fatal_error:
    if fail_hard:
      print 'Multiple failures uploading to dashboard.'
      print '@@@STEP_EXCEPTION@@@'
    else:
      print 'Multiple failures uploading to dashboard.'
      print 'You may have to whitelist your bot, please see crbug.com/222607.'
      print '@@@STEP_WARNINGS@@@'


def _GetCacheFileName(build_dir):
  """Get the cache filename, creating the file if it does not exist."""
  cache_dir = os.path.join(os.path.abspath(build_dir), CACHE_DIR)
  if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
  cache_filename = os.path.join(cache_dir, CACHE_FILENAME)
  if not os.path.exists(cache_filename):
    # Create the file.
    open(cache_filename, 'wb').close()
  return cache_filename


def _GetResultsJson(logname, lines, system, test_name, url, masterid,
                    buildername, buildnumber, supplemental_columns):
  """Prepare JSON to send from the data in the given arguments.

  Args:
    logname: Summary log file name.
    lines: List of log-file lines. Each line is valid JSON which, when
        deserialized, is a dict containing the keys 'traces' and 'rev'.
    system: A string such as 'linux-release', which comes from perf_id.
    test_name: Test name.
    url: Chrome Performance Dashboard URL.
    masterid: Buildbot master ID.
    buildername: Builder name.
    buildnumber: Build number.
    supplemental_columns: Dict of supplemental data to add.

  Returns:
    JSON that shall be sent to the Chrome Performance Dashboard.
  """
  results_to_add = []
  master = slave_utils.GetActiveMaster()
  bot = system
  chart_name = logname.replace('-summary.dat', '')
  for line in lines:
    data = json.loads(line)
    revision = data['rev']
    git_hash = None
    chrome_supplemental_revision = False
    if master == 'ChromiumWebkit':
      # Blink builds can have the same chromium revision for two builds. So
      # order them by timestamp to get them to show on the dashboard in the
      # order they were built.
      revision = _GetTimestamp()
      chrome_supplemental_revision = True
    try:
      revision = int(revision)
    except ValueError:
      # The dashboard requires ordered integer revision numbers. If the revision
      # is not an integer, assume it's a git hash and send a timestamp.
      revision = _GetTimestamp()
      git_hash = data['rev']

    for (trace_name, trace_values) in data['traces'].iteritems():

      is_important = trace_name in data.get('important', [])
      if trace_name == chart_name + '_ref':
        trace_name = 'ref'
      chart_name = chart_name.replace('_by_url', '')
      trace_name = trace_name.replace('/', '_')
      test_path = '%s/%s/%s' % (test_name, chart_name, trace_name)
      if chart_name == trace_name:
        test_path = '%s/%s' % (test_name, chart_name)
      result = {
          'master': master,
          'bot': system,
          'test': test_path,
          'revision': revision,
          'masterid': masterid,
          'buildername': buildername,
          'buildnumber': buildnumber,
          'supplemental_columns': {},
      }
      # Test whether we have x/y data.
      have_multi_value_data = False
      for value in trace_values:
        if isinstance(value, list):
          have_multi_value_data = True
      if have_multi_value_data:
        result['data'] = trace_values
      else:
        result['value'] = trace_values[0]
        result['error'] = trace_values[1]

      if chrome_supplemental_revision:
        try:
          result['supplemental_columns']['r_chromium_svn'] = int(data['rev'])
        except ValueError:
          # Revision is git hash.
          result['supplemental_columns']['r_chromium'] = data['rev']
      if 'webkit_rev' in data and data['webkit_rev'] != 'undefined':
        result['supplemental_columns']['r_webkit_rev'] = data['webkit_rev']
      if 'v8_rev' in data and data['v8_rev'] != 'undefined':
        result['supplemental_columns']['r_v8_rev'] = data['v8_rev']
      if git_hash:
        result['supplemental_columns']['r_chromium_rev'] = git_hash
      result['supplemental_columns'].update(supplemental_columns)
      if data.get('units'):
        result['units'] = data['units']
      if data.get('units_x'):
        result['units_x'] = data['units_x']
      if data.get('stack'):
        result['stack'] = data['stack']
      if is_important:
        result['important'] = True
      results_to_add.append(result)
  _PrintLinkStep(url, master, bot, test_name, revision)
  return json.dumps(results_to_add)


def _GetTimestamp():
  return int(calendar.timegm(datetime.datetime.utcnow().utctimetuple()))


def _SendResultsJson(url, results_json):
  """Make a HTTP POST with the given JSON to the Performance Dashboard.

  Args:
    url: URL of Performance Dashboard instance.
    results_json: JSON string that contains the data to be sent.

  Returns:
    A string describing any error that occurred. If no errors, return None.
  """
  # When data is provided to urllib2.Request, a POST is sent instead of GET.
  # The data must be in the application/x-www-form-urlencoded format.
  data = urllib.urlencode({'data': results_json})
  req = urllib2.Request(url + SEND_RESULTS_PATH, data)
  try:
    urllib2.urlopen(req)
  except urllib2.HTTPError, e:
    return 'HTTPError: %d for JSON %s\n' % (e.code, results_json)
  except urllib2.URLError, e:
    return 'URLError: %s for JSON %s\n' % (str(e.reason), results_json)
  except httplib.HTTPException, e:
    return 'HTTPException for JSON %s\n' % results_json
  return None


def _PrintLinkStep(url, master, system, test_path, revision):
  """Print a buildbot annotation with a link to the results.

  Args:
    url: The Performance Dashboard URL, e.g. "https://chromeperf.appspot.com"
    master: Name of the buildbot master, e.g. ChromiumPerf
    system: A string such as 'linux-release', which comes from perf_id.
    test_path: Slash-separated test path, e.g. "moz/times"
    revision: Revision number.
  """
  results_link = url + RESULTS_LINK_PATH % (
      urllib.quote(master),
      urllib.quote(system),
      urllib.quote(test_path),
      revision)
  print '@@@STEP_LINK@%s@%s@@@' % ('Results Dashboard', results_link)
