#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run a chrome test executable directly, or in isolated mode."""

import logging
import optparse
import os
import subprocess
import sys


USAGE = ('%s [options] /full/path/to/test.exe -- [original test command]' %
         os.path.basename(sys.argv[0]))

ISOLATE_ENABLED_TESTS = (
  'base_unittests',
  'net_unittests',
)

ISOLATE_ENABLED_BUILDERS = {
  # CI linux
  'Linux Tests': ISOLATE_ENABLED_TESTS,
  # CI mac
  #'Mac10.6 Tests (1)': ISOLATE_ENABLED_TESTS,
  #'Mac10.7 Tests (1)': ISOLATE_ENABLED_TESTS,
  # CI win
  'Vista Tests (2)': ISOLATE_ENABLED_TESTS,
  'Win7 Tests (2)': ISOLATE_ENABLED_TESTS,
  'XP Tests (2)': ISOLATE_ENABLED_TESTS,

  # Try Server
  'linux_rel': ISOLATE_ENABLED_TESTS,
  'mac_rel': ISOLATE_ENABLED_TESTS,
  'win_rel': ISOLATE_ENABLED_TESTS,
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


def run_test_isolated(isolate_script, test_exe, original_command):
  """Runs the test under isolate.py run.

  It compensates for discrepencies between sharding_supervisor.py arguments and
  run_test_cases.py arguments.

  The isolated file must be alongside the test executable, with the same
  name and the .isolated extension.
  """
  isolated_file = os.path.splitext(test_exe)[0] + '.isolated'

  if not os.path.exists(isolated_file):
    logging.error('No isolate file %s', isolated_file)
    return 1

  isolate_command = [sys.executable, isolate_script,
                     'run', '--isolated', isolated_file]

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
  option_parser.add_option('--tool_dir', default='',
                           help='The location tools directory, used to located '
                           'the isolate scripts.')
  option_parser.add_option('-v', '--verbose', action='count', default=0,
                           help='Use to increase log verbosity. Can be passed '
                           'in multiple time for more logs.')

  options, args = option_parser.parse_args(argv)

  test_exe = args[0]
  original_command = args[1:]

  # Initialize logging.
  level = [logging.ERROR, logging.INFO, logging.DEBUG][min(2, options.verbose)]
  logging.basicConfig(level=level,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')

  if should_run_as_isolated(options.builder_name, options.test_name):
    logging.info('Running test in isolate mode')
    isolate_script = os.path.join(options.tool_dir, 'swarm_client',
                                  'isolate.py')
    return run_test_isolated(isolate_script, test_exe, original_command)
  else:
    logging.info('Running test normally')
    return run_command(original_command)


if '__main__' == __name__:
  sys.exit(main(None))
