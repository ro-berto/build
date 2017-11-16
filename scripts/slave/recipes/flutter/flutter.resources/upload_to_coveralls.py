#!/usr/bin/env python
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import os
import sys
import subprocess


def main():
  parser = argparse.ArgumentParser(
      description='Uploads coverage data to Coveralls')
  parser.add_argument(
      '--token-file',
      metavar='FILENAME',
      help='Filename of a file containing the repo token for Coveralls.')
  parser.add_argument(
      '--coverage-path',
      metavar='FILENAME',
      help='Path of a file containing the coverage data to upload.')

  args = parser.parse_args()

  if not args.token_file:
    sys.stderr.write('Must supply token file with --token-file\n')
    return -1

  if not args.coverage_path:
    sys.stderr.write('Must supply coverage path with --coverage-path\n')
    return -1

  repo_token = ''
  with open(args.token_file, 'r') as token_file:
    repo_token = token_file.read().strip()

  # The ruby gem 'coveralls-lcov' must be installed on the system.
  # Add to the nodes.yaml file as:
  # - nodes:
  #   # ...
  #   classes:
  #    chrome_infra::packages::gem:
  #      gems: [coveralls-lcov]
  return subprocess.call(
      ['coveralls-lcov',
       '--repo-token=%s' % repo_token, args.coverage_path])


if '__main__' == __name__:
  sys.exit(main())
