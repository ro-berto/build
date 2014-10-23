#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Compare the artifacts from two builds."""

import filecmp
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
    res = 1

  for f in first_list & second_list:
    first_file = os.path.join(first_dir, f)
    second_file = os.path.join(second_dir, f)
    if filecmp.cmp(first_file, second_file, shallow=False):
      print('%s: equal' % f)
    else:
      print('%s: DIFFERENT' % f)
      res = 1

  return res


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
