#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run a chrome test executable directly, or in isolated mode."""

import json
import logging
import optparse
import os
import re
import subprocess
import sys

from slave import build_directory


USAGE = ('%s [options] /full/path/to/test.exe -- [original test command]' %
         os.path.basename(sys.argv[0]))

LINUX_ISOLATE_ENABLED_TESTS = set((
  'base_unittests',
  'browser_tests',
  'interactive_ui_tests',
  'net_unittests',
  'unit_tests',
))

# TODO(maruel): Not enabled because of lack of XCode support and missing
# dependencies for more complex tests.
MAC_ISOLATE_ENABLED_TESTS = set()

WIN_ISOLATE_ENABLED_TESTS = set((
  'base_unittests',
  'browser_tests',
  'interactive_ui_tests',
  'net_unittests',
  'unit_tests',
))

# http://crbug.com/260311
# They are missing files for an unknown reason.
BUG_260311 = set((
  'browser_tests',
  'interactive_ui_tests',
))

ISOLATE_ENABLED_BUILDERS = {
  # CI linux
  'Linux Tests': LINUX_ISOLATE_ENABLED_TESTS,
  # CI mac
  'Mac10.6 Tests (1)': MAC_ISOLATE_ENABLED_TESTS,
  'Mac10.7 Tests (1)': MAC_ISOLATE_ENABLED_TESTS,
  # CI win
  'Vista Tests (1)': WIN_ISOLATE_ENABLED_TESTS - BUG_260311,
  'Vista Tests (2)': WIN_ISOLATE_ENABLED_TESTS - BUG_260311,
  'Vista Tests (3)': WIN_ISOLATE_ENABLED_TESTS - BUG_260311,
  'Win7 Tests (1)': WIN_ISOLATE_ENABLED_TESTS,
  'Win7 Tests (2)': WIN_ISOLATE_ENABLED_TESTS,
  'Win7 Tests (3)': WIN_ISOLATE_ENABLED_TESTS,
  'XP Tests (1)': WIN_ISOLATE_ENABLED_TESTS - BUG_260311,
  'XP Tests (2)': WIN_ISOLATE_ENABLED_TESTS - BUG_260311,
  'XP Tests (3)': WIN_ISOLATE_ENABLED_TESTS - BUG_260311,

  # Try Server
  'linux_rel': LINUX_ISOLATE_ENABLED_TESTS,
  'mac_rel': MAC_ISOLATE_ENABLED_TESTS,
  'win_rel': WIN_ISOLATE_ENABLED_TESTS,
}


def should_run_as_isolated(builder_name, test_name):
  logging.info('should_run_as_isolated(%s, %s)' % (builder_name, test_name))
  return test_name in ISOLATE_ENABLED_BUILDERS.get(builder_name, [])


def run_command(command):
  """Inspired from chromium_utils.py's RunCommand()."""
  print '\n' + subprocess.list2cmdline(command)
  sys.stdout.flush()
  sys.stderr.flush()
  return subprocess.call(command)


def sanitize_build_dir(s, build_dir_basename):
  """Replaces references to build directory in s with references to build_dir"""
  return re.sub(r'\b(?:out|build|xcodebuild)([\\/](?:Debug|Release))',
                build_dir_basename + r'\1', s)


def sanitize_isolated_file(isolated_file, build_dir_basename):
  """Crack open .isolated file and fix embedded paths, if necessary.

  isolates assume that they can embed the build directory at build time and
  still used that directory at test time. With a builder/tester setup, this
  isn't generally true, so rewrite the paths in the isolated file. See
  http://crbug.com/311622 for details. This can go away once all bots using
  isolates are using ninja.
  """
  # See the isolates file format description at:
  # https://code.google.com/p/swarming/wiki/IsolatedDesign#.isolated_file_format
  with open(isolated_file) as f:
    isolated_data = json.load(f)

  # 1. check version
  if isolated_data['version'] != '1.0':
    logging.error('Unexpected isolate version %s', isolated_data['version'])
    return 1

  # 2. fix command, print it
  for i in range(len(isolated_data['command'])):
    arg = isolated_data['command'][i]
    isolated_data['command'][i] = sanitize_build_dir(arg, build_dir_basename)

  # 3. fix files
  sanitized_files = {}
  for key, value in isolated_data['files'].iteritems():
    # a) fix key
    key = sanitize_build_dir(key, build_dir_basename)
    sanitized_files[key] = value
    # b) fix 'l' entry
    if 'l' in value:
      value['l'] = sanitize_build_dir(value['l'], build_dir_basename)
  isolated_data['files'] = sanitized_files

  # 4. Fix variables->PRODUCT_DIR if necessary (only present in the .cache file)
  variables = isolated_data.get('variables', {})
  if 'PRODUCT_DIR' in variables:
    variables['PRODUCT_DIR'] = sanitize_build_dir(variables['PRODUCT_DIR'],
                                                  build_dir_basename)

  # TODO(thakis): fix 'includes' if necessary.

  with open(isolated_file, 'w') as f:
    json.dump(isolated_data, f)


def run_test_isolated(isolate_script, test_exe, original_command):
  """Runs the test under isolate.py run.

  It compensates for discrepancies between sharding_supervisor.py arguments and
  run_test_cases.py arguments.

  The isolated file must be alongside the test executable, with the same
  name and the .isolated extension.
  """
  isolated_file = os.path.splitext(test_exe)[0] + '.isolated'

  if not os.path.exists(isolated_file):
    logging.error('No isolate file %s', isolated_file)
    return 1

  # '/path/to/src/out' -> 'out'
  build_dir_basename = os.path.basename(
      build_directory.GetBuildOutputDirectory())
  sanitize_isolated_file(isolated_file, build_dir_basename)

  # Update the .isolated.state cache too.
  cache_file = isolated_file + '.state'
  if os.path.exists(cache_file):
    sanitize_isolated_file(cache_file, build_dir_basename)

  isolate_command = [sys.executable, isolate_script,
                     'run', '--isolated', isolated_file,
                     # Print info log lines, so isolate.py prints the path to
                     # the binary it's about to run, http://crbug.com/311625
                     '-v']

  # Start setting the test specific options.
  isolate_command.append('--')
  isolate_command.append('--no-cr')
  original_command = original_command[:]
  while original_command:
    item = original_command.pop(0)
    if item == '--total-slave':
      isolate_command.extend(['--shards', original_command.pop(0)])
    elif item == '--slave-index':
      isolate_command.extend(['--index', original_command.pop(0)])
    elif item.startswith(('--gtest_filter', '--gtest_output')):
      isolate_command.append(item)

  return run_command(isolate_command)


def main(argv):
  option_parser = optparse.OptionParser(USAGE)
  option_parser.add_option('--test_name', default='',
                           help='The name of the test')
  option_parser.add_option('--builder_name', default='',
                           help='The name of the builder that created this'
                           'test')
  option_parser.add_option('--checkout_dir',
                           help='Checkout directory, used to locate the '
                           'swarm_client scripts.')
  option_parser.add_option('-f', '--force-isolated',  action='store_true',
                           help='Force test to run isolated. By default only '
                           'white listed builders and tests are run isolated.')
  option_parser.add_option('-v', '--verbose', action='count', default=0,
                           help='Use to increase log verbosity. Can be passed '
                           'in multiple times for more detailed logs.')

  options, args = option_parser.parse_args(argv)

  test_exe = args[0]
  original_command = args[1:]

  # Initialize logging.
  level = [logging.ERROR, logging.INFO, logging.DEBUG][min(2, options.verbose)]
  logging.basicConfig(level=level,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')

  if (options.force_isolated or
      should_run_as_isolated(options.builder_name, options.test_name)):
    logging.info('Running test in isolate mode')
    # Search first in swarming_client
    isolate_script = os.path.join(options.checkout_dir, 'src', 'tools',
                                  'swarming_client', 'isolate.py')

    # Remove around 2013-12-01.
    if not os.path.isfile(isolate_script):
      isolate_script = os.path.join(options.checkout_dir, 'src', 'tools',
                                    'swarm_client', 'isolate.py')
    return run_test_isolated(isolate_script, test_exe, original_command)
  else:
    logging.info('Running test normally')
    return run_command(original_command)


if '__main__' == __name__:
  sys.exit(main(None))
