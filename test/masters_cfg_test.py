#!/usr/bin/env python
# Copyright 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests all master.cfgs to make sure they load properly."""

import collections
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

import masters_util

from common import chromium_utils
from common import master_cfg_utils

# Masters which do not currently load from the default configuration. These need
# to be fixed and removed from the list!
BLACKLIST = set(['chromium.swarm',
                 'chromium.chromebot',
                 'chromiumos.tryserver',
                 'client.nacl.chrome'])


Cmd = collections.namedtuple('Cmd', ['name', 'path', 'env'])


def GetMasterCmds(masters, blacklist, pythonpaths):
  assert blacklist <= set(m for m, _ in masters)
  env = os.environ.copy()
  pythonpaths = list(pythonpaths or [])
  buildpaths = ['scripts', 'third_party', 'site_config']
  thirdpartypaths = ['buildbot_8_4p1', 'buildbot_slave_8_4', 'jinja2',
                     'mock-1.0.1', 'twisted_10_2']

  pythonpaths.extend(os.path.join(BASE_DIR, p) for p in buildpaths)
  pythonpaths.extend(os.path.join(BASE_DIR, 'third_party', p)
                     for p in thirdpartypaths)
  if env.get('PYTHONPATH'):
    pythonpaths.append(env.get('PYTHONPATH'))
  env['PYTHONPATH'] = os.pathsep.join(pythonpaths)

  return [Cmd(name, path, env)
      for name, path in masters if name not in blacklist]


def main(argv):
  start_time = time.time()
  num_skipped = len(BLACKLIST)
  master_list = GetMasterCmds(
      masters=master_cfg_utils.GetMasters(include_internal=False),
      blacklist=BLACKLIST,
      pythonpaths=None)
  build_internal = os.path.join(BASE_DIR, '..', 'build_internal')
  if os.path.exists(build_internal):
    internal_test_data = chromium_utils.ParsePythonCfg(os.path.join(
        build_internal, 'test', 'internal_masters_cfg.py'))
    internal_cfg = internal_test_data['masters_cfg_test']
    num_skipped += len(internal_cfg['blacklist'])
    master_list.extend(GetMasterCmds(
        masters=master_cfg_utils.GetMasters(include_public=False),
        blacklist=internal_cfg['blacklist'],
        pythonpaths=[os.path.join(build_internal, p)
                     for p in internal_cfg['paths']]))

  with masters_util.TemporaryMasterPasswords():
    processes = [subprocess.Popen([
      sys.executable, os.path.join(BASE_DIR, 'scripts', 'slave', 'runbuild.py'),
      cmd.name, '--test-config'], stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, env=cmd.env) for cmd in master_list]
    results = map(lambda x: (x.communicate()[0], x.returncode), processes)
    failures = [(cmd, out) for cmd, (out, r) in zip(master_list, results) if r]
    if failures:
      print 'The following master.cfgs did not load:'
      for command, output in failures:
        print '%s: %s' % (command.name, command.path)
        for line in output.splitlines():
          print '> ', line
      return 1
  print 'Parsed %d masters (%d skipped) in %gs.' % (
      len(master_list), num_skipped, round(time.time() - start_time, 1))


if __name__ == '__main__':
  sys.exit(main(sys.argv))
