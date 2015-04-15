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

from infra.libs.infra_types import freeze

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# List of files that are known to be non deterministic. This is a "temporary"
# workaround to find regression on the deterministic builders.
#
# PNaCl general bug: http://crbug.com/429358
#
# TODO(sebmarchand): Remove this once all the files are deterministic.
WHITELIST = freeze({
  # http://crbug.com/383340
  'android': {
    # Completed.
  },

  # http://crbug.com/330263
  'linux': {
    'browser_tests.isolated',
    'irt_exception_test_pnacl_newlib_x64.nexe',
    'irt_manifest_file_pnacl_newlib_x64.nexe',
    'ppapi_tests_extensions_packaged_app_pnacl_newlib_x64.nexe',
  },

  # http://crbug.com/330262
  'mac': {
    'base_unittests',
    'base_unittests.isolated',
    'browser_tests',
    'browser_tests.isolated',
    'content_browsertests',
    'content_browsertests.isolated',
    'content_unittests',
    'content_unittests.isolated',
    'crash_inspector',
    'crashpad_handler',
    'd8',
    'exif.so',
    'ffmpegsumo.so',
    'genmacro',
    'genmodule',
    'genperf',
    'genstring',
    'genversion',
    'image_diff',
    'infoplist_strings_tool',
    'interactive_ui_tests',
    'interactive_ui_tests.isolated',
    'ipc_mojo_perftests',
    'ipc_mojo_unittests',
    'libclearkeycdm.dylib',
    'mksnapshot',
    'net_unittests',
    'net_unittests.isolated',
    'osmesa.so',
    'pdfsqueeze',
    'peerconnection_server',
    'protoc',
    're2c',
    'sync_integration_tests',
    'sync_integration_tests.isolated',
    'tls_edit',
    'unit_tests',
    'unit_tests.isolated',
    'yasm',
  },

  # http://crbug.com/330260
  'win': {
    'base_unittests.exe',
    'base_unittests.isolated',
    'browser_tests.exe',
    'browser_tests.isolated',
    'chrome.dll',
    'chrome.exe',
    'chrome_child.dll',
    'chrome_watcher.dll',
    'clearkeycdm.dll',
    'content_browsertests.exe',
    'content_browsertests.isolated',
    'content_unittests.exe',
    'content_unittests.isolated',
    'd8.exe',
    'delegate_execute.exe',
    'delegate_execute_unittests.exe',
    'ipc_mojo_perftests.exe',
    'ipc_mojo_unittests.exe',
    'interactive_ui_tests.exe',
    'interactive_ui_tests.isolated',
    'metro_driver.dll',
    'mksnapshot.exe',
    'mock_nacl_gdb.exe',
    'net_unittests.exe',
    'net_unittests.isolated',
    'np_test_netscape_plugin.dll',
    'npapi_test_plugin.dll',
    'peerconnection_server.exe',
    'sync_integration_tests.exe',
    'sync_integration_tests.isolated',
    'test_registrar.exe',
    'unit_tests.exe',
    'unit_tests.isolated',
  },
})

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


def compare_build_artifacts(first_dir, second_dir, target_platform,
                            recursive=False):
  """Compares the artifacts from two distinct builds."""
  if not os.path.isdir(first_dir):
    print >> sys.stderr, '%s isn\'t a valid directory.' % first_dir
    return 1
  if not os.path.isdir(second_dir):
    print >> sys.stderr, '%s isn\'t a valid directory.' % second_dir
    return 1

  epoch_hex = struct.pack('<I', int(time.time())).encode('hex')
  print('Epoch: %s' %
      ' '.join(epoch_hex[i:i+2] for i in xrange(0, len(epoch_hex), 2)))

  with open(os.path.join(BASE_DIR, 'deterministic_build_blacklist.json')) as f:
    blacklist = frozenset(json.load(f))
  whitelist = WHITELIST[target_platform]

  # The two directories.
  first_list = get_files_to_compare(first_dir, recursive) - blacklist
  second_list = get_files_to_compare(second_dir, recursive) - blacklist

  equals = []
  expected_diffs = []
  unexpected_diffs = []
  unexpected_equals = []
  all_files = sorted(first_list & second_list)
  missing_files = sorted(first_list.symmetric_difference(second_list))
  if missing_files:
    print >> sys.stderr, 'Different list of files in both directories:'
    print >> sys.stderr, '\n'.join('  ' + i for i in missing_files)
    unexpected_diffs.extend(missing_files)

  max_filepath_len = max(len(n) for n in all_files)
  for f in all_files:
    first_file = os.path.join(first_dir, f)
    second_file = os.path.join(second_dir, f)
    result = compare_files(first_file, second_file)
    if not result:
      tag = 'equal'
      equals.append(f)
      if f in whitelist:
        unexpected_equals.append(f)
    else:
      if f in whitelist:
        expected_diffs.append(f)
        tag = 'expected'
      else:
        unexpected_diffs.append(f)
        tag = 'unexpected'
      result = 'DIFFERENT (%s): %s' % (tag, result)
    print('%-*s: %s' % (max_filepath_len, f, result))
  unexpected_diffs.sort()

  print('Equals:           %d' % len(equals))
  print('Expected diffs:   %d' % len(expected_diffs))
  print('Unexpected diffs: %d' % len(unexpected_diffs))
  if unexpected_diffs:
    print('Unexpected files with diffs:\n')
    for u in unexpected_diffs:
      print('  %s\n' % u)
  if unexpected_equals:
    print('Unexpected files with no diffs:\n')
    for u in unexpected_equals:
      print('  %s\n' % u)

  return int(bool(unexpected_diffs))


def main():
  parser = optparse.OptionParser(usage='%prog [options]')
  parser.add_option(
      '-f', '--first-build-dir', help='The first build directory.')
  parser.add_option(
      '-s', '--second-build-dir', help='The second build directory.')
  parser.add_option('-r', '--recursive', action='store_true', default=False,
                    help='Indicates if the comparison should be recursive.')
  parser.add_option('-t', '--target-platform', help='The target platform.')
  options, _ = parser.parse_args()

  if not options.first_build_dir:
    parser.error('--first-build-dir is required')
  if not options.second_build_dir:
    parser.error('--second-build-dir is required')
  if not options.target_platform:
    parser.error('--target-platform is required')

  return compare_build_artifacts(os.path.abspath(options.first_build_dir),
                                 os.path.abspath(options.second_build_dir),
                                 options.target_platform,
                                 options.recursive)


if __name__ == '__main__':
  sys.exit(main())
