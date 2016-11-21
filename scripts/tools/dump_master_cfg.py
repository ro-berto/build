#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Dumps master config as JSON.

Uses master_cfg_utils.LoadConfig, which should be called at most once
in the same process. That's why this is a separate utility.
"""

import argparse
import json
import os
import subprocess
import sys

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir))
if not SCRIPTS_DIR in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from common import env

env.Install()

from common import master_cfg_utils
from master.factory.build_factory import BuildFactory

SELF = sys.argv[0]


class BuildbotJSONEncoder(json.JSONEncoder):
  def default(self, obj):  # pylint: disable=E0202
    if isinstance(obj, BuildFactory):
      return {'repr': repr(obj), 'properties': obj.properties.asDict()}

    return repr(obj)


def _dump_master((name, path)):
  data = subprocess.check_output(
      [sys.executable, SELF, path, '-'])
  try:
    return (name, json.loads(data))
  except Exception as e:
    return (name, e)


def dump_all_masters(glob):
  # Selective imports. We do this here b/c "dump_master_cfg" is part of
  # a lot of production paths, and we don't want random import/pathing errors
  # to break that.
  import fnmatch
  import multiprocessing

  import config_bootstrap
  from slave import bootstrap

  # Homogenize master names: remove "master." from glob if present. We'll do the
  # same with master names.
  def strip_prefix(v, pfx):
    if v.startswith(pfx):
      v = v[len(pfx):]
    return v
  glob = strip_prefix(glob, 'master.')

  bootstrap.ImportMasterConfigs(include_internal=True)
  all_masters = {
      strip_prefix(os.path.basename(mc.local_config_path), 'master.'): mc
      for mc in config_bootstrap.Master.get_all_masters()}

  pool = multiprocessing.Pool(multiprocessing.cpu_count())
  m = dict(pool.map(_dump_master, (
      (k, v.local_config_path) for k, v in sorted(all_masters.items())
      if fnmatch.fnmatch(k, glob))))
  pool.close()
  pool.join()

  for k, v in sorted(m.items()):
    if isinstance(v, Exception):
      print >>sys.stderr, 'Failed to load JSON from %s: %s' % (k, v)
      m[k] = None

  return m


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('-m', '--multi', action='store_true',
      help='If specified, produce multi-master format and interpret the '
           '"master" argument as a glob expression of masters to match.')
  parser.add_argument('master',
      help='The path of the master to dump. If "*" is provided, produce a '
           'multi-master-format output list of all master configs.')
  parser.add_argument('output', type=argparse.FileType('w'), default=sys.stdout)

  args = parser.parse_args(argv)

  if args.multi:
    data = dump_all_masters(args.master)
  else:
    data = master_cfg_utils.LoadConfig(args.master)['BuildmasterConfig']

  json.dump(data,
            args.output,
            cls=BuildbotJSONEncoder,
            indent=4,
            sort_keys=True)
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
