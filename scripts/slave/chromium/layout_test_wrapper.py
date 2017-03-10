#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script to run layout tests on the buildbots.

Runs the run-webkit-tests script found in third_party/WebKit/Tools/Scripts above
this script, passing on many but not all command arguments to that script.

TODO(qyearsley): Remove all usage of this script, see crbug.com/695700.
"""

import json
import optparse
import os
import re
import sys

from common import chromium_utils
from slave import build_directory
from slave import slave_utils

# Options which may be forwarded by this script.
BOOLEAN_OPTIONS = [
    '--clobber-old-results',
    '--debug-rwt-logging',
    '--enable-leak-detection',
    '--enable-wptserve',
    '--enable'
    '--full-results-html',
    '--fully-parallel',
    '--no-pixel-tests',
    '--no-show-results',
]
STRING_OPTIONS = [
    '--results-directory',
    '--build-dir',
    '--target',
    '--platform',
    '--skipped',
    '--batch-size',
    '--order',
    '--seed',
    '--total-shards',
    '--shard-index',
    '--master-name',
    '--builder-name',
    '--build-number',
    '--step-name',
    '--test-results-server',
    '--time-out-ms',
    '--json-test-results',
    '--exit-after-n-failures',
    '--exit-after-n-crashes-or-timeouts',
    '--additional-driver-flag',
]
LIST_OPTIONS = [
  '--additional-expectations',
  '--test-list',
]


def layout_test(options, args):
  """Calls run-webkit-tests using Python from the tree."""
  build_dir = os.path.abspath(build_directory.GetBuildOutputDirectory())
  blink_scripts_dir = chromium_utils.FindUpward(
      build_dir, 'third_party', 'WebKit', 'Tools', 'Scripts')
  run_blink_tests = os.path.join(blink_scripts_dir, 'run-webkit-tests')

  command = [run_blink_tests]

  assert options.results_directory
  assert os.path.isabs(options.results_directory)

  chromium_utils.RemoveDirectory(options.results_directory)

  command.extend(['--results-directory', options.results_directory])

  def attr_name(flag_name):
    return flag_name.strip('-').replace('-', '_')

  for option in BOOLEAN_OPTIONS:
    if options.getattr(attr_name(option)):
      command.append(option)

  for option in STRING_OPTIONS:
    value = options.getattr(attr_name(option))
    if value:
      command.extend([option, value])

  for option in LIST_OPTIONS:
    for value in options.getattr(attr_name(option)):
      command.extend([option, value])

  command.extend(args)

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unit test leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  try:
    return slave_utils.RunPythonCommandInBuildDir(
        build_dir, options.target, command)
  finally:
    assert options.json_test_results, '--json-test-results must be given'
    results_dir = options.results_directory
    results_json = os.path.join(results_dir, "failing_results.json")

    # If the json results file was not produced, then we produce no output
    # file too and rely on a recipe to handle this as invalid result.
    if os.path.isfile(results_json):
      with open(results_json, 'rb') as f:
        data = f.read()

      # data is in the form of:
      #   ADD_RESULTS(<json object>);
      # but use a regex match to also support a raw json object.
      m = re.match(r'[^({]*' # From the beginning, take any except '(' or '{'
                   r'(?:'
                     r'\((.*)\);'  # Expect '(<json>);'
                     r'|'          # or
                     r'({.*})'     # '<json object>'
                   r')$', data)
      assert m is not None
      data = m.group(1) or m.group(2)

      json_data = json.loads(data)
      assert isinstance(json_data, dict)

      with open(options.json_test_results, 'wb') as f:
        f.write(data)


def main():
  assert sys.platform != 'win32', 'This script should not be run on Windows.'

  option_parser = optparse.OptionParser(
      description='See corresponding arguments in run-webkit-tests --help')

  for option in BOOLEAN_OPTIONS:
    option_parser.add_option(option, action='store_true')

  for option in STRING_OPTIONS:
    option_parser.add_option(option, action='store')

  for option in LIST_OPTIONS:
    option_parser.add_option(option, action='append')

  options, args = option_parser.parse_args()

  return layout_test(options, args)


if '__main__' == __name__:
  sys.exit(main())
