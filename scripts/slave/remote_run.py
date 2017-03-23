#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import collections
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

from common import annotator
from common import chromium_utils
from common import env
from slave import cipd
from slave import infra_platform
from slave import logdog_bootstrap
from slave import monitoring_utils
from slave import robust_tempdir
from slave import update_scripts


# BuildBot root directory: /b
BUILDBOT_ROOT = os.path.abspath(os.path.dirname(BUILD_ROOT))


LOGGER = logging.getLogger('remote_run')

# Masters in this list will use the canary path.
_CANARY_MASTERS = set((
  'chromium.infra',
  'chromium.infra.cron',
  'internal.infra',

  ## Not whitelisted b/c of recipe roller, see: crbug.com/703352
  #'internal.infra.cron',

  'chromium.swarm',
))

# The name of the recipe engine CIPD package.
_RECIPES_PY_CIPD_PACKAGE = 'infra/recipes-py'
# The name of the Kitchen CIPD package.
_KITCHEN_CIPD_PACKAGE = 'infra/tools/luci/kitchen/${platform}'

# _CIPD_PINS is a mapping of master name to pinned CIPD package version to use
# for that master.
#
# If "kitchen" pin is empty, use the traditional "recipes.py" invocation path.
# Otherwise, use Kitchen.
# TODO(dnj): Remove this logic when Kitchen is always enabled.
CipdPins = collections.namedtuple('CipdPins', ('recipes', 'kitchen'))

# Stable CIPD pin set.
_STABLE_CIPD_PINS = CipdPins(
      recipes='git_revision:3125a3b89e18dff89cf6d59f0a0486d832521bf1',
      kitchen='')

# Canary CIPD pin set.
_CANARY_CIPD_PINS = CipdPins(
      recipes='git_revision:3125a3b89e18dff89cf6d59f0a0486d832521bf1',
      kitchen='git_revision:b4507cd464bcbbda2e506a30fcf2c5ba01813d2c')


def _get_cipd_pins(mastername, force_canary):
  return (_CANARY_CIPD_PINS if force_canary or (mastername in _CANARY_MASTERS)
          else _STABLE_CIPD_PINS)


def all_cipd_packages():
  """Generator which yields all referenced CIPD packages."""
  # All CIPD packages are in top-level platform config.
  for pins in (_STABLE_CIPD_PINS, _CANARY_CIPD_PINS):
    yield cipd.CipdPackage(name=_RECIPES_PY_CIPD_PACKAGE, version=pins.recipes)
    if pins.kitchen: # TODO(dnj): Remove me when everything runs on Kitchen.
      yield cipd.CipdPackage(name=_KITCHEN_CIPD_PACKAGE, version=pins.kitchen)


# ENGINE_FLAGS is a mapping of master name to a engine flags. This can be used
# to test new recipe engine flags on a select few masters.
_ENGINE_FLAGS = {
  # None is the default set of engine flags, and is used if nothing else
  # matches. It MUST be defined.
  None: {
    'engine_flags': {
      'use_result_proto': True,
    }
  },

  'chromium.fyi': {
    'engine_flags': {
      'use_result_proto': True,
    }
  },
  'tryserver.chromium.linux': {
    'engine_flags': {
      'use_result_proto': True,
    }
  },
}

def _get_engine_flags(mastername):
  return  _ENGINE_FLAGS.get(mastername, _ENGINE_FLAGS[None])


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
  # Build our CIPD manifest. We'll pass it via STDIN.
  manifest = '\n'.join('%s %s' % (pkg.name, pkg.version) for pkg in packages)

  cmd = [
      'cipd' + infra_platform.exe_suffix(), # TODO(dnj): Is the suffix needed?
      'ensure',
      '-ensure-file', '-',
      '-root', path,
  ]

  LOGGER.info('Executing CIPD command: %s\nManifest:\n%s', cmd, manifest)
  proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
  stdout, _ = proc.communicate(input=manifest)
  if proc.returncode != 0:
    LOGGER.error('CIPD exited with non-zero return code (%s):\n%s',
        proc.returncode, stdout)
    raise ValueError('Failed to install CIPD packages (%d)' % (
        proc.returncode,))


def _rename_or_delete(src, dst):
  if not os.path.isdir(src):
    return
  if os.path.isdir(dst):
    LOGGER.info('Removing legacy [%s] in favor of [%s]', src, dst)
    chromium_utils.RemoveDirectory(src)
  else:
    LOGGER.info('Moving [%s] => [%s]', src, dst)
    chromium_utils.MoveFile(src, dst)


def _remote_run_with_kitchen(args, stream, pins, properties, tempdir, basedir):
  # Write our build properties to a JSON file.
  properties_file = os.path.join(tempdir, 'remote_run_properties.json')
  with open(properties_file, 'w') as f:
    json.dump(properties, f)

  # "/b/c" as a cache directory.
  cache_dir = os.path.join(BUILDBOT_ROOT, 'c')
  try:
    # Kitchen-style paths use a Git cache directory named 'git'. However,
    # traditional paths use 'git_cache'. We will try and convert these paths
    # and, failing that, delete the original one.
    _rename_or_delete(os.path.join(cache_dir, 'git_cache'),
                      os.path.join(cache_dir, 'git'))
  except Exception as e:
    LOGGER.error('Failed to update Git cache paths: %s', e)

  # Create our directory structure.
  recipe_temp_dir = os.path.join(tempdir, 't')
  os.makedirs(recipe_temp_dir)

  # Use CIPD to download Kitchen to a root within the temporary directory.
  cipd_root = os.path.join(basedir, '.remote_run_cipd')
  recipes_pkg = cipd.CipdPackage(
      name=_RECIPES_PY_CIPD_PACKAGE,
      version=pins.recipes)
  kitchen_pkg = cipd.CipdPackage(
      name=_KITCHEN_CIPD_PACKAGE,
      version=pins.kitchen)

  _install_cipd_packages(cipd_root, kitchen_pkg, recipes_pkg)

  kitchen_bin = os.path.join(cipd_root, 'kitchen' + infra_platform.exe_suffix())

  kitchen_cmd = [
      kitchen_bin,
      '-log-level', ('debug' if LOGGER.isEnabledFor(logging.DEBUG) else 'info'),
  ]

  recipe_result_path = os.path.join(tempdir, 'recipe_result.json')
  kitchen_cmd += [
      'cook',
      '-mode', 'buildbot',
      '-recipe-engine-path', cipd_root,
      '-output-result-json', recipe_result_path,
      '-properties-file', properties_file,
      '-recipe', args.recipe or properties.get('recipe'),
      '-repository', args.repository,
      '-cache-dir', cache_dir,
      '-temp-dir', recipe_temp_dir,
      '-checkout-dir', os.path.join(tempdir, 'rw'),
      '-workdir', os.path.join(tempdir, 'w'),
  ]

  # Add additional system Python paths. Ideally, none of these would be
  # required, since our remote checkout should be self-sufficient. Each of these
  # should be viewed as a hermetic breach.
  for python_path in [
      os.path.join(BUILD_ROOT, 'scripts'),
      os.path.join(BUILD_ROOT, 'site_config'),
      ]:
    kitchen_cmd += ['-python-path', python_path]

  # Master "remote_run" factory has been changed to pass "refs/heads/master" as
  # a default instead of "origin/master". However, this is a master-side change,
  # and requires a master restart. Rather than restarting all masters, we will
  # just pretend the change took effect here.
  #
  # No "-revision" means "latest", which is the same as "origin/master"'s
  # meaning.
  #
  # See: https://chromium-review.googlesource.com/c/446895/
  # See: crbug.com/696704
  #
  # TODO(dnj,nodir): Delete this once we're confident that all masters have been
  # restarted to take effect.
  if args.revision and (args.revision != 'origin/master'):
    kitchen_cmd += ['-revision', args.revision]

  # Using LogDog?
  try:
    # Load bootstrap configuration (may raise NotBootstrapped).
    cfg = logdog_bootstrap.get_config(args, properties)
    annotation_url = logdog_bootstrap.get_annotation_url(cfg)

    if cfg.logdog_only:
      kitchen_cmd += ['-logdog-only']

    kitchen_cmd += [
        '-logdog-annotation-url', annotation_url,
    ]

    # (Debug) Use Kitchen output file if in debug mode.
    if args.logdog_debug_out_file:
      kitchen_cmd += ['-logdog-debug-out-file', args.logdog_debug_out_file]

    logdog_bootstrap.annotate(cfg, stream)
  except logdog_bootstrap.NotBootstrapped as e:
    LOGGER.info('Not configured to use LogDog: %s', e)

  # Invoke Kitchen, capture its return code.
  recipe_return_code = _call(kitchen_cmd)

  # Try to open recipe result JSON. Any failure will result in an exception
  # and an infra failure.
  #
  # On success, it may be JSON "null", so use an empty dict.
  with open(recipe_result_path) as f:
    return_value = json.load(f) or {}

  # If we failed, but aren't a step failure, we assume it was an
  # exception.
  f = return_value.get('failure', {})
  if any(f.get(typ) for typ in ('timeout', 'step_data')):
    # Return an infra failure for these failure types.
    #
    # The recipe engine used to return -1, which got interpreted as 255 by
    # os.exit in python, since process exit codes are a single byte.
    recipe_return_code = 255

  return recipe_return_code


def _exec_recipe(args, rt, stream, basedir):
  tempdir = rt.tempdir(basedir)
  LOGGER.info('Using temporary directory: [%s].', tempdir)

  build_data_dir = rt.tempdir(basedir)
  LOGGER.info('Using build data directory: [%s].', build_data_dir)

  # Construct our properties.
  properties = copy.copy(args.factory_properties)
  properties.update(args.build_properties)

  # Determine our pins.
  mastername = properties.get('mastername')
  pins = _get_cipd_pins(mastername,
                        args.canary or 'remote_run_canary' in properties)
  if args.kitchen:
    pins = pins._replace(kitchen=args.kitchen)
  legacy_remote_run = not pins.kitchen

  # Augment our input properties...
  properties['build_data_dir'] = build_data_dir
  properties['builder_id'] = 'master.%s:%s' % (
    mastername, properties['buildername'])

  if legacy_remote_run:
    # path_config property defines what paths a build uses for checkout, git
    # cache, goma cache, etc.
    # Unless it is explicitly specified by a builder, use paths for buildbot
    # environment.
    properties['path_config'] = properties.get('path_config', 'buildbot')
    properties['bot_id'] = properties['slavename']
  else:
    # If we're using Kitchen, our "path_config" must be empty or "kitchen".
    path_config = properties.pop('path_config', None)
    if path_config and path_config != 'kitchen':
      raise ValueError("Users of 'remote_run.py' MUST specify either 'kitchen' "
                       "or no 'path_config', not [%s]." % (path_config,))

  LOGGER.info('Using properties: %r', properties)

  monitoring_utils.write_build_monitoring_event(build_data_dir, properties)

  # Ensure that the CIPD client is installed and available on PATH.
  from slave import cipd_bootstrap_v2
  cipd_bootstrap_v2.high_level_ensure_cipd_client(
    basedir, properties.get(mastername))

  # Make switching to remote_run easier: we do not use buildbot workdir,
  # and it takes disk space leading to out of disk errors.
  buildbot_workdir = properties.get('workdir')
  if buildbot_workdir:
    try:
      if os.path.exists(buildbot_workdir):
        buildbot_workdir = os.path.realpath(buildbot_workdir)
        cwd = os.path.realpath(os.getcwd())
        if cwd.startswith(buildbot_workdir):
          buildbot_workdir = cwd

        LOGGER.info('Cleaning up buildbot workdir %r', buildbot_workdir)

        # Buildbot workdir is usually used as current working directory,
        # so do not remove it, but delete all of the contents. Deleting
        # current working directory of a running process may cause
        # confusing errors.
        for p in (os.path.join(buildbot_workdir, x)
                  for x in os.listdir(buildbot_workdir)):
          LOGGER.info('Deleting %r', p)
          chromium_utils.RemovePath(p)
    except Exception as e:
      # It's preferred that we keep going rather than fail the build
      # on optional cleanup.
      LOGGER.exception('Buildbot workdir cleanup failed: %s', e)

  # (Canary) Use Kitchen if configured.
  # TODO(dnj): Make this the only path once we move to Kitchen.
  if not legacy_remote_run:
    return _remote_run_with_kitchen(args, stream, pins, properties, tempdir,
        basedir)

  ##
  # Classic Remote Run
  #
  # TODO(dnj): Delete this in favor of Kitchen.
  ##

  cache_dir = os.path.join(BUILDBOT_ROOT, 'c')
  try:
    # Kitchen-style paths use a Git cache directory named 'git'. However,
    # traditional paths use 'git_cache'. If we deployed a Kitchen-style cache
    # on this bot, convert it back to a non-Kitchen cache.
    _rename_or_delete(os.path.join(cache_dir, 'git'),
                      os.path.join(cache_dir, 'git_cache'))
  except Exception as e:
    LOGGER.error('Failed to revert Git cache paths: %s', e)

  properties_file = os.path.join(tempdir, 'remote_run_properties.json')
  with open(properties_file, 'w') as f:
    json.dump(properties, f)

  cipd_path = os.path.join(basedir, '.remote_run_cipd')

  _install_cipd_packages(cipd_path,
      cipd.CipdPackage(_RECIPES_PY_CIPD_PACKAGE, pins.recipes))

  engine_flags = _get_engine_flags(mastername)

  engine_args = []
  if engine_flags:
    engine_flags_path = os.path.join(tempdir, 'engine_flags.json')
    with open(engine_flags_path, 'w') as f:
      json.dump(engine_flags, f)

    engine_args = ['--operational-args-path', engine_flags_path]

  recipe_result_path = os.path.join(tempdir, 'recipe_result.json')
  recipe_cmd = [
      sys.executable,
      os.path.join(cipd_path, 'recipes.py'),] + engine_args + [
      '--verbose',
      'remote',
      '--repository', args.repository,
      '--workdir', os.path.join(tempdir, 'rw'),
  ]
  if args.revision:
    recipe_cmd.extend(['--revision', args.revision])
  if args.use_gitiles:
    recipe_cmd.append('--use-gitiles')
  recipe_cmd.extend([
      '--',] + (
      engine_args) + [
      '--verbose',
      'run',
      '--properties-file', properties_file,
      '--workdir', os.path.join(tempdir, 'w'),
      '--output-result-json', recipe_result_path,
      properties.get('recipe') or args.recipe,
  ])
  # If we bootstrap through logdog, the recipe command line gets written
  # to a temporary file and does not appear in the log.
  LOGGER.info('Recipe command line: %r', recipe_cmd)

  # Default to return code != 0 is for the benefit of buildbot, which uses
  # return code to decide if a step failed or not.
  recipe_return_code = 1
  try:
    bs = logdog_bootstrap.bootstrap(rt, args, basedir, tempdir, properties,
                                    recipe_cmd)

    LOGGER.info('Bootstrapping through LogDog: %s', bs.cmd)
    bs.annotate(stream)
    _ = _call(bs.cmd)
    recipe_return_code = bs.get_result()
  except logdog_bootstrap.NotBootstrapped as e:
    LOGGER.info('Not using LogDog. Invoking `recipes.py` directly.')
    recipe_return_code = _call(recipe_cmd)

  # Try to open recipe result JSON. Any failure will result in an exception
  # and an infra failure.
  with open(recipe_result_path) as f:
    return_value = json.load(f)

  if engine_flags.get('use_result_proto'):
    # If we failed, but aren't a step failure, we assume it was an
    # exception.
    f = return_value.get('failure')
    if f is not None and not f.get('step_failure'):
      # The recipe engine used to return -1, which got interpreted as 255
      # by os.exit in python, since process exit codes are a single byte.
      recipe_return_code = 255

  return recipe_return_code


def main(argv, stream):
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
  parser.add_argument('--canary', action='store_true',
      help='Force use of canary configuration.')
  parser.add_argument('--kitchen', metavar='CIPD_VERSION',
      help='Force use of Kitchen bootstrapping at this revision.')
  parser.add_argument('--verbose', action='store_true')
  parser.add_argument(
      '--use-gitiles', action='store_true',
      help='Use Gitiles-specific way to fetch repo (faster for large repos)')

  group = parser.add_argument_group('LogDog Bootstrap')
  logdog_bootstrap.add_arguments(group)

  args = parser.parse_args(argv[1:])

  try:
    basedir = chromium_utils.FindUpward(os.getcwd(), 'b')
  except chromium_utils.PathNotFound as e:
    LOGGER.warn(e)
    # Use base directory inside system temporary directory - if we use slave
    # one (cwd), the paths get too long. Recipes which need different paths
    # or persistent directories should do so explicitly.
    basedir = tempfile.gettempdir()

  # Choose a tempdir prefix. If we have no active subdir, we will use a prefix
  # of "rr". If we have an active subdir, we will use "rs/<subdir>". This way,
  # there will be no tempdir collisions between combinations of the two
  # sitautions.
  active_subdir = chromium_utils.GetActiveSubdir()
  if active_subdir:
    prefix = os.path.join('rs', str(active_subdir))
  else:
    prefix = 'rr'

  with robust_tempdir.RobustTempdir(prefix, leak=args.leak) as rt:
    # Explicitly clean up possibly leaked temporary directories
    # from previous runs.
    rt.cleanup(basedir)
    return _exec_recipe(args, rt, stream, basedir)


def shell_main(argv):
  logging.basicConfig(
      level=(logging.DEBUG if '--verbose' in argv else logging.INFO))

  if update_scripts.update_scripts():
    # Re-execute with the updated remote_run.py.
    return _call([sys.executable] + argv)

  stream = annotator.StructuredAnnotationStream()
  exc_info = None
  try:
    return main(argv, stream)
  except Exception:
    exc_info = sys.exc_info()

  # Report on the "remote_run" execution. If an exception (infra failure)
  # occurred, raise it so that the build and the step turn purple.
  with stream.step('remote_run_result'):
    if exc_info is not None:
      raise exc_info[0], exc_info[1], exc_info[2]


if __name__ == '__main__':
  sys.exit(shell_main(sys.argv))
