#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import logging
import os
import subprocess
import sys


# Install Infra build environment.
BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BUILD_ROOT, 'scripts'))

from common import annotator
from common import chromium_utils
from common import env
from common import master_cfg_utils
from slave import logdog_bootstrap
from slave import monitoring_utils
from slave import robust_tempdir
from slave import update_scripts

# Logging instance.
LOGGER = logging.getLogger('annotated_run')

# /b/build/slave/<slavename>/build/
BUILD_DIR = os.getcwd()
# /b/build/slave/<slavename>/
BUILDER_DIR = os.path.dirname(BUILD_DIR)

# ENGINE_FLAGS is a mapping of master name to a engine flags. This can be used
# to test new recipe engine flags on a select few masters.
_ENGINE_FLAGS = {
  None: {},
}

def _build_dir():
  return BUILD_DIR

def _builder_dir():
  return BUILDER_DIR

def _ensure_directory(*path):
  path = os.path.join(*path)
  if not os.path.isdir(path):
    os.makedirs(path)
  return path


def _run_command(cmd, **kwargs):
  if kwargs.pop('dry_run', False):
    LOGGER.info('(Dry Run) Would have executed command: %s', cmd)
    return 0, ''

  LOGGER.debug('Executing command: %s', cmd)
  kwargs.setdefault('stderr', subprocess.STDOUT)
  proc = subprocess.Popen(cmd, **kwargs)
  stdout, _ = proc.communicate()

  LOGGER.debug('Process [%s] returned [%d] with output:\n%s',
               cmd, proc.returncode, stdout)
  return proc.returncode, stdout


def _check_command(cmd, **kwargs):
  rv, stdout = _run_command(cmd, **kwargs)
  if rv != 0:
    raise subprocess.CalledProcessError(rv, cmd, output=stdout)
  return stdout


def get_recipe_properties(stream, workdir, build_properties,
                          use_factory_properties_from_disk):
  """Constructs the recipe's properties from buildbot's properties.

  This retrieves the current factory properties from the master_config
  in the slave's checkout (no factory properties are handed to us from the
  master), and merges in the build properties.

  Using the values from the checkout allows us to do things like change
  the recipe and other factory properties for a builder without needing
  a master restart.

  As the build properties doesn't include the factory properties, we would:
  1. Load factory properties from checkout on the slave.
  2. Override the factory properties with the build properties.
  3. Set the factory-only properties as build properties using annotation so
     that they will show up on the build page.
  """
  if not use_factory_properties_from_disk:
    return build_properties

  with stream.step('setup_properties') as s:
    factory_properties = {}

    mastername = build_properties.get('mastername')
    buildername = build_properties.get('buildername')
    if mastername and buildername:
      # Load factory properties from tip-of-tree checkout on the slave builder.
      factory_properties = get_factory_properties_from_disk(
          workdir, mastername, buildername)

    # Check conflicts between factory properties and build properties.
    conflicting_properties = {}
    for name, value in factory_properties.items():
      if not build_properties.has_key(name) or build_properties[name] == value:
        continue
      conflicting_properties[name] = (value, build_properties[name])

    if conflicting_properties:
      s.step_text(
          '<br/>detected %d conflict[s] between factory and build properties'
          % len(conflicting_properties))

      conflicts = ['  "%s": factory: "%s", build: "%s"' % (
            name,
            '<unset>' if (fv is None) else fv,
            '<unset>' if (bv is None) else bv)
          for name, (fv, bv) in conflicting_properties.items()]
      LOGGER.warning('Conflicting factory and build properties:\n%s',
                     '\n'.join(conflicts))
      LOGGER.warning("Will use the values from build properties.")

    # Figure out the factory-only properties and set them as build properties so
    # that they will show up on the build page.
    for name, value in factory_properties.items():
      if not build_properties.has_key(name):
        s.set_build_property(name, json.dumps(value))

    # Build properties override factory properties.
    properties = factory_properties.copy()
    properties.update(build_properties)

    # Unhack buildbot-hacked blamelist (iannucci).
    if ('blamelist_real' in properties and 'blamelist' in properties):
      properties['blamelist'] = properties['blamelist_real']
      del properties['blamelist_real']

    return properties


def get_factory_properties_from_disk(workdir, mastername, buildername):
  master_list = master_cfg_utils.GetMasters()
  master_path = None
  for name, path in master_list:
    if name == mastername:
      master_path = path

  if not master_path:
    raise LookupError('master "%s" not found.' % mastername)

  script_path = os.path.join(env.Build, 'scripts', 'tools',
                             'dump_master_cfg.py')

  master_json = os.path.join(workdir, 'dump_master_cfg.json')
  dump_cmd = [sys.executable,
              script_path,
              master_path, master_json]
  proc = subprocess.Popen(dump_cmd, cwd=env.Build,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out, err = proc.communicate()
  if proc.returncode:
    raise LookupError('Failed to get the master config; running %r in %r '
                      'returned exit code %d\nstdout: %s\nstderr: %s'% (
                      dump_cmd, env.Build, proc.returncode, out, err))

  with open(master_json, 'rU') as f:
    config = json.load(f)

  # Now extract just the factory properties for the requested builder
  # from the master config.
  props = {}
  found = False
  for builder_dict in config['builders']:
    if builder_dict['name'] == buildername:
      found = True
      factory_properties = builder_dict['factory']['properties']
      for name, (value, _) in factory_properties.items():
        props[name] = value

  if not found:
    raise LookupError('builder "%s" not found on in master "%s"' %
                      (buildername, mastername))

  if 'recipe' not in props:
    raise LookupError('Cannot find recipe for %s on %s' %
                      (buildername, mastername))

  return props


def get_args(argv):
  """Process command-line arguments."""
  parser = argparse.ArgumentParser(
      description='Entry point for annotated builds.')
  parser.add_argument('-v', '--verbose',
      action='count', default=0,
      help='Increase verbosity. This can be specified multiple times.')
  parser.add_argument('-d', '--dry-run', action='store_true',
      help='Perform the setup, but refrain from executing the recipe.')
  parser.add_argument('-l', '--leak', action='store_true',
      help="Refrain from cleaning up generated artifacts.")
  parser.add_argument('--build-properties',
      type=json.loads, default={},
      help='build properties in JSON format')
  parser.add_argument('--factory-properties',
      type=json.loads, default={},
      help='factory properties in JSON format')
  parser.add_argument('--build-properties-gz', dest='build_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='build properties in b64 gz JSON format')
  parser.add_argument('--factory-properties-gz', dest='factory_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='factory properties in b64 gz JSON format')
  parser.add_argument('--keep-stdin', action='store_true', default=False,
      help='don\'t close stdin when running recipe steps')
  parser.add_argument('--master-overrides-slave', action='store_true',
      help='use the property values given on the command line from the master, '
           'not the ones looked up on the slave')
  parser.add_argument('--use-factory-properties-from-disk',
      action='store_true', default=False,
      help='use factory properties loaded from disk on the slave')

  group = parser.add_argument_group('LogDog Bootstrap')
  logdog_bootstrap.add_arguments(group)

  return parser.parse_args(argv)


def clean_old_recipe_engine():
  """Clean stale pycs from the old location of recipe_engine.

  This function should only be needed for a little while after the recipe
  packages rollout (2015-09-16).
  """
  for (dirpath, _, filenames) in os.walk(
      os.path.join(env.Build, 'third_party', 'recipe_engine')):
    for filename in filenames:
      if filename.endswith('.pyc'):
        os.remove(os.path.join(dirpath, filename))


def _exec_recipe(rt, opts, stream, basedir, tdir, properties):
  # Find out if the recipe we intend to run is in build_internal's recipes. If
  # so, use recipes.py from there, otherwise use the one from build.
  recipe_file = properties['recipe'].replace('/', os.path.sep) + '.py'

  # Use the standard recipe runner unless the recipes are explicitly in the
  # "build_limited" repository.
  recipe_runner = os.path.join(env.Build,
                               'scripts', 'slave', 'recipes.py')
  if env.BuildInternal:
    build_limited = os.path.join(env.BuildInternal, 'scripts', 'slave')
    if os.path.exists(os.path.join(build_limited, 'recipes', recipe_file)):
      recipe_runner = os.path.join(build_limited, 'recipes.py')

  # Dump properties to JSON and build recipe command.
  props_file = os.path.join(tdir, 'recipe_properties.json')
  with open(props_file, 'w') as fh:
    json.dump(properties, fh)

  mastername = properties.get('mastername')
  engine_flags = {}
  if mastername:
    engine_flags = _ENGINE_FLAGS.get(mastername)
  if not engine_flags:
    engine_flags = _ENGINE_FLAGS[None]

  recipe_result_path = os.path.join(tdir, 'recipe_result.json')

  engine_args = []
  if engine_flags:
    engine_flags_path = os.path.join(tdir, 'op_args.json')
    with open(engine_flags_path, 'w') as f:
      json.dump(engine_flags, f)
    engine_args = ['--operational-args-path', engine_flags_path]

  recipe_cmd = [
      sys.executable, '-u', recipe_runner,] + engine_args + [
      '--verbose',
      'run',
      '--workdir=%s' % _build_dir(),
      '--properties-file=%s' % props_file,
      '--output-result-json',
      recipe_result_path,
      properties['recipe'],
  ]

  recipe_return_code = None
  try:
    bs = logdog_bootstrap.bootstrap(rt, opts, basedir, tdir, properties,
                                    recipe_cmd)

    LOGGER.info('Bootstrapping through LogDog: %s', bs.cmd)
    bs.annotate(stream)
    _, _ = _run_command(bs.cmd, dry_run=opts.dry_run)
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
      recipe_return_code, _ = _run_command(recipe_cmd, dry_run=opts.dry_run)

    if engine_flags.get('use_result_proto'):
      with open(recipe_result_path, 'r') as f:
        return_value = json.load(f)

      if return_value.get('failure'):
        f = return_value['failure']

        # If we aren't a step failure, we assume it was an exception.
        if not f.get('step_failure'):
          # The recipe engine used to return -1, which got interpreted as 255
          # by os.exit in python, since process exit codes are a single byte.
          recipe_return_code = 255
        else:
          # return code != 0 is for the benefit of buildbot, which uses return
          # code to decide if a step failed or not.
          recipe_return_code = 1


  return recipe_return_code


def main(argv):
  opts = get_args(argv)

  if opts.verbose == 0:
    level = logging.INFO
  else:
    level = logging.DEBUG
  logging.getLogger().setLevel(level)

  clean_old_recipe_engine()

  # Enter our runtime environment.
  basedir = _builder_dir()
  with robust_tempdir.RobustTempdir(
      prefix='.recipe_runtime', leak=opts.leak) as rt:
    tdir = rt.tempdir(base=basedir)
    LOGGER.debug('Using temporary directory: [%s].', tdir)

    # Load factory properties and configuration.
    # TODO(crbug.com/551165): remove flag "factory_properties".
    use_factory_properties_from_disk = (opts.use_factory_properties_from_disk or
                                        bool(opts.factory_properties))

    stream = annotator.StructuredAnnotationStream()
    properties = get_recipe_properties(
        stream, tdir, opts.build_properties, use_factory_properties_from_disk)
    LOGGER.debug('Loaded properties: %s', properties)

    # Setup monitoring directory and send a monitoring event.
    build_data_dir = _ensure_directory(tdir, 'build_data')
    properties['build_data_dir'] = build_data_dir

    # path_config property defines what paths a build uses for checkout, git
    # cache, goma cache, etc.
    # Unless it is explicitly specified by a builder, use paths for buildbot
    # environment.
    properties['path_config'] = properties.get('path_config', 'buildbot')

    # Write our annotated_run.py monitoring event.
    monitoring_utils.write_build_monitoring_event(build_data_dir, properties)

    # Execute our recipe.
    return _exec_recipe(rt, opts, stream, basedir, tdir, properties)


def shell_main(argv):
  if update_scripts.update_scripts():
    # Re-execute with the updated annotated_run.py.
    rv, _ = _run_command([sys.executable] + argv)
    return rv
  else:
    return main(argv[1:])


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  sys.exit(shell_main(sys.argv))
