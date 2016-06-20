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
from slave import logdog_bootstrap
from slave import monitoring_utils
from slave import robust_tempdir
from slave import update_scripts


LOGGER = logging.getLogger('remote_run')


def _call(cmd, **kwargs):
  LOGGER.info('Executing command: %s', cmd)
  exit_code = subprocess.call(cmd, **kwargs)
  LOGGER.info('Command %s finished with exit code %d.', cmd, exit_code)
  return exit_code


def _install_cipd_packages(path, *packages):
  """Bootstraps CIPD in |path| and installs requested |packages|.

  Args:
    path (str): The CIPD installation root.
    packages (list of CipdPackage): The set of CIPD packages to install.
  """
  cmd = [
      sys.executable,
      os.path.join(env.Build, 'scripts', 'slave', 'cipd.py'),
      '--dest-directory', path,
      '-vv' if logging.getLogger().level == logging.DEBUG else '-v',
  ]
  for p in packages:
    cmd += ['-P', '%s@%s' % (p.name, p.version)]

  exit_code = _call(cmd)
  if exit_code != 0:
    raise Exception('Failed to install CIPD packages.')


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

  group = parser.add_argument_group('LogDog Bootstrap')
  logdog_bootstrap.add_arguments(group)

  args = parser.parse_args(argv[1:])

  # Keep CIPD directory between builds.
  cipd_path = os.path.join(os.getcwd(), '.remote_run_cipd')
  _install_cipd_packages(
      cipd_path, cipd.CipdPackage('infra/recipes-py', 'latest'))

  with robust_tempdir.RobustTempdir(
      prefix='rr', leak=args.leak) as rt:
    try:
      basedir = chromium_utils.FindUpward(os.getcwd(), 'b')
    except chromium_utils.PathNotFound as e:
      LOGGER.warn(e)
      # Use base directory inside system temporary directory - if we use slave
      # one (cwd), the paths get too long. Recipes which need different paths
      # or persistent directories should do so explicitly.
      basedir = tempfile.gettempdir()

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
    properties_file = os.path.join(tempdir, 'remote_run_properties.json')
    with open(properties_file, 'w') as f:
      json.dump(properties, f)

    monitoring_utils.write_build_monitoring_event(build_data_dir, properties)

    recipe_cmd = [
        sys.executable,
        os.path.join(cipd_path, 'recipes.py'),
        '--verbose',
        'remote_run',
        '--repository', args.repository,
        '--revision', args.revision,
        '--workdir', os.path.join(tempdir, 'rw'),
        '--',
        '--properties-file', properties_file,
        '--workdir', os.path.join(tempdir, 'w'),
        args.recipe,
    ]
    # If we bootstrap through logdog, the recipe command line gets written
    # to a temporary file and does not appear in the log.
    LOGGER.info('Recipe command line: %r', recipe_cmd)
    recipe_return_code = None
    try:
      bs = logdog_bootstrap.bootstrap(rt, args, basedir, tempdir, properties,
                                      recipe_cmd)

      LOGGER.info('Bootstrapping through LogDog: %s', bs.cmd)
      _ = _call(bs.cmd)
      recipe_return_code = bs.get_result()
    except logdog_bootstrap.NotBootstrapped as e:
      LOGGER.info('Not bootstrapped: %s', e.message)
    except logdog_bootstrap.BootstrapError as e:
      LOGGER.warning('Could not bootstrap LogDog: %s', e.message)
    except Exception as e:
      LOGGER.exception('Exception while bootstrapping LogDog.')
    finally:
      if recipe_return_code is None:
        LOGGER.info('Not using LogDog. Invoking `recipes.py` directly.')
        recipe_return_code = _call(recipe_cmd)
    return recipe_return_code


def shell_main(argv):
  logging.basicConfig(
      level=(logging.DEBUG if '--verbose' in argv else logging.INFO))

  if update_scripts.update_scripts():
    # Re-execute with the updated remote_run.py.
    return _call([sys.executable] + argv)

  return main(argv)


if __name__ == '__main__':
  sys.exit(shell_main(sys.argv))
