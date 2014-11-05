#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Compare the artifacts from two builds."""

import difflib
import json
import optparse
import os
import struct
import sys
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_files_to_compare(build_dir, recursive=False):
  """Get the list of files to compare."""
  allowed = frozenset(
      ('', '.apk', '.app', '.dll', '.dylib', '.exe', '.nexe', '.so'))
  non_x_ok_exts = frozenset(('.apk', '.isolated'))
  def check(f):
    if not os.path.isfile(f):
      return False
    if os.path.basename(f).startswith('.'):
      return False
    ext = os.path.splitext(f)[1]
    if ext in non_x_ok_exts:
      return True
    return ext in allowed and os.access(f, os.X_OK)

  ret_files = set()
  for root, dirs, files in os.walk(build_dir):
    if not recursive:
      dirs[:] = [d for d in dirs if d.endswith('_apk')]
    for f in (f for f in files if check(os.path.join(root, f))):
      ret_files.add(os.path.relpath(os.path.join(root, f), build_dir))
  return ret_files


def diff_dict(a, b):
  """Returns a yaml-like textural diff of two dict.

  It is currently optimized for the .isolated format.
  """
  out = ''
  for key in set(a) | set(b):
    va = a.get(key)
    vb = b.get(key)
    if va.__class__ != vb.__class__:
      out += '- %s:  %r != %r\n' % (key, va, vb)
    elif isinstance(va, dict):
      c = diff_dict(va, vb)
      if c:
        out += '- %s:\n%s\n' % (
            key, '\n'.join('  ' + l for l in c.splitlines()))
    elif va != vb:
      out += '- %s:  %s != %s\n' % (key, va, vb)
  return out.rstrip()


def diff_binary(first_filepath, second_filepath, file_len):
  """Returns a compact binary diff if the diff is small enough."""
  CHUNK_SIZE = 32
  MAX_STREAMS = 10
  diffs = 0
  streams = []
  offset = 0
  with open(first_filepath, 'rb') as lhs:
    with open(second_filepath, 'rb') as rhs:
      while True:
        lhs_data = lhs.read(CHUNK_SIZE)
        rhs_data = rhs.read(CHUNK_SIZE)
        if not lhs_data:
          break
        if lhs_data != rhs_data:
          diffs += sum(l != r for l, r in zip(lhs_data, rhs_data))
          if streams is not None:
            if len(streams) < MAX_STREAMS:
              streams.append((offset, lhs_data, rhs_data))
            else:
              streams = None
        offset += len(lhs_data)
        del lhs_data
        del rhs_data
  if not diffs:
    return None
  result = '%d out of %d bytes are different (%.2f%%)' % (
        diffs, file_len, 100.0 * diffs / file_len)
  if streams:
    encode = lambda text: ''.join(i if 31 < ord(i) < 128 else '.' for i in text)
    for offset, lhs_data, rhs_data in streams:
      lhs_line = '%s \'%s\'' % (lhs_data.encode('hex'), encode(lhs_data))
      rhs_line = '%s \'%s\'' % (rhs_data.encode('hex'), encode(rhs_data))
      diff = list(difflib.Differ().compare([lhs_line], [rhs_line]))[-1][2:-1]
      result += '\n  0x%-8x: %s\n              %s\n              %s' % (
            offset, lhs_line, rhs_line, diff)
  return result


def compare_files(first_filepath, second_filepath):
  """Compares two binaries and return the number of differences between them.

  Returns None if the files are equal, a string otherwise.
  """
  if first_filepath.endswith('.isolated'):
    with open(first_filepath, 'rb') as f:
      lhs = json.load(f)
    with open(second_filepath, 'rb') as f:
      rhs = json.load(f)
    diff = diff_dict(lhs, rhs)
    if diff:
      return '\n' + '\n'.join('  ' + line for line in diff.splitlines())
    # else, falls through binary comparison, it must be binary equal too.

  file_len = os.stat(first_filepath).st_size
  if file_len != os.stat(second_filepath).st_size:
    return 'different size: %d != %d' % (
        file_len, os.stat(second_filepath).st_size)

  return diff_binary(first_filepath, second_filepath, file_len)


def compare_build_artifacts(first_dir, second_dir, recursive=False):
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
  first_list = get_files_to_compare(first_dir, recursive) - blacklist
  second_list = get_files_to_compare(second_dir, recursive) - blacklist

  diff = first_list.symmetric_difference(second_list)
  if diff:
    print >> sys.stderr, 'Different list of files in both directories'
    print >> sys.stderr, '\n'.join('  ' + i for i in sorted(diff))
    res += len(diff)

  epoch_hex = struct.pack('<I', int(time.time())).encode('hex')
  print('Epoch: %s' %
      ' '.join(epoch_hex[i:i+2] for i in xrange(0, len(epoch_hex), 2)))
  max_filepath_len = max(len(n) for n in first_list & second_list)
  for f in sorted(first_list & second_list):
    first_file = os.path.join(first_dir, f)
    second_file = os.path.join(second_dir, f)
    result = compare_files(first_file, second_file)
    if not result:
      result = 'equal'
    else:
      result = 'DIFFERENT: %s' % result
      res += 1
    print('%-*s: %s' % (max_filepath_len, f, result))

  print '%d files are equal, %d are different.'  % (
      len(first_list & second_list) - res, res)

  return 0 if res == 0 else 1


def main():
  parser = optparse.OptionParser(usage='%prog [options]')
  parser.add_option(
      '-f', '--first-build-dir', help='The first build directory.')
  parser.add_option(
      '-s', '--second-build-dir', help='The second build directory.')
  parser.add_option('-r', '--recursive', action='store_true', default=False,
                    help='Indicates if the comparison should be recursive.')
  options, _ = parser.parse_args()

  if not options.first_build_dir:
    parser.error('--first-build-dir is required')
  if not options.second_build_dir:
    parser.error('--second-build-dir is required')

  return compare_build_artifacts(os.path.abspath(options.first_build_dir),
                                 os.path.abspath(options.second_build_dir),
                                 options.recursive)


if __name__ == '__main__':
  sys.exit(main())
