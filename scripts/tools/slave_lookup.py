#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simple utility script to read slave names and output their information."""


import argparse
import json
import os
import sys

# Install infra environment.
SCRIPTS_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.pardir))
sys.path.insert(0, SCRIPTS_ROOT)
from common import env
env.Install()

from common import chromium_utils


def main(args):
  parser = argparse.ArgumentParser()
  parser.add_argument('-i', '--input', metavar='PATH',
      type=argparse.FileType('r'), default=None,
      help='Read slave names from this file (use - for STDIN).')
  parser.add_argument('slave_names', nargs='*',
      help='Individual names of slaves. Leave blank to read from STDIN.')
  opts = parser.parse_args(args)

  slave_names = set(opts.slave_names)
  if not slave_names and not opts.input:
    opts.input = sys.stdin
  if opts.input:
    slave_names.update(s.strip() for s in opts.input.read().split())
    opts.input.close()

  slaves = {}
  for path in chromium_utils.ListMastersWithSlaves():
    for slave in chromium_utils.GetSlavesFromMasterPath(path):
      hostname = slave.get('hostname')
      if hostname in slave_names:
        slaves[hostname] = slave

  json.dump(slaves, sys.stdout, indent=1, sort_keys=True)


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
