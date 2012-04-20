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


def _get_first_number(line):
  for part in line.split():
    if part.isdigit():
      return int(part)

  print 'No number in :'
  print line
  return 0


class TestRunSummary(object):
  def __init__(self):
    self.test_passed_count = 0
    self.failed_tests = []
    self.disabled_test_count  = 0
    self.ignored_test_count = 0

  def AddSummaryData(self, buf):
    lines = buf.splitlines()

    for line in lines:
      if '[  PASSED  ]' in line:
        self.test_passed_count += _get_first_number(line)
      elif '[  FAILED  ]' in line:
        if ', listed below' not in line:
          self.failed_tests.append(line)
      elif 'DISABLED' in line:
        self.disabled_test_count += _get_first_number(line)
      elif 'failures' in line:
        self.ignored_test_count += _get_first_number(line)

  def Output(self):
    output = []

    output.append('[  PASSED  ] %i tests.' % self.test_passed_count)
    if self.failed_tests:
      output.append('[  FAILED  ] failed tests listed below:')
      output.extend(self.failed_tests)
      output.append('%i FAILED TESTS' % len(self.failed_tests))

    if self.disabled_test_count:
      output.append('%i DISABLED TESTS' % self.disabled_test_count)

    if self.ignored_test_count:
      output.append('%i tests with ignored failures (FAILS prefix)' %
                    self.ignored_test_count)

    return output


# TODO(csharp) The sharing_supervisor.py also has test parsing code, they should
# be shared.
def TestRunOutput(output):
  """Go through the given output and only return the output from the Test Run
     Step.
  """
  test_run_output = []

  in_step = False
  step_name = ''
  for line in output.splitlines(True):
    if in_step:
      if '[       OK ] ' + step_name in line:
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
  summary_total = TestRunSummary()
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
        test_exit_codes = test_outputs['exit_codes'].split(',')
        exit_codes[index] = int(max(test_exit_codes))
        hostnames[index] = test_outputs['hostname']

        print
        print '================================================================'
        print 'Begin output from shard index %s (%s)' % (index,
                                                         hostnames[index])
        print '================================================================'
        print

        cleaned_output = TestRunOutput(test_outputs['output'])
        summary_index = cleaned_output.rfind('[  PASSED  ]')
        summary_total.AddSummaryData(cleaned_output[summary_index:])
        sys.stdout.write(cleaned_output[:summary_index - 1])

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

  print '\n'.join(summary_total.Output())
  print

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
