#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script acts as the liason between the master and the swarming_client
code.

This helps with master restarts and when swarming_client is updated. It helps
support older versions of the client code, without having to complexify the
master code.
"""

import optparse
import os
import subprocess
import sys

from common import chromium_utils
from common import find_depot_tools  # pylint: disable=W0611

from slave.swarming import swarming_utils

# From depot tools/
import fix_encoding


PRIORITIES = {
  'ci': 10,
  'cq': 20,
  'fyi': 30,
  'tryjob': 40,
}


def v0(client, options):
  """Compatible up to the oldest swarm_client code."""
  cmd = [
    sys.executable,
    os.path.join(client, 'swarm_trigger_step.py'),
    '--swarm-url', options.swarming,
    '--data-server', options.isolate_server,
    '--os_image', options.os,
    '--test-name-prefix', options.task_prefix,
  ]
  for i in options.tasks:
    cmd.append('--run_from_hash')
    cmd.extend(i)

  print ' '.join(cmd)
  return subprocess.call(cmd, cwd=client)


def v0_1(client, options):
  """Code starting around r218375.

  TODO(maruel): Put exact revision once committe.d
  """
  cmd = [
    sys.executable,
    os.path.join(client, 'swarming.py'),
    'trigger',
    '--swarming', options.swarming,
    '--isolate-server', options.isolate_server,
    '--os', options.os,
    '--task-prefix', options.task_prefix,
    '--priority', str(PRIORITIES[options.type]),
  ]

  for i in options.tasks:
    cmd.append('--task')
    cmd.extend(i)

  # Enable profiling on the -dev server.
  if '-dev' in options.swarming:
    cmd.append('--profile')

  print ' '.join(cmd)
  return subprocess.call(cmd, cwd=client)


def determine_version_and_run_handler(client, options):
  """Executes the proper handler based on the code layout and --version support.
  """
  if os.path.isfile(os.path.join(client, 'swarm_get_results.py')):
    # Oh, that's old.
    return v0(client, options)
  return v0_1(client, options)


def process_build_properties(options):
  """Converts build properties and factory properties into expected flags."""
  options.task_prefix = '%s-%s-' % (
      options.build_properties.get('buildername'),
      options.build_properties.get('buildnumber'),
  )
  # target_os is not defined when using a normal builder (and it's not
  # needed since the OS match), it's defined in builder/tester configurations.
  options.os = options.build_properties.get('target_os', options.os)


def main():
  """Note: this is solely to run the current master's code and can totally
  differ from the underlying script flags.

  To update these flags:
  - Update the following code to support both the previous flag and the new
    flag.
  - Change scripts/master/factory/swarm_commands.py to pass the new flag.
  - Restart all the masters using swarming.
  - Remove the old flag from this code.
  """
  client = swarming_utils.find_client(os.getcwd())
  if not client:
    print >> sys.stderr, 'Failed to find swarm(ing)_client'
    return 1

  parser = optparse.OptionParser()
  parser.add_option(
      '--os', default=sys.platform,
      help='it\'s possible to trigger a task on an OS while the client code '
           'runs on another OS')
  parser.add_option('--swarming')
  parser.add_option('--isolate-server')
  parser.add_option('--task-prefix', help='task name prefix')
  parser.add_option(
      '--type',
      choices=sorted(PRIORITIES),
      default='fyi',
      help='Type of job will define it\'s priority')
  parser.add_option(
      '--task', nargs=4, action='append', default=[], dest='tasks')
  chromium_utils.AddPropertiesOptions(parser)
  options, args = parser.parse_args()
  if args:
    parser.error('Unsupported args: %s' % args)

  if options.build_properties:
    # Loads the other flags implicitly.
    process_build_properties(options)

  return determine_version_and_run_handler(client, options)


if __name__ == '__main__':
  fix_encoding.fix_encoding()
  sys.exit(main())
