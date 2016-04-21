#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import copy
import json
import logging
import os
import subprocess
import sys
import tempfile


# Install Infra build environment.
BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BUILD_ROOT, 'scripts'))

from common import chromium_utils
from common import env
from slave import cipd
from slave import infra_platform
from slave import robust_tempdir
from slave import update_scripts


LOGGER = logging.getLogger('kitchen_run')


KITCHEN_CIPD_VERSION = 'latest'


CIPD_BINARIES = {
  ('linux', 32): cipd.CipdBinary(
      cipd.CipdPackage('infra/tools/luci/kitchen/linux-386',
                       KITCHEN_CIPD_VERSION),
      'kitchen'),
  ('linux', 64): cipd.CipdBinary(
      cipd.CipdPackage('infra/tools/luci/kitchen/linux-amd64',
                       KITCHEN_CIPD_VERSION),
      'kitchen'),
  ('mac', 64): cipd.CipdBinary(
      cipd.CipdPackage('infra/tools/luci/kitchen/mac-amd64',
                       KITCHEN_CIPD_VERSION),
      'kitchen'),
  ('win', 32): cipd.CipdBinary(
      cipd.CipdPackage('infra/tools/luci/kitchen/windows-386',
                       KITCHEN_CIPD_VERSION),
      'kitchen.exe'),
  ('win', 64): cipd.CipdBinary(
      cipd.CipdPackage('infra/tools/luci/kitchen/windows-amd64',
                       KITCHEN_CIPD_VERSION),
      'kitchen.exe'),
}


def _call(cmd, **kwargs):
  LOGGER.info('Executing command: %s', cmd)
  exit_code = subprocess.call(cmd, **kwargs)
  LOGGER.info('Command %s finished with exit code %d.', cmd, exit_code)
  return exit_code


def _install_cipd_packages(path, *binaries):
  """Bootstraps CIPD in |path| and installs requested |binaries|.

  Args:
    path (str): The CIPD installation root.
    binaries (list of CipdBinary): The set of CIPD binaries to install.

  Returns (list): The paths to the binaries.
  """
  cmd = [
      sys.executable,
      os.path.join(env.Build, 'scripts', 'slave', 'cipd.py'),
      '--dest-directory', path,
      '-vv' if logging.getLogger().level == logging.DEBUG else '-v',
  ]
  for b in binaries:
    cmd += ['-P', '%s@%s' % (b.package.name, b.package.version)]

  exit_code = _call(cmd)
  if exit_code != 0:
    raise Exception('Failed to install CIPD packages.')
  return [os.path.join(path, b.relpath) for b in binaries]


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--repository', required=True,
      help='URL of a git repository to fetch.')
  parser.add_argument('--revision',
      help='Git commit hash to check out.')
  parser.add_argument('--recipe', required=True,
      help='Name of the recipe to run')
  parser.add_argument('--build-properties-gz', dest='build_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='Build properties in b64 gz JSON format')
  parser.add_argument('--factory-properties-gz', dest='factory_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='factory properties in b64 gz JSON format')
  parser.add_argument('--leak', action='store_true',
      help='Refrain from cleaning up generated artifacts.')
  parser.add_argument('--verbose', action='store_true')
  args = parser.parse_args(argv[1:])

  basedir = os.getcwd()
  cipd_path = os.path.join(basedir, '.kitchen_cipd')
  (kitchen,) = _install_cipd_packages(
      cipd_path, CIPD_BINARIES[infra_platform.get()])

  with robust_tempdir.RobustTempdir(
      prefix='.kitchen_run', leak=args.leak) as rt:
    # Explicitly clean up possibly leaked temporary directories
    # from previous runs.
    rt.cleanup(basedir)

    tempdir = rt.tempdir(basedir)
    LOGGER.info('Using temporary directory: [%s].', tempdir)

    build_data_dir = rt.tempdir(basedir)
    LOGGER.info('Using build data directory: [%s].', build_data_dir)

    properties = copy.copy(args.factory_properties)
    properties.update(args.build_properties)
    properties['build_data_dir'] = build_data_dir
    LOGGER.info('Using properties: %r', properties)
    properties_file = os.path.join(tempdir, 'kitchen_properties.json')
    with open(properties_file, 'w') as f:
      json.dump(properties, f)

    return _call([
        kitchen, 'cook',
        '-repository', args.repository,
        '-revision', args.revision,
        '-recipe', args.recipe,
        '-properties-file', properties_file,
        '-workdir', tempdir,
    ])


def shell_main(argv):
  logging.basicConfig(
      level=(logging.DEBUG if '--verbose' in argv else logging.INFO))

  if update_scripts.update_scripts():
    # Re-execute with the updated kitchen_run.py.
    return _call([sys.executable] + argv)

  return main(argv)


if __name__ == '__main__':
  sys.exit(shell_main(sys.argv))
