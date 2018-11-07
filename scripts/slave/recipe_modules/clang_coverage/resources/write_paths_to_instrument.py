#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Writes an input file for the partial code coverage compile wrapper."""

import argparse
import os
import sys


def _make_argument_parser(*args, **kwargs):
  parser = argparse.ArgumentParser(*args, **kwargs)
  parser.add_argument(
      '--write-to', required=True, help='path to input file to be written')
  parser.add_argument(
      '--src-path', required=True, help='absolute path to checkout')
  parser.add_argument(
      '--build-path', required=True, help='absolute path to build directory')
  parser.add_argument(
      'sources',
      nargs='*',
      help='paths of source files to instrument relative to '
      '--src-path, with platform-specific path separator.')
  return parser


def main():
  desc = ('make the paths to the given source files relative to the build dir '
          'and write to a file')
  parser = _make_argument_parser(description=desc)
  params = parser.parse_args()

  with open(params.write_to, 'w') as out_file:
    # TODO(crbug.com/901597): Ensure that this path computation results in
    # relative paths using platform-appropriate separators.
    rebased_paths = [
        os.path.relpath(os.path.join(params.src_path, f), params.build_path) +
        '\n' for f in params.sources
    ]
    out_file.write(''.join(rebased_paths))


if __name__ == '__main__':
  sys.exit(main())
