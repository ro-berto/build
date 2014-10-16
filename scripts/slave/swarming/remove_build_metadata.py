#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Remove the build metadata embedded in the artifacts of a build."""

import optparse
import os
import subprocess
import sys


def RunZapTimestamp(src_dir, filename):
  syzygy_dir = os.path.join(
      src_dir, 'third_party', 'syzygy', 'binaries', 'exe')
  zap_timestamp_exe = os.path.join(syzygy_dir, 'zap_timestamp.exe')
  return subprocess.call([zap_timestamp_exe, filename])


def RemovePEMetadata(build_dir, src_dir):
  """Remove the build metadata from a PE file."""
  files = (i for i in os.listdir(build_dir) if i.endswith(('.dll', '.exe')))

  for filename in files:
    # Only run zap_timestamp on the PE files for which we have a PDB.
    if os.path.exists(os.path.join(build_dir, filename + '.pdb')):
      ret = RunZapTimestamp(src_dir, os.path.join(build_dir, filename))
      if ret != 0:
        print "zap_timestamp.exe failed for %s." % filename
        return ret


def main():
  parser = optparse.OptionParser(usage='%prog [options]')
  # TODO(sebmarchand): Add support for reading the list of artifact from a
  # .isolated file.
  parser.add_option('--build-dir', help='The build directory.')
  parser.add_option('--src-dir', help='The source directory.')
  options, _ = parser.parse_args()

  if not options.build_dir:
    parser.error('--build-dir is required')
  if not options.src_dir:
    parser.error('--src-dir is required')

  # There's nothing to do for the non-Windows platform yet.
  if sys.platform == 'win32':
    return RemovePEMetadata(options.build_dir, options.src_dir)


if __name__ == '__main__':
  sys.exit(main())
