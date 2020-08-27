#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to check whether a target exists in the ninja build graph or not.

  Before this is run, ninja build files should already be generated or updated.

  For a list of command line options, call this script with '--help'.
"""

import json
import optparse
import os
import subprocess
import sys


def targets_exist(targets, target_build_dir, ninja_path):
  """Returns True if the given targets exist in the ninja build file.

  Args:
    targets (list): A list of target names.
    target_build_dir (str): The path to the target build directory.
    ninja_path (str): Path to the ninja executable.
  """
  print 'Checking targets: %s' % ', '.join(targets)
  cmd = [ninja_path, '-C', target_build_dir, '-t', 'query']
  cmd.extend(targets)
  with open(os.devnull, 'w') as f:  # Mute normal output, only care about error.
    p = subprocess.Popen(cmd, stdout=f)
  return_code = p.wait()
  print 'return code: %s' % return_code
  return return_code == 0


def check_targets(targets, target_build_dir, ninja_path):
  """Returns a dict with a list of existing targets.

  Args:
    targets (list): A list of target names.
    target_build_dir (str): The path to the target build directory.
  """
  found = []

  targets = sorted(set(targets))
  # Check all the targets at once first in one ninja command.
  # If a target among a few doesn't exist, ninja will exit with 1 immediately
  # and not process the remaining targets. In that case, we have to check them
  # one by one instead.
  all_existing = targets_exist(targets, target_build_dir, ninja_path)

  if all_existing:  # All targets exists.
    found = targets
  elif len(targets) > 1:  # At least one target does not exist.
    for target in targets:
      if targets_exist([target], target_build_dir, ninja_path):
        found.append(target)

  return {'found': found}


def parse_args():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--target-build-dir',
                           help='The target build directory. eg: out/Release.')
  option_parser.add_option('--ninja-path', default='ninja',
                           help='Path to the ninja executable.')
  option_parser.add_option('--target', action='append', default=[],
                           help='Specify the target to be checked. eg: '
                                'browser_tests, obj/path/to/Source.o, or '
                                'gen/path/to/generated.cc, etc.')
  option_parser.add_option('--json-output',
                           help='Optional. Specify a file to dump the result '
                                'as json.')
  options, _ = option_parser.parse_args()
  return (options.target_build_dir, options.target, options.json_output,
          options.ninja_path)


def main():
  target_build_dir, targets, json_output, ninja_path = parse_args()
  if not (target_build_dir and targets):
    print 'Invalid parameter.'
    print 'target-build-dir: %s' % target_build_dir
    print 'targets:'
    for target in targets:
      print '  %s' % target
    return 1

  result = check_targets(targets, target_build_dir, ninja_path)
  if json_output:
    with open(json_output, 'wb') as f:
      json.dump(result, f, indent=2)
  else:
    print json.dumps(result, indent=2)

  return 0


if __name__ == '__main__':
  sys.exit(main())
