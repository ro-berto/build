#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Dumps a list of known slaves, along with their OS and master."""

import os
import sys
path = os.path.join(os.path.dirname(__file__), os.path.pardir)
sys.path.append(path)
from common import chromium_utils


def main():
  slaves = []
  for master in chromium_utils.ListMasters():
    masterbase = os.path.basename(master)
    master_slaves = {}
    execfile(os.path.join(master, 'slaves.cfg'), master_slaves)
    for slave in master_slaves.get('slaves', []):
      slave['master'] = masterbase
    slaves.extend(master_slaves.get('slaves', []))
  for slave in sorted(slaves, cmp=None, key=lambda x : x.get('hostname', '')):
    slavename = slave.get('hostname')
    if not slavename:
      continue
    osname = slave.get('os', '?')
    print '%-30s %-35s %-10s' % (slavename, slave.get('master', '?'), osname)


if __name__ == '__main__':
  main()
