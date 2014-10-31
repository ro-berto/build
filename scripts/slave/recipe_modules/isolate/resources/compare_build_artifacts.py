#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Compare the artifacts from two builds."""

import json
import optparse
import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_files_to_compare(build_dir):
  """Get the list of files to compare."""
  allowed = frozenset(
      ('', '.app', '.dll', '.dylib', '.exe', '.nexe', '.so'))

  def check(f):
    if not os.path.isfile(f):
      return False
    if os.path.basename(f).startswith('.'):
      return False
    ext = os.path.splitext(f)[1]
    if ext == '.isolated':
      return True
    return ext in allowed and os.access(f, os.X_OK)

  return set(f for f in os.listdir(build_dir) if
             check(os.path.join(build_dir, f)))


def compare_files(first_filepath, second_filepath):
  """Compare two binaries and return the number of differences between them.

  Returns -1 if the files have a different size.
  """
  if os.stat(first_filepath).st_size != os.stat(second_filepath).st_size:
    return -1

  # Read the files by chunks of 1MB.
  chunk_size = 1024 * 1024
  diffs = 0
  with open(first_filepath, 'rb') as lhs:
    with open(second_filepath, 'rb') as rhs:
      while True:
        lhs_data = lhs.read(chunk_size)
        rhs_data = rhs.read(chunk_size)
        if not lhs_data:
          break
        diffs += sum(l != r for l, r in zip(lhs_data, rhs_data))

  return diffs


def compare_build_artifacts(first_dir, second_dir):
  """Compare the artifacts from two distinct builds."""
  if not os.path.isdir(first_dir):
    print >> sys.stderr, '%s isn\'t a valid directory.' % first_dir
    return 1
  if not os.path.isdir(second_dir):
    print >> sys.stderr, '%s isn\'t a valid directory.' % second_dir
    return 1

  with open(os.path.join(BASE_DIR, 'deterministic_build_blacklist.json')) as f:
    blacklist = frozenset(json.load(f))

  res = 0
  first_list = get_files_to_compare(first_dir) - blacklist
  second_list = get_files_to_compare(second_dir) - blacklist

  diff = first_list.symmetric_difference(second_list)
  if diff:
    print >> sys.stderr, 'Different list of files in both directories'
    print >> sys.stderr, '\n'.join('  ' + i for i in sorted(diff))
    res += len(diff)

  max_filepath_len = max(len(n) for n in first_list & second_list)
  for f in sorted(first_list & second_list):
    first_file = os.path.join(first_dir, f)
    second_file = os.path.join(second_dir, f)
    files_diffs = compare_files(first_file, second_file)
    if not files_diffs:
      result = 'equal'
    else:
      result = 'DIFFERENT: %s' % ('different size' if result == -1 else
                                  '%d different bytes' % files_diffs)
      res += 1
    print('%-*s: %s' % (max_filepath_len, f, result))

  print '%d files are equal, %d are different.'  % (
      len(first_list & second_list) - res, res)

  return 0 if res == 0 else 1


def main():
  parser = optparse.OptionParser(usage='%prog [options]')
  parser.add_option('--first-build-dir', help='The first build directory.')
  parser.add_option('--second-build-dir', help='The second build directory.')
  options, _ = parser.parse_args()

  if not options.first_build_dir:
    parser.error('--first-build-dir is required')
  if not options.second_build_dir:
    parser.error('--second-build-dir is required')

  return compare_build_artifacts(options.first_build_dir,
                                 options.second_build_dir)


if __name__ == '__main__':
  sys.exit(main())
