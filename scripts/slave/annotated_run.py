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
from slave import remote_run
from slave import robust_tempdir
from slave import update_scripts

# Logging instance.
LOGGER = logging.getLogger('annotated_run')

# /b/build/slave/<slavename>/build/
BUILD_DIR = os.getcwd()
# /b/build/slave/<slavename>/
BUILDER_DIR = os.path.dirname(BUILD_DIR)
# /b
B_DIR = os.path.dirname(os.path.dirname(os.path.dirname(BUILDER_DIR)))


# List of bots that automatically get run through "remote_run".
_REMOTE_RUN_PASSTHROUGH_ALL = '*'
_REMOTE_RUN_PASSTHROUGH = {
  'chromium.fyi': [
    'ios-simulator',
  ],

  'client.flutter': '*',
}


def _is_remote_run_passthrough(properties):
  builders = _REMOTE_RUN_PASSTHROUGH.get(properties.get('mastername'))
  return (builders is _REMOTE_RUN_PASSTHROUGH_ALL or
          builders and properties.get('buildername') in builders)


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
  parser.add_argument('--remote-run-passthrough', action='store_true',
      help='pass through and use remote_run')

  group = parser.add_argument_group('LogDog Bootstrap')
  logdog_bootstrap.add_arguments(group)

  return parser.parse_args(argv)


def _locate_recipe(recipe):
  # Find out if the recipe we intend to run is in build_internal's recipes. If
  # so, use recipes.py from there, otherwise use the one from build.
  recipe_file = recipe.replace('/', os.path.sep) + '.py'

  # Use the standard recipe runner unless the recipes are explicitly in the
  # "build_limited" repository.
  if env.BuildInternal:
    build_limited = os.path.join(env.BuildInternal, 'scripts', 'slave')
    if os.path.exists(os.path.join(build_limited, 'recipes', recipe_file)):
      return (
          os.path.join(build_limited, 'recipes.py'),
          ('https://chrome-internal.googlesource.com/chrome/tools/'
           'build_limited/scripts/slave.git'))

  # Public recipe (this repository).
  return (
      os.path.join(env.Build, 'scripts', 'slave', 'recipes.py'),
      'https://chromium.googlesource.com/chromium/tools/build.git')


def _remote_run_passthrough(opts, properties, stream):
  recipe = properties.pop('recipe')
  _, recipe_repository = _locate_recipe(recipe)

  with stream.step('remote_run passthrough') as s:
    s.step_text('<br>'.join([
      'recipe: %s' % (recipe,),
      'recipe_repository: %s' % (recipe_repository,),
    ]))

  cmd = [
    'annotated_run', # argv[0]
    '--repository', recipe_repository,
    '--recipe', recipe,
    '--build-properties-gz', chromium_utils.b64_gz_json_encode(properties),
    '--canary',
  ]
  if opts.verbose > 0:
    cmd += ['--verbose']
  if opts.leak:
    cmd += ['--leak']

  LOGGER.info('Configured for "remote_run" passthrough w/ translated argv: %s',
              cmd)
  return remote_run.main(cmd, stream, passthrough=True)


def _exec_recipe(rt, opts, stream, basedir, tdir, properties):
  recipe_runner, _ = _locate_recipe(properties['recipe'])

  # Dump properties to JSON and build recipe command.
  props_file = os.path.join(tdir, 'recipe_properties.json')
  with open(props_file, 'w') as fh:
    json.dump(properties, fh)

  recipe_result_path = os.path.join(tdir, 'recipe_result.json')

  engine_args = []

  recipe_cmd = [
      remote_run.find_python(), '-u', recipe_runner,
  ] + engine_args + [
      '--verbose',
      'run',
      '--workdir=%s' % _build_dir(),
      '--properties-file=%s' % props_file,
      '--output-result-json',
      recipe_result_path,
      properties['recipe'],
  ]

  environ = os.environ.copy()
  environ['VPYTHON_CLEAR_PYTHONPATH'] = '1'

  # Default to return code != 0 is for the benefit of buildbot, which uses
  # return code to decide if a step failed or not.
  recipe_return_code = 1
  try:
    bs = logdog_bootstrap.bootstrap(rt, opts, basedir, tdir, properties,
                                    recipe_cmd)

    LOGGER.info('Bootstrapping through LogDog: %s', bs.cmd)
    bs.annotate(stream)
    _, _ = _run_command(bs.cmd, dry_run=opts.dry_run, env=environ)
    recipe_return_code = bs.get_result()
  except logdog_bootstrap.NotBootstrapped as e:
    LOGGER.info('Not using LogDog. Invoking `recipes.py` directly: %s', e)
    recipe_return_code, _ = _run_command(recipe_cmd, dry_run=opts.dry_run,
                                         env=environ)

  # Try to open recipe result JSON. Any failure will result in an exception
  # and an infra failure.
  with open(recipe_result_path, 'r') as f:
    return_value = json.load(f)

  # If we failed, but aren't a step failure, we assume it was an
  # exception.
  f = return_value.get('failure')
  if f is not None and not f.get('step_failure'):
    # The recipe engine used to return -1, which got interpreted as 255
    # by os.exit in python, since process exit codes are a single byte.
    recipe_return_code = 255
  return recipe_return_code


def main(argv):
  # We always want everything to be unbuffered so that we can see the logs on
  # buildbot/logdog as soon as they're available.
  os.environ['PYTHONUNBUFFERED'] = '1'

  opts = get_args(argv)

  if opts.verbose == 0:
    level = logging.INFO
  else:
    level = logging.DEBUG
  logging.getLogger().setLevel(level)

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

    # If this is an opt-in run, or if this builder is configured for
    # passthrough, use "remote_run"!
    if (_is_remote_run_passthrough(properties) or
        opts.remote_run_passthrough):
      return _remote_run_passthrough(opts, properties, stream)

    # Ensure that the CIPD client and base tooling is installed and available on
    # PATH.
    from slave import cipd_bootstrap_v2
    cipd_bootstrap_v2.high_level_ensure_cipd_client(
      B_DIR, properties.get('mastername'))

    # Setup monitoring directory and send a monitoring event.
    build_data_dir = _ensure_directory(tdir, 'build_data')
    properties['build_data_dir'] = build_data_dir

    # path_config property defines what paths a build uses for checkout, git
    # cache, goma cache, etc.
    # Unless it is explicitly specified by a builder, use paths for buildbot
    # environment.
    properties['path_config'] = properties.get('path_config', 'buildbot')

    properties['bot_id'] = properties['slavename']
    properties['builder_id'] = (
        'master.{mastername}:{buildername}'.format(**properties))
    properties['build_id'] = (
        'buildbot/{mastername}/{buildername}/{buildnumber}'.format(
            **properties))

    remote_run.set_recipe_runtime_properties(stream, opts, properties)
    LOGGER.info('Using properties: %r', properties)

    # Write our annotated_run.py monitoring event.
    monitoring_utils.write_build_monitoring_event(build_data_dir, properties)

    # Cleanup system and temporary directories.
    from slave import cleanup_temp
    cleanup_temp.Cleanup(B_DIR)

    # Create a cleanup directory so that the recipe engine can assume that it
    # exists.
    _ensure_directory(_builder_dir(), 'build.dead')

    # Execute our recipe.
    return _exec_recipe(rt, opts, stream, basedir, tdir, properties)


def shell_main(argv):
  if update_scripts.update_scripts():
    # Re-execute with the updated annotated_run.py.
    rv, _ = _run_command([sys.executable] + argv)
    return rv
  return main(argv[1:])


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  sys.exit(shell_main(sys.argv))
