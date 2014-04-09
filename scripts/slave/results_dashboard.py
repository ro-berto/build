#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions for adding results to the Performance Dashboard."""

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
def SendResults(logs_dict, perf_id, test, url, mastername, buildername,
                buildnumber, build_dir, supplemental_columns,
                fail_hard=False):
  """Takes data in the old log format, and sends it to the dashboard.

  This function tries to send any data from the cache file (which contains any
  data that wasn't successfully sent in a previous run), as well as the data
  from the arguments provided in this run.

  Args:
    logs_dict: Map of log filename (which contains the chart name) to a list of
        log file lines. Each one of these lines should be valid JSON and should
        include the properties 'traces' and 'rev'.
    perf_id: A string such as 'linux-release'. This is the bot name used on
        the dashboard.
    test: Test suite name (Note: you can also provide nested subtests
        under the top-level test by separating names with a slash.
    url: Performance Dashboard URL.
    mastername: Buildbot master name, e.g. 'chromium.perf'. Note that this is
        *not* necessarily the same as the "master name" used on the dashboard.
        This was previously incorrectly called the "master id".
    buildername: Builder name.
    buildnumber: Build number as a string.
    build_dir: Directory name, where the cache dir shall be.
    supplemental_columns: Dictionary of supplemental data to upload.
    fail_hard: Whether a fatal error will cause this step of the buildbot
        run to be annotated with "@@@STEP_EXCEPTION@@@".
  """
  # Validate some of the required arguments.
  if not logs_dict:
    print 'Empty logs dictionary passed to SendResults: %s' % str(logs_dict)
    print '@@@STEP_EXCEPTION@@@'
    return
  if type(supplemental_columns) is not dict:
    print 'Non-dictionary supplemental_columns: %s' % str(supplemental_columns)
    print '@@@STEP_EXCEPTION@@@'
    return

  new_results_lines = _GetResultsJson(logs_dict, perf_id, test, url,
                                      mastername, buildername, buildnumber,
                                      supplemental_columns)
  # Write the new request line to the cache, in case of errors.
  cache_filename = _GetCacheFileName(build_dir)
  cache = open(cache_filename, 'ab')
  for line in new_results_lines:
    cache.write('\n' + line)
  cache.close()

  # Send all the results from this run and the previous cache to the dashboard.
  cache = open(cache_filename, 'rb')
  cache_lines = cache.readlines()
  cache.close()
  errors = []
  lines_to_retry = []
  fatal_error = False
  total_results = len(cache_lines)
  for index, line in enumerate(cache_lines):
    line = line.strip()
    if not line:
      continue
    print 'Submitting result %d of %d to dashboard...' % (
        index + 1, total_results)
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


def _GetResultsJson(logs_dict, perf_id, test_name, url, mastername, buildername,
                    buildnumber, supplemental_columns):
  """Prepare JSON to send from the data in the given arguments.

  Args:
    log_dict: A dictionary mapping summary log file names to lists of log-file
        lines. Each line is valid JSON which when parsed is a dictionary that
        has the keys 'traces' and 'rev'.
    perf_id: A string such as 'linux-release'.
    test_name: Test name.
    url: Chrome Performance Dashboard URL.
    mastername: Buildbot master name (this is lowercase with dots, and is not
        necessarily the same as the "master" sent to the dashboard).
    buildername: Builder name.
    buildnumber: Build number.
    supplemental_columns: Dictionary of supplemental data to add.

  Returns:
    A list JSON strings that shall be sent to the dashboard.
  """
  results_to_add = []
  # Note that this master string is not the same as "mastername"!
  master = slave_utils.GetActiveMaster()
  revision = None

  for logname, log in logs_dict.iteritems():
    if not logname.endswith('-summary.dat'):
      continue
    lines = [str(l).rstrip() for l in log]
    chart_name = logname.replace('-summary.dat', '')

    for line in lines:
      data = json.loads(line)
      revision, revision_columns = _RevisionNumberColumns(data, master)

      for (trace_name, trace_values) in data['traces'].iteritems():
        is_important = trace_name in data.get('important', [])
        test_path = _TestPath(test_name, chart_name, trace_name)
        result = {
            'master': master,
            'bot': perf_id,
            'test': test_path,
            'revision': revision,
            'masterid': mastername,
            'buildername': buildername,
            'buildnumber': buildnumber,
            'supplemental_columns': {}
        }
        # Add the supplemental_columns values that were passed in after the
        # calculated revision column values so that these can be overwritten.
        result['supplemental_columns'].update(revision_columns)
        result['supplemental_columns'].update(supplemental_columns)
        # Check whether we have x/y data.
        have_multi_value_data = False
        for value in trace_values:
          if isinstance(value, list):
            have_multi_value_data = True
        if have_multi_value_data:
          result['data'] = trace_values
        else:
          result['value'] = trace_values[0]
          result['error'] = trace_values[1]

        if data.get('units'):
          result['units'] = data['units']
        if data.get('units_x'):
          result['units_x'] = data['units_x']
        if is_important:
          result['important'] = True
        results_to_add.append(result)

  _PrintLinkStep(url, master, perf_id, test_name, revision)

  # It was experimentally determined that 512 points takes about 7.5 seconds
  # to handle, and App Engine times out after about 60 seconds.
  results_lists = _ChunkList(results_to_add, 500)
  return map(json.dumps, results_lists)


def _ChunkList(items, chunk_size):
  """Divides a list into a list of sublists no longer than the given size.

  Args:
    items: The original list of items. Can be very long.
    chunk_size: The maximum size of sublists in the results returned.

  Returns:
    A list of sublists (which contain the original items, in order).
  """
  chunks = []
  items_left = items[:]
  while items_left:
    chunks.append(items_left[:chunk_size])
    items_left = items_left[chunk_size:]
  return chunks


def _RevisionNumberColumns(data, master):
  """Get the revision number and revision-related columns from the given data.

  Args:
    data: A dict of information from one line of the log file.
    master: The name of the buildbot master.

  Returns:
    A pair with the revision number (which must be an int), and a dict of
    version-related supplemental columns.
  """
  def GetTimestamp():
    """Get the Unix timestamp for the current time."""
    return int(calendar.timegm(datetime.datetime.utcnow().utctimetuple()))

  revision_supplemental_columns = {}
  git_hash = None
  try:
    revision = int(data['rev'])
  except ValueError:
    # The dashboard requires ordered integer revision numbers. If the revision
    # is not an integer, assume it's a git hash and send a timestamp.
    revision = GetTimestamp()
    git_hash = data['rev']

  if 'ver' in data and data['ver'] != 'undefined':
    revision_supplemental_columns['r_chrome_version'] = data['ver']
    revision_supplemental_columns['a_default_rev'] = 'r_chrome_version'
    revision = GetTimestamp()

  if master in ['ChromiumWebkit', 'Oilpan']:
    # Blink builds can have the same chromium revision for two builds. So
    # order them by timestamp to get them to show on the dashboard in the
    # order they were built.
    if not git_hash:
      revision_supplemental_columns['r_chromium_svn'] = revision
    revision = GetTimestamp()

  # Regardless of what the master is, if a git hash is given instead of an int,
  # then set a supplemental column to hold this git hash.
  if git_hash:
    revision_supplemental_columns['r_chromium'] = git_hash

  if master == 'Oilpan':
    # For Oilpan, send the webkit_rev as r_oilpan since we are getting
    # the oilpan branch revision instead of the Blink trunk revision
    # and set r_oilpan to be the dashboard default revision.
    revision_supplemental_columns['r_oilpan'] = data['webkit_rev']
    revision_supplemental_columns['a_default_rev'] = 'r_oilpan'
  else:
    # For other revision data, add it if it's present and not undefined:
    for key in ['webkit_rev', 'webrtc_rev', 'v8_rev']:
      if key in data and data[key] != 'undefined':
        revision_supplemental_columns['r_' + key] = data[key]

  return revision, revision_supplemental_columns


def _TestPath(test_name, chart_name, trace_name):
  """Get the slash-separated test path.

  Args:
    test: Test name. Typically, this will be a top-level 'test suite' name
        such as 'moz'. A nested test hierarchy can be specified by including
        slashes in this name.
    chart_name: Name of chart where multiple trace lines are grouped.
    trace_name: Name of trace line on chart.

  Returns:
    A slash-separated list of names that corresponds to the hierarchy of test
    data in the Chrome Performance Dashboard.
  """
  if trace_name == chart_name + '_ref':
    trace_name = 'ref'
  chart_name = chart_name.replace('_by_url', '')
  trace_name = trace_name.replace('/', '_')
  test_path = '%s/%s/%s' % (test_name, chart_name, trace_name)
  if chart_name == trace_name:
    test_path = '%s/%s' % (test_name, chart_name)
  return test_path


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
