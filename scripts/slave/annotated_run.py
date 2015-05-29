#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import optparse
import os
import subprocess
import sys

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.append(os.path.join(BUILD_ROOT, 'scripts'))
sys.path.append(os.path.join(BUILD_ROOT, 'third_party'))

from common import annotator
from common import chromium_utils
from slave import recipe_universe

from recipe_engine import main as recipe_main


def get_recipe_properties(factory_properties, build_properties):
  """Constructs the recipe's properties from buildbot's properties.

  This merges factory_properties and build_properties.  Furthermore, it
  tries to reconstruct the 'recipe' property from builders.pyl if it isn't
  already there, and in that case merges in properties form builders.pyl.
  """
  properties = factory_properties.copy()
  properties.update(build_properties)

  # Try to reconstruct the recipe from builders.pyl if not given.
  if 'recipe' not in properties:
    mastername = properties['mastername']
    buildername = properties['buildername']

    master_path = chromium_utils.MasterPath(mastername)
    builders_file = os.path.join(master_path, 'builders.pyl')
    if os.path.isfile(builders_file):
      builders = chromium_utils.ReadBuildersFile(builders_file)
      assert buildername in builders['builders'], (
        'buildername %s is not listed in %s' % (buildername, builders_file))
      builder = builders['builders'][buildername]

      # Update properties with builders.pyl data.
      properties['recipe'] = builder['recipe']
      properties.update(builder.get('properties', {}))
    else:
      raise LookupError('Cannot find recipe for %s on %s' %
                        (build_properties['buildername'],
                        build_properties['mastername']))
  return properties


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
    cmd_dict = {
        'name': 'update_scripts',
        'cmd': gclient_cmd,
        'cwd': BUILD_ROOT,
    }
    annotator.print_step(cmd_dict, os.environ, stream)
    if subprocess.call(gclient_cmd, cwd=BUILD_ROOT) != 0:
      s.step_text('gclient sync failed!')
      s.step_warnings()
    os.environ['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'

    # After running update scripts, set PYTHONIOENCODING=UTF-8 for the real
    # annotated_run.
    os.environ['PYTHONIOENCODING'] = 'UTF-8'

    return True


def main(argv):
  opts, _ = get_args(argv)
  properties = get_recipe_properties(
      opts.factory_properties, opts.build_properties)
  stream = annotator.StructuredAnnotationStream()
  ret = recipe_main.run_steps(properties, stream,
                              universe=recipe_universe.get_universe())
  return ret.status_code


def shell_main(argv):
  if update_scripts():
    return subprocess.call([sys.executable] + argv)
  else:
    return main(argv)

if __name__ == '__main__':
  sys.exit(shell_main(sys.argv))
