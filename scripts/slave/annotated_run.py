#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import json
import optparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.append(os.path.join(BUILD_ROOT, 'scripts'))
sys.path.append(os.path.join(BUILD_ROOT, 'third_party'))

from common import annotator
from common import chromium_utils
from common import master_cfg_utils

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
BUILD_LIMITED_ROOT = os.path.join(
    os.path.dirname(BUILD_ROOT), 'build_internal', 'scripts', 'slave')

PACKAGE_CFG = os.path.join(
    os.path.dirname(os.path.dirname(SCRIPT_PATH)),
    'infra', 'config', 'recipes.cfg')

if sys.platform.startswith('win'):
  # TODO(pgervais): add windows support
  # QQ: Where is infra/run.py on windows machines?
  RUN_CMD = None
else:
  RUN_CMD = os.path.join('/', 'opt', 'infra-python', 'run.py')

@contextlib.contextmanager
def namedTempFile():
  fd, name = tempfile.mkstemp()
  os.close(fd)  # let the exceptions fly
  try:
    yield name
  finally:
    try:
      os.remove(name)
    except OSError as e:
      print >> sys.stderr, "LEAK: %s: %s" % (name, e)


def get_recipe_properties(build_properties, use_factory_properties_from_disk):
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

  stream = annotator.StructuredAnnotationStream()
  with stream.step('setup_properties') as s:
    factory_properties = {}

    mastername = build_properties.get('mastername')
    buildername = build_properties.get('buildername')
    if mastername and buildername:
      # Load factory properties from tip-of-tree checkout on the slave builder.
      factory_properties = get_factory_properties_from_disk(
          mastername, buildername)

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
      print 'Conflicting factory and build properties:'
      for name, (factory_value, build_value) in conflicting_properties.items():
        print ('  "%s": factory: "%s", build: "%s"' % (
            name,
            '<unset>' if (factory_value is None) else factory_value,
            '<unset>' if (build_value is None) else build_value))
      print "Will use the values from build properties."

    # Figure out the factory-only properties and set them as build properties so
    # that they will show up on the build page.
    for name, value in factory_properties.items():
      if not build_properties.has_key(name):
        s.set_build_property(name, json.dumps(value))

    # Build properties override factory properties.
    properties = factory_properties.copy()
    properties.update(build_properties)
    return properties


def get_factory_properties_from_disk(mastername, buildername):
  master_list = master_cfg_utils.GetMasters()
  master_path = None
  for name, path in master_list:
    if name == mastername:
      master_path = path

  if not master_path:
    raise LookupError('master "%s" not found.' % mastername)

  script_path = os.path.join(BUILD_ROOT, 'scripts', 'tools',
                             'dump_master_cfg.py')

  with namedTempFile() as fname:
    dump_cmd = [sys.executable,
                script_path,
                master_path, fname]
    proc = subprocess.Popen(dump_cmd, cwd=BUILD_ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    exit_code = proc.returncode

    if exit_code:
      raise LookupError('Failed to get the master config; dump_master_cfg %s'
                        'returned %d):\n%s\n%s\n'% (
                        mastername, exit_code, out, err))

    with open(fname, 'rU') as f:
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

  parser = optparse.OptionParser(
      description='Entry point for annotated builds.')
  parser.add_option('--build-properties',
                    action='callback', callback=chromium_utils.convert_json,
                    type='string', default={},
                    help='build properties in JSON format')
  parser.add_option('--factory-properties',
                    action='callback', callback=chromium_utils.convert_json,
                    type='string', default={},
                    help='factory properties in JSON format')
  parser.add_option('--build-properties-gz',
                    action='callback', callback=chromium_utils.convert_gz_json,
                    type='string', default={}, dest='build_properties',
                    help='build properties in b64 gz JSON format')
  parser.add_option('--factory-properties-gz',
                    action='callback', callback=chromium_utils.convert_gz_json,
                    type='string', default={}, dest='factory_properties',
                    help='factory properties in b64 gz JSON format')
  parser.add_option('--keep-stdin', action='store_true', default=False,
                    help='don\'t close stdin when running recipe steps')
  parser.add_option('--master-overrides-slave', action='store_true',
                    help='use the property values given on the command line '
                         'from the master, not the ones looked up on the slave')
  parser.add_option('--use-factory-properties-from-disk',
                    action='store_true', default=False,
                    help='use factory properties loaded from disk on the slave')
  return parser.parse_args(argv)


def update_scripts():
  if os.environ.get('RUN_SLAVE_UPDATED_SCRIPTS'):
    os.environ.pop('RUN_SLAVE_UPDATED_SCRIPTS')
    return False

  stream = annotator.StructuredAnnotationStream()

  with stream.step('update_scripts') as s:
    gclient_name = 'gclient'
    if sys.platform.startswith('win'):
      gclient_name += '.bat'
    gclient_path = os.path.join(BUILD_ROOT, '..', 'depot_tools', gclient_name)
    gclient_cmd = [gclient_path, 'sync', '--force', '--verbose']
    try:
      fd, output_json = tempfile.mkstemp()
      os.close(fd)
      gclient_cmd += ['--output-json', output_json]
    except Exception:
      # Super paranoia try block.
      output_json = None
    cmd_dict = {
        'name': 'update_scripts',
        'cmd': gclient_cmd,
        'cwd': BUILD_ROOT,
    }
    annotator.print_step(cmd_dict, os.environ, stream)
    if subprocess.call(gclient_cmd, cwd=BUILD_ROOT) != 0:
      s.step_text('gclient sync failed!')
      s.step_warnings()
    elif output_json:
      try:
        with open(output_json, 'r') as f:
          gclient_json = json.load(f)
        for line in json.dumps(
            gclient_json, sort_keys=True,
            indent=4, separators=(',', ': ')).splitlines():
          s.step_log_line('gclient_json', line)
        s.step_log_end('gclient_json')
        revision = gclient_json['solutions']['build/']['revision']
        scm = gclient_json['solutions']['build/']['scm']
        s.step_text('%s - %s' % (scm, revision))
        s.set_build_property('build_scm', json.dumps(scm))
        s.set_build_property('build_revision', json.dumps(revision))
      except Exception as e:
        s.step_text('Unable to process gclient JSON %s' % repr(e))
        s.step_warnings()
      finally:
        try:
          os.remove(output_json)
        except Exception as e:
          print >> sys.stderr, "LEAKED:", output_json, e
    else:
      s.step_text('Unable to get SCM data')
      s.step_warnings()

    os.environ['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'

    # After running update scripts, set PYTHONIOENCODING=UTF-8 for the real
    # annotated_run.
    os.environ['PYTHONIOENCODING'] = 'UTF-8'

    return True


def clean_old_recipe_engine():
  """Clean stale pycs from the old location of recipe_engine.

  This function should only be needed for a little while after the recipe
  packages rollout (2015-09-16).
  """
  for (dirpath, _, filenames) in os.walk(
      os.path.join(BUILD_ROOT, 'third_party', 'recipe_engine')):
    for filename in filenames:
      if filename.endswith('.pyc'):
        path = os.path.join(dirpath, filename)
        os.remove(path)


@contextlib.contextmanager
def build_data_directory():
  """Context manager that creates a build-specific directory.

  The directory is wiped when exiting.

  Yields:
    build_data (str or None): full path to a writeable directory. Return None if
        no directory can be found or if it's not writeable.
  """
  prefix = 'build_data'

  # TODO(pgervais): import that from infra_libs.logs instead
  if sys.platform.startswith('win'):  # pragma: no cover
    DEFAULT_LOG_DIRECTORIES = [
      'E:\\chrome-infra-logs',
      'C:\\chrome-infra-logs',
    ]
  else:
    DEFAULT_LOG_DIRECTORIES = ['/var/log/chrome-infra']

  build_data_dir = None
  for candidate in DEFAULT_LOG_DIRECTORIES:
    if os.path.isdir(candidate):
      build_data_dir = os.path.join(candidate, prefix)
      break

  # Remove any leftovers and recreate the dir.
  if build_data_dir:
    print >> sys.stderr, "Creating directory"
    # TODO(pgervais): use infra_libs.rmtree instead.
    if os.path.exists(build_data_dir):
      try:
        shutil.rmtree(build_data_dir)
      except Exception as exc:
        # Catching everything: we don't want to break any builds for that reason
        print >> sys.stderr, (
          "FAILURE: path can't be deleted: %s.\n%s" % (build_data_dir, str(exc))
        )
    print >> sys.stderr, "Creating directory"

    if not os.path.exists(build_data_dir):
      try:
        os.mkdir(build_data_dir)
      except Exception as exc:
        print >> sys.stderr, (
          "FAILURE: directory can't be created: %s.\n%s" %
          (build_data_dir, str(exc))
        )
        build_data_dir = None

  # Under this line build_data_dir should point to an existing empty dir
  # or be None.
  yield build_data_dir

  # Clean up after ourselves
  if build_data_dir:
    # TODO(pgervais): use infra_libs.rmtree instead.
    try:
      shutil.rmtree(build_data_dir)
    except Exception as exc:
      # Catching everything: we don't want to break any builds for that reason.
      print >> sys.stderr, (
        "FAILURE: path can't be deleted: %s.\n%s" % (build_data_dir, str(exc))
      )


def main(argv):
  opts, _ = get_args(argv)
  # TODO(crbug.com/551165): remove flag "factory_properties".
  use_factory_properties_from_disk = (opts.use_factory_properties_from_disk or
                                      bool(opts.factory_properties))
  properties = get_recipe_properties(
      opts.build_properties, use_factory_properties_from_disk)

  clean_old_recipe_engine()

  # Find out if the recipe we intend to run is in build_internal's recipes. If
  # so, use recipes.py from there, otherwise use the one from build.
  recipe_file = properties['recipe'].replace('/', os.path.sep) + '.py'
  if os.path.exists(os.path.join(BUILD_LIMITED_ROOT, 'recipes', recipe_file)):
    recipe_runner = os.path.join(BUILD_LIMITED_ROOT, 'recipes.py')
  else:
    recipe_runner = os.path.join(SCRIPT_PATH, 'recipes.py')

  with build_data_directory() as build_data_dir:
    # Create a LogRequestLite proto containing this build's information.
    if build_data_dir:
      properties['build_data_dir'] = build_data_dir

      hostname = socket.getfqdn()
      if hostname:  # just in case getfqdn() returns None.
        hostname = hostname.split('.')[0]
      else:
        hostname = None

      if RUN_CMD and os.path.exists(RUN_CMD):
        try:
          cmd = [RUN_CMD, 'infra.tools.send_monitoring_event',
             '--event-mon-output-file',
                 os.path.join(build_data_dir, 'log_request_proto'),
             '--event-mon-run-type', 'file',
             '--event-mon-service-name',
                 'buildbot/master/master.%s'
                 % properties.get('mastername', 'UNKNOWN'),
             '--build-event-build-name',
                 properties.get('buildername', 'UNKNOWN'),
             '--build-event-build-number',
                 str(properties.get('buildnumber', 0)),
             '--build-event-build-scheduling-time',
                 str(1000*int(properties.get('requestedAt', 0))),
             '--build-event-type', 'BUILD',
             '--event-mon-timestamp-kind', 'POINT',
             # And use only defaults for credentials.
           ]
          # Add this conditionally so that we get an error in
          # send_monitoring_event log files in case it isn't present.
          if hostname:
            cmd += ['--build-event-hostname', hostname]
          subprocess.call(cmd)
        except Exception:
          print >> sys.stderr, traceback.format_exc()

      else:
        print >> sys.stderr, (
          'WARNING: Unable to find run.py at %r, no events will be sent.'
          % str(RUN_CMD)
        )

    with namedTempFile() as props_file:
      with open(props_file, 'w') as fh:
        fh.write(json.dumps(properties))
      cmd = [
          sys.executable, '-u', recipe_runner,
          'run',
          '--workdir=%s' % os.getcwd(),
          '--properties-file=%s' % props_file,
          properties['recipe'] ]
      status = subprocess.call(cmd)

    # TODO(pgervais): Send events from build_data_dir to the endpoint.
  return status

def shell_main(argv):
  if update_scripts():
    return subprocess.call([sys.executable] + argv)
  else:
    return main(argv)


if __name__ == '__main__':
  sys.exit(shell_main(sys.argv))
