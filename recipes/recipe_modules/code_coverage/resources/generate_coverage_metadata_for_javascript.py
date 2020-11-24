# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to generate JavaScript coverage metadata file.

The code coverage data format is defined at:
https://chromium.googlesource.com/infra/infra/+/refs/heads/master/appengine/findit/model/proto/code_coverage.proto
"""

import argparse
import fnmatch
import logging
import os
import sys


def get_json_coverage_files(json_dir):
  """Gets all JSON coverage files from directory.

  Args:
    dir: Directory in which to search for JSON files.

  Returns:
    A list of absolute paths to the JSON files that match.
  """
  files = []
  for filename in os.listdir(json_dir):
    if fnmatch.fnmatch(filename, '*.json'):
      files.append(os.path.join(json_dir, filename))

  return files


def _parse_args(args):
  """Parses the arguments.

  Args:
    args: The passed arguments.

  Returns:
    The parsed arguments as parameters.
  """
  parser = argparse.ArgumentParser(
      description='Generate the JavaScript coverage metadata')
  parser.add_argument(
      '--src-path',
      required=True,
      type=str,
      help='absolute path to the code checkout')
  parser.add_argument(
      '--output-dir',
      required=True,
      type=str,
      help='absolute path to the directory to write the metadata, must exist')
  parser.add_argument(
      '--coverage-dir',
      required=True,
      type=str,
      help='absolute path to the directory that contains merged JavaScript '
      'coverage data')
  params = parser.parse_args(args=args)

  return params


def main():
  params = _parse_args(sys.argv[1:])

  # TODO(benreich): Add monorail component mapping

  coverage_files = get_json_coverage_files(params.coverage_dir)
  if not coverage_files:
    raise Exception('No coverage file found under %s' % params.coverage_dir)
  logging.info('Found coverage files: %s', str(coverage_files))

  # TODO(benreich): Process the merged coverage files.


if __name__ == '__main__':
  logging.basicConfig(
      format='[%(asctime)s %(levelname)s] %(message)s', level=logging.INFO)
  sys.exit(main())
