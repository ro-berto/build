#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Dumps a list of known slaves, along with their OS and master."""

import argparse
import collections
import json
import logging
import os
import subprocess
import sys

# This file is located inside tests. Update this path if that changes.
BUILD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BUILD, 'scripts')
LIST_SLAVES = os.path.join(SCRIPTS, 'tools', 'list_slaves.py')

sys.path.append(SCRIPTS)

from common import chromium_utils


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    '-g',
    '--gen',
    '--generate',
    action='store_true',
    dest='generate',
    help='Generate slaves.expected for all masters.',
  )
  args = parser.parse_args()

  masters = chromium_utils.ListMastersWithSlaves()
  master_map = {}

  for master_path in masters:
    # Convert ~/<somewhere>/master.<whatever> to just whatever.
    master = os.path.basename(master_path).split('.', 1)[-1]
    botmap = json.loads(subprocess.check_output([
        LIST_SLAVES, '--json', '--master', master]))

    slave_map = collections.defaultdict(set)

    for entry in botmap:
      assert entry['mastername'] == 'master.%s' % master

      for builder in entry['builder']:
        slave_map[builder].add(entry['hostname'])

    master_map[master_path] = {}

    for buildername in sorted(slave_map.keys()):
      master_map[master_path][buildername] = sorted(slave_map[buildername])

  retcode = 0

  for master_path, slaves_expectation in master_map.iteritems():
    if os.path.exists(master_path):
      slaves_expectation_file = os.path.join(master_path, 'slaves.expected')

      if args.generate:
        with open(slaves_expectation_file, 'w') as fp:
          json.dump(slaves_expectation, fp, indent=2, sort_keys=True)
        print 'Wrote expectation: %s.' % slaves_expectation_file
      else:
        if os.path.exists(slaves_expectation_file):
          with open(slaves_expectation_file) as fp:
            if json.load(fp) != slaves_expectation:
              logging.error(
                  'Mismatched expectation: %s.', slaves_expectation_file)
              retcode = 1
        else:
          logging.error('File not found: %s.', slaves_expectation_file)
          retcode = 1

  return retcode


if __name__ == '__main__':
  sys.exit(main())
