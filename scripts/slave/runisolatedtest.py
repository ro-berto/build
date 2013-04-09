#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run a chrome test executable directly, or in isolated mode."""

import logging
import optparse
import os
import sys

from common import chromium_utils


USAGE = ('%s [options] /full/path/to/test.exe -- [original test command]' %
         os.path.basename(sys.argv[0]))

ISOLATE_ENABLED_TESTS = {
    # Uncomment once these once the .isolated files can handle moving machines.
    #'Linux Tests': 'base_unittests',
    #'linux_rel': 'base_unittests',
    #'Vista Tests (2)': 'base_unittests',
    #'Win 7 Tests x64 (2)': 'base_unittests',
    #'win_rel': 'base_unittests',
    #'Win7 Tests (2)': 'base_unittests',
    #'XP Tests (2)': 'base_unittests',
}


def should_run_as_isolated(builder_name, test_name):
  logging.info('should_run_as_isolated(%s, %s)' % (builder_name, test_name))

  return test_name in ISOLATE_ENABLED_TESTS.get(builder_name, ())


def run_test_isolated(isolate_script, test_exe, original_command):
  # The isolated file should be alongside the test executable, with the same
  # name and the .isolated extension.
  isolated_file = os.path.splitext(test_exe)[0] + '.isolated'

  if not os.path.exists(isolated_file):
    logging.error('No isolate file %s', isolated_file)
    return 1

  isolate_command = [sys.executable, isolate_script,
                     'run', '--isolated', isolated_file]

  # Start setting the test specific options.
  isolate_command.append('--')
  isolate_command.append('--no-cr')

  # Convert any commands from the original command that are understood.
  if ('--total-slave' in original_command and
      '--slave-index' in original_command):
    total_count_pos = original_command.index('--total_slave') + 1
    index_pos = original_command.index('--slave-index') + 1
    isolate_command.extend(['--shards', original_command[total_count_pos],
                            '--index', original_command[index_pos]])

  return chromium_utils.RunCommand(isolate_command)


def main():
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

  options, args = option_parser.parse_args()

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
    return chromium_utils.RunCommand(original_command)


if '__main__' == __name__:
  sys.exit(main())
