#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script that can be used to filter out files from a patch/diff.

Usage: pipe the patch contents to stdin and the filtered output will be written
to stdout.
The output will be compatible with the patch program, both for Subversion and
Git patches.
NOTICE: the script can only manage patches created by depot tools (i.e. it
is supposed to be used for tryjob generated patches. This is because it relies
no the Index: line being present, which is normally not the case for Git patches
(it is added by depot_tools/third_party/upload.py during the creation of the
try job).
"""

import optparse
import os
import re
import sys

from depot_tools import patch


_FILENAME_REGEX = re.compile(r'^.*: ([^\t]+).*\n$')


def parse_patch_set(patch_contents):
  patch_chunks = []
  current_chunk = []
  for line in patch_contents.splitlines(True):
    # See https://code.google.com/p/chromium/codesearch#
    #     chromium/tools/depot_tools/third_party/upload.py
    # for details on how patches uploaded with depot_tools will have each
    # file chunk start with either of these strings (for both Git and SVN).
    if line.startswith(('Index:', 'Property changes on:')) and current_chunk:
      patch_chunks.insert(0, current_chunk)
      current_chunk = []
    current_chunk.append(line)

  if current_chunk:
    patch_chunks.insert(0, current_chunk)

  # Parse filename for each patch chunk and create FilePatchDiff objects

  patches = []
  for chunk in patch_chunks:
    match = _FILENAME_REGEX.match(chunk[0])
    if not match:
      raise Exception('Did not find any filename in line "%s". Notice that '
                      'only patches uploaded using depot tools are supported '
                      'since normal Git patches don\'t include the "Index:" '
                      'line.' % chunk[0])
    filename = match.group(1).replace('\\', '/')
    patches.append(patch.FilePatchDiff(filename=filename, diff=''.join(chunk),
                                       svn_properties=[]))
  return patch.PatchSet(patches)


def convert_to_patch_compatible_diff(filename, patch_data):
  """Convert patch data to be compatible with the standard patch program.

  This will remove the "a/" and "b/" prefixes added by Git, so the patch becomes
  compatible with the standard patch program.
  """
  diff = ''
  for line in patch_data.splitlines(True):
    if line.startswith('---'):
      line = line.replace('a/' + filename, filename)
    elif line.startswith('+++'):
      line = line.replace('b/' + filename, filename)
    diff += line
  return diff


def main():
  usage = '%s -f <path-filter> [-r <root-dir>]' % os.path.basename(sys.argv[0])
  parser = optparse.OptionParser(usage=usage)
  parser.add_option('-f', '--path-filter',
                    help=('The path filter (UNIX paths) that all file paths '
                          'are required to have to pass this filter (no '
                          'regexp).'))
  parser.add_option('-r', '--root-dir',
                    help=('The patch root dir in which to apply the patch. If '
                          'specified, it will be prepended to the filename '
                          'for each patch entry before the filter is applied.'))

  options, args = parser.parse_args()
  if args:
    parser.error('Unused args: %s' % args)
  if not options.path_filter:
    parser.error('A path filter must be be specified.')

  patch_contents = sys.stdin.read()

  # Only print the patch entries that passes our path filter.
  for patch_entry in parse_patch_set(patch_contents):
    filename = patch_entry.filename
    if options.root_dir:
      filename = os.path.join(options.root_dir, filename)

    if filename.startswith(options.path_filter):
      print convert_to_patch_compatible_diff(patch_entry.filename,
                                             patch_entry.get(for_git=False)),

if __name__ == '__main__':
  sys.exit(main())
