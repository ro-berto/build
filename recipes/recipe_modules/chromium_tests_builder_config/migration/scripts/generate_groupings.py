#!/usr/bin/env python3
# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script for generating files for tracking builder config migration.

The script generates files containing the groupings of not-yet migrated
builders for a given project. The groupings are builders that are
related to each other via a triggering relationship or a mirroring
relationship. All such builders must be migrated to use src-side configs
together. These files are used by a presubmit script to prevent changes
that add new groupings of builders.

The files generated by the script are JSON files containing a javascript
object with a key for each unmigrated builder in the project. The
corresponding value is the list of builders that are grouped together by
triggering & mirroring relationships.

The builders that are included in the migration file for a project are
determined by the JSON files in the filters subdirectory that contain
the JSON equivalent of a list of BuilderGroupFilter messages from
builder_config_migration.proto.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

DEFAULT_GROUPINGS_DIR = os.path.normpath(f'{__file__}/../..')


def parse_args(args=None, *, parser_type=None):
  """Parse the command-line arguments.

  Args:
    args: (list[str]) Arguments to use instead of sys.argv. Used for
      unit testing.
    parser_type: (class) The type of the argument parser to use. Used
      for unit testing.

  Returns:
    An argparse.Namespace object with the following attributes:
      * func: (func(args) -> None) The function to call to perform the
        generation/validation operation.
      * groupings_dir: (str) The directory where the groupings are
        located.
      * projects: (list[str]) The LUCI projects to generate groupings
        files for.
  """
  parser_type = parser_type or argparse.ArgumentParser
  parser = parser_type(description='Update the migration groupings files')

  parser.set_defaults(func=generate_groupings)
  parser.add_argument(
      '--validate',
      help='Validate that files are up-to-date instead of generating them',
      action='store_const',
      dest='func',
      const=validate_groupings)
  parser.add_argument(
      'projects', help='The projects to generate/validate', nargs='+')

  # Flags to facilitate testing
  parser.add_argument(
      '--groupings-dir',
      help=('The directory where the groupings files are located/generated to'
            ' (used for testing)'),
      default=DEFAULT_GROUPINGS_DIR)

  return parser.parse_args(args)


_RECIPES_PY = os.path.normpath(f'{__file__}/../../../../../recipes.py')


def _run_builder_config_migration_recipe(project, output_path):
  with open(os.path.normpath(f'{__file__}/../filters/{project}.json')) as f:
    filters = json.load(f)
  properties = {
      'groupings_operation': {
          'output_path': output_path,
          'builder_group_filters': filters,
      }
  }
  cmd = [
      sys.executable,
      _RECIPES_PY,
      'run',
      '--properties',
      json.dumps(properties),
      'chromium/builder_config_migration',
  ]

  env = os.environ.copy()
  env['RECIPES_USE_PY3'] = 'true'

  try:
    subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, env=env)
  except subprocess.CalledProcessError as e:
    sys.stderr.write(e.output)
    raise


def generate_groupings(
    args, *, groupings_generator=_run_builder_config_migration_recipe):
  """Generate the contents of the groupings files.

  Args:
    args: The parsed arguments returned from `parse_args`.
    groupings_generator: The generator to call to generate the file
      content. Used for unit testing only.
  """
  for p in args.projects:
    groupings_generator(p, f'{args.groupings_dir}/{p}.json')


class ValidationException(Exception):

  def __init__(self, projects):
    super().__init__(projects)
    self._projects = tuple(projects)

  @property
  def projects(self):
    return self._projects

  def __str__(self):
    project_str = ', '.join(sorted(self.projects))
    return (f'The following groupings files need regeneration: {project_str}\n'
            f"Please run {__file__} {' '.join(self.projects)}")


def validate_groupings(
    args, *, groupings_generator=_run_builder_config_migration_recipe):
  """Validate the contents of the groupings files.

  Args:
    args: The parsed arguments returned from `parse_args`.
    groupings_generator: The generator to call to generate the file
      content. Used for unit testing only.

  Raises:
    ValidationException if 1 or more projects need to be regenerated.
  """
  needs_regen = []
  with tempfile.TemporaryDirectory() as d:
    for p in args.projects:
      output_path = f'{d}/{p}.json'
      groupings_generator(p, output_path)
      with open(output_path) as f:
        contents = f.read()
      try:
        with open(f'{args.groupings_dir}/{p}.json') as f:
          old_contents = f.read()
      except FileNotFoundError:
        old_contents = None
      if old_contents != contents:
        needs_regen.append(p)
  if needs_regen:
    raise ValidationException(needs_regen)


def main():
  args = parse_args()
  try:
    args.func(args)
  except ValidationException as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
  main()
