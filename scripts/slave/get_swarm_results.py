#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# get_swarm_results.py: Retrieves and output swarm test results for a given
# test request name.

"""Takes in a test name and retrives all the output that the swarm server
has produced for tests with that name. This is expected to be called as a
build step."""

import json
import optparse
import sys
import time
import urllib
import urllib2

from common import gtest_utils


def TestRunOutput(output):
  """Go through the given output and only return the output from the Test Run
     Step. This removes all the swarm specific output.
  """
  test_run_output = []

  in_step = False
  step_name = ''
  for line in output.splitlines(True):
    if in_step:
      if ('[       OK ] ' + step_name in line or
          '[  FAILED  ] ' + step_name in line):
        break
      else:
        test_run_output.append(line)
    elif '[ RUN      ] ' in line and 'Run Test' in line:
      in_step = True
      i = len('[ RUN      ] ')
      step_name = line[i:].strip()

  return ''.join(test_run_output)


def GetTestKeys(swarm_base_url, test_name):
  key_data = urllib.urlencode([('name', test_name)])
  test_keys_url = '%s/get_matching_test_cases?%s' % (swarm_base_url.rstrip('/'),
                                                     key_data)
  result = urllib2.urlopen(test_keys_url).read()
  if 'No matching' in result:
    print ('Error: Unable to find any tests with the name, %s, on swarm server'
           % test_name)
    return []

  # TODO(csharp): return in a proper format (like json)
  return result.split()


def GetSwarmResults(swarm_base_url, test_keys):
  gtest_parser = gtest_utils.GTestLogParser()
  hostnames = ['unknown'] * len(test_keys)
  exit_codes = [1] * len(test_keys)
  for index in range(len(test_keys)):
    result_url = '%s/get_result?r=%s' % (swarm_base_url.rstrip('/'),
                                         test_keys[index])
    while True:
      output = None
      try:
        output = urllib2.urlopen(result_url).read()
      except urllib2.HTTPError, e:
        print 'Calling %s threw %s' % (result_url, e)
        break

      try:
        test_outputs = json.loads(output)
      except (ValueError, TypeError), e:
        print 'Unable to get results for shard  %d' % index
        print e
        break

      if test_outputs['output']:
        if test_outputs['exit_codes']:
          test_exit_codes = test_outputs['exit_codes'].split(',')
          exit_codes[index] = max(map(int, test_exit_codes))
        hostnames[index] = test_outputs['hostname']

        print
        print '================================================================'
        print 'Begin output from shard index %s (%s)' % (index,
                                                         hostnames[index])
        print '================================================================'
        print

        cleaned_output = TestRunOutput(test_outputs['output'])
        for line in cleaned_output.splitlines():
          gtest_parser.ProcessLine(line)
        sys.stdout.write(cleaned_output)

        print
        print '================================================================'
        print 'End output from shard index %s (%s). Return %d' % (
            index, hostnames[index], exit_codes[index])
        print '================================================================'
        print

        if exit_codes[index] == 0:
          # If the test passed, delete the key since it is no longer needed.
          remove_key_url = '%s/cleanup_results' % (swarm_base_url.rstrip('/'))
          key_encoding = urllib.urlencode([('r', test_keys[index])])
          urllib2.urlopen(remove_key_url,
                          key_encoding)
        break
      else:
        # Test is not yet done, wait a bit before checking again.
        time.sleep(0.5)

  print 'Summary for all the shards:'

  failed_tests = gtest_parser.FailedTests()
  if len(failed_tests) > 0:
    plural = 's' if len(failed_tests) > 1 else ''
    print '%d test%s failed, listed below:' % (len(failed_tests), plural)
    print failed_tests
  else:
    print 'All tests passed.'

  return max(exit_codes)


def main():
  """Retrieve the given swarm test results from the swarm server and print it
  to stdout.

  Args:
    test_name: The name of the test to retrieve output for.
  """
  # Parses arguments
  parser = optparse.OptionParser(usage='%prog [options] test_name',
                                 description=sys.modules[__name__].__doc__)
  parser.add_option('-u', '--url', default='http://localhost:8080',
                    help='Specify the url of the Swarm server. '
                    'Defaults to %default')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Print verbose logging')
  (options, args) = parser.parse_args()
  if not args:
    parser.error('Must specify one test name.')
  elif len(args) > 1:
    parser.error('Must specify only one test name.')
  test_name = args[0]

  test_keys = GetTestKeys(options.url, test_name)

  return GetSwarmResults(options.url, test_keys)


if __name__ == '__main__':
  sys.exit(main())
