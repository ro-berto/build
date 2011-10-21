#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Creates a zip file of a build and upload it to google storage.

    This will be used by the ASAN security tests.
"""

import optparse
import os
import re
import stat
import sys

from common import chromium_utils
from slave import slave_utils

class StagingError(Exception): pass


def ShouldPackageFile(filename, target):
  """Returns true if the file should be a part of the resulting archive."""
  file_filter = '^.+\.(o|a|d)$'

  if re.match(file_filter, filename):
    return False

  # Skip files that we don't care about. Mostly directories.
  things_to_skip = [
    # intermediate build directories (full of .o, .d, etc.).
    'appcache', 'glue', 'googleurl', 'lib', 'lib.host', 'obj', 'obj.host',
    'obj.target', 'src', '.deps',
    # scons build cruft
    '.sconsign.dblite',
    # build helper, not needed on testers
    'mksnapshot',
  ]

  if filename in things_to_skip:
    return False

  return True


def archive(options, args):
  src_dir = os.path.abspath(os.path.dirname(options.build_dir))
  build_dir = os.path.join(src_dir, 'out', options.target)
  staging_dir = slave_utils.GetStagingDir(src_dir)
  build_revision = slave_utils.SubversionRevision(src_dir)
  chromium_utils.MakeParentDirectoriesWorldReadable(staging_dir)

  print 'Staging in %s' % build_dir

  # Build the list of files to archive.
  zip_file_list = [f for f in os.listdir(build_dir)
                   if ShouldPackageFile(f, options.target)]

  zip_file_name = 'asan-%s-%s-%d' % (chromium_utils.PlatformName(),
                                     options.target.lower(),
                                     build_revision)

  (zip_dir, zip_file) = chromium_utils.MakeZip(staging_dir,
                                               zip_file_name,
                                               zip_file_list,
                                               build_dir,
                                               raise_error=True)
  chromium_utils.RemoveDirectory(zip_dir)
  if not os.path.exists(zip_file):
    raise StagingError('Failed to make zip package %s' % zip_file)
  chromium_utils.MakeWorldReadable(zip_file)

  # Report the size of the zip file to help catch when it gets too big.
  zip_size = os.stat(zip_file)[stat.ST_SIZE]
  print 'Zip file is %ld bytes' % zip_size

  gs_bucket = options.factory_properties.get('gs_bucket', None)
  status = slave_utils.GSUtilCopyFile(zip_file, gs_bucket)
  if status:
    raise StagingError('Failed to upload %s to %s. Error %d' % (zip_file,
                                                                gs_bucket,
                                                                status))
  return status


def main(argv):
  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--target', default='Release',
                           help='build target to archive (Debug or Release)')
  option_parser.add_option('', '--build-dir',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('--build-properties', action='callback',
                           callback=chromium_utils.convert_json, type='string',
                           nargs=1, default={},
                           help='build properties in JSON format')
  option_parser.add_option('--factory-properties', action='callback',
                           callback=chromium_utils.convert_json, type='string',
                           nargs=1, default={},
                           help='factory properties in JSON format')

  options, args = option_parser.parse_args(argv)
  return archive(options, args)

if '__main__' == __name__:
  sys.exit(main(sys.argv))
