#!/usr/bin/env python

import os
import sys
path = os.path.join(os.path.dirname(__file__), os.path.pardir, 'common')
sys.path.append(path)
import chromium_utils

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
