#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Ensure that all slave configurations are well formed."""

import contextlib
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

from common import chromium_utils

sys.path.pop(0)


@contextlib.contextmanager
def using_sys_path(path):
  orig_sys_path = sys.path
  try:
    sys.path = path
    yield
  finally:
    sys.path = orig_sys_path


# List of slaves that are allowed to be used more than once.
WHITELIST = ['build1-m6']

def main():
  # Get public slaves.
  slaves_list = chromium_utils.GetAllSlaves(
      fail_hard=True,
      include_internal=False)

  # Get internal slaves, if appropriate.
  build_internal = os.path.join(BASE_DIR, '..', 'build_internal')
  if os.path.exists(build_internal):
    internal_test_data = chromium_utils.ParsePythonCfg(
        os.path.join(build_internal, 'tests', 'internal_masters_cfg.py'),
        fail_hard=True)
    internal_cfg = internal_test_data['masters_cfg_test']
    internal_sys_path = [os.path.join(build_internal, p)
                         for p in internal_cfg['paths']] + sys.path
    with using_sys_path(internal_sys_path):
      slaves_list.extend(chromium_utils.GetAllSlaves(
          fail_hard=True,
          include_public=False))

  status = 0
  slaves = {}
  for slave in slaves_list:
    mastername = slave['mastername']
    slavename = chromium_utils.EntryToSlaveName(slave)
    if slave.get('subdir') == 'b':
      print 'Illegal subdir for %s: %s' % (mastername, slavename)
      status = 1
    if slavename and slave.get('hostname') not in WHITELIST:
      slaves.setdefault(slavename, []).append(mastername)
  for slavename, masters in slaves.iteritems():
    if len(masters) > 1:
      print '%s duplicated in masters: %s' % (slavename, ' '.join(masters))
      status = 1
  return status

if __name__ == '__main__':
  sys.exit(main())
