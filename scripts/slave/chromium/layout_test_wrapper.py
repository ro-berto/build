#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script to run layout tests on the buildbots.

TODO(qyearsley): Remove all usage of this script, see crbug.com/695700.
"""

import argparse
import os
import sys

from common import chromium_utils
from slave import build_directory
from slave import slave_utils


def layout_test(options):
  """Calls run-webkit-tests using Python from the tree."""
  build_dir = os.path.abspath(build_directory.GetBuildOutputDirectory())
  blink_scripts_dir = chromium_utils.FindUpward(
      build_dir, 'third_party', 'WebKit', 'Tools', 'Scripts')
  run_blink_tests = os.path.join(blink_scripts_dir, 'run-webkit-tests')

  # Forward all command line arguments on to run-webkit-tests.
  command = [run_blink_tests] + sys.argv[1:]

  chromium_utils.RemoveDirectory(options.results_directory)

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unit test leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  try:
    return slave_utils.RunPythonCommandInBuildDir(
        build_dir, options.target, command)
  finally:
    results_dir = options.results_directory
    results_json = os.path.join(results_dir, "full_results.json")

    # If the json results file was not produced, then we produce no output
    # file too and rely on a recipe to handle this as invalid result.
    if not os.path.isfile(results_json):
      print 'File %s not found!' % results_json
    else:
      with open(results_json, 'rb') as f:
        data = f.read()

      # data is in the form of:
      # 'ADD_RESULTS({json object});' or just '{json object}'
      start = data.find('{')
      end = data.rfind('}')
      # Find returns -1 when it didn't find something.
      if start != -1 and end != -1:
        data = data[start:end+1]
        with open(options.json_test_results, 'wb') as f:
          f.write(data)
        print 'Wrote test results to %s (%d bytes)' % (
            options.json_test_results, len(data))
      else:
        print 'JSON data not found in full_results.json'
        print '-'*75

      print data[:500], '...'
      print '<snip>'
      print '...', data[-500:]
      print '-'*75


def main():
  assert sys.platform != 'win32', 'This script should not be run on Windows.'

  # Some options are still used in what's left of this script.
  # They will be parsed and used, but then passed on verbatim.
  parser = argparse.ArgumentParser()
  parser.add_argument('--results-directory', required=True)
  parser.add_argument('--json-test-results', required=True)
  parser.add_argument('--target', required=True)
  parsed_options, _ = parser.parse_known_args()

  assert os.path.isabs(parsed_options.results_directory)

  return layout_test(parsed_options)


if '__main__' == __name__:
  sys.exit(main())
