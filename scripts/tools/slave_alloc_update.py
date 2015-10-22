#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Command-line tool to update slave allocation JSON for slave pools that are
managed by `<build>/scripts/common/slave_alloc.py`.

This script is directed at a master, and will:
  1) Load the master's `slaves.cfg` and process it.
  2) For each identified SlaveAllocator instance, regenerate the slave pool JSON
     file.
"""

import argparse
import logging
import os
import sys

import common.chromium_utils
import common.env
import common.slave_alloc


def _UpdateSlaveAlloc(master_dir, sa):
  logging.info('Updating slaves for master "%s": [%s]',
               os.path.basename(master_dir), sa.state_path)
  with common.chromium_utils.MasterEnvironment(master_dir):
    sa.SaveState()


def _UpdateMaster(master_name):
  master_dir = common.chromium_utils.MasterPath(master_name)
  slaves_cfg_path = os.path.join(os.path.abspath(master_dir), 'slaves.cfg')
  if not os.path.isfile(slaves_cfg_path):
    raise ValueError('Master directory does not contain "slaves.cfg": %s' % (
                     master_dir,))

  logging.debug('Loading "slaves.cfg" from: [%s]', slaves_cfg_path)
  cfg = common.chromium_utils.ParsePythonCfg(slaves_cfg_path, fail_hard=False)

  updated = False
  for name, sa in (cfg or {}).iteritems():
    if isinstance(sa, common.slave_alloc.SlaveAllocator):
      logging.debug('Identified slave allocator variable [%s]', name)
      _UpdateSlaveAlloc(master_dir, sa)
      updated = True
  return updated


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--verbose',
      action='count', default=0,
      help='Increase verbosity. This can be specified multiple times.')
  parser.add_argument('masters', metavar='NAME', nargs='+',
      help='Name of the master to update.')
  args = parser.parse_args(argv)

  # Configure logging verbosity.
  if args.verbose == 0:
    level = logging.WARNING
  elif args.verbose == 1:
    level = logging.INFO
  else:
    level = logging.DEBUG
  logging.getLogger().setLevel(level)

  # Update each master directory.
  for name in args.masters:
    if not _UpdateMaster(name):
      raise ValueError('No slave allocators identified for [%s]' % (name,))


if __name__ == '__main__':
  logging.basicConfig()
  try:
    sys.exit(main(sys.argv[1:]))
  except Exception as e:
    logging.exception('Uncaught exception encountered during execution: %s', e)
    sys.exit(2)
