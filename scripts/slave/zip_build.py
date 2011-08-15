#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Creates a zip file in the staging dir with the result of a compile.
    It can be sent to other machines for testing.
"""

import glob
import optparse
import os
import re
import shutil
import stat
import sys

from common import chromium_utils
from slave import slave_utils

class StagingError(Exception): pass

WARNING_EXIT_CODE = 88


def GetRecentBuildsByBuildNumber(zip_list, zip_base, zip_ext):
  # Build an ordered list of build numbers we have zip files for.
  regexp = re.compile(zip_base + '_([0-9]+)(_old)?' + zip_ext)
  build_list = []
  for x in zip_list:
    regexp_match = regexp.match(os.path.basename(x))
    if regexp_match:
      build_list.append(int(regexp_match.group(1)))
  # Since we match both ###.zip and ###_old.zip, bounce through a set and back
  # to a list to get an order list of build numbers.
  build_list = list(set(build_list))
  build_list.sort()
  # Only keep the last 10 number (that means we could have 20 due to _old files
  # if someone forced a respin of every single one)
  saved_build_list = build_list[-10:]
  ordered_asc_by_build_number_list = []
  for saved_build in saved_build_list:
    recent_name = zip_base + ('_%d' % saved_build) + zip_ext
    ordered_asc_by_build_number_list.append(recent_name)
    ordered_asc_by_build_number_list.append(
        recent_name.replace(zip_ext, '_old' + zip_ext))
  return ordered_asc_by_build_number_list


def GetRecentBuildsByModificationTime(zip_list):
  """Return the 10 most recent builds by modification time."""
  # Get the modification times for all of the entries in zip_list.
  mtimes_to_files = {}
  for zip_file in zip_list:
    mtime = int(os.stat(zip_file).st_mtime)
    mtimes_to_files.setdefault(mtime, [])
    mtimes_to_files[mtime].append(zip_file)
  # Order all files in our list by modification time.
  mtimes_to_files_keys = mtimes_to_files.keys()
  mtimes_to_files_keys.sort()
  ordered_asc_by_mtime_list = []
  for key in mtimes_to_files_keys:
    ordered_asc_by_mtime_list.extend(mtimes_to_files[key])
  # Return the most recent 10 builds.
  return ordered_asc_by_mtime_list[-10:]


def GetRealBuildDirectory(build_dir, target):
  """Return the build directory."""
  if chromium_utils.IsWindows():
    return os.path.join(build_dir, target)

  if chromium_utils.IsLinux():
    return os.path.join(os.path.dirname(build_dir), 'out', target)

  if chromium_utils.IsMac():
    return os.path.join(os.path.dirname(build_dir), 'xcodebuild', target)

  raise NotImplementedError('%s is not supported.' % sys.platform)


def ShouldPackageFile(filename, target):
  """Returns true if the file should be a part of the resulting archive."""
  if chromium_utils.IsWindows() and target is 'Release':
    # Special case for chrome. Add back all the chrome*.pdb files to the list.
    # Also add browser_test*.pdb, ui_tests.pdb and ui_tests.pdb.
    # TODO(nsylvain): This should really be defined somewhere else.
    expression = (r"^(chrome_dll|chrome_exe"
    #             r"|browser_test.+|unit_tests"
    #             r"|chrome_frame_.*tests"
                  r")\.pdb$")
    if re.match(expression, filename):
      return True

  file_filter = '$NO_FILTER^'
  if chromium_utils.IsWindows():
    # Remove all .ilk/.pdb files
    file_filter = '^.+\.(ilk|pdb|7z)$'
  elif chromium_utils.IsMac():
    # The static libs are just built as intermediate targets, and we don't
    # need to pull the dSYMs over to the testers.
    file_filter = '^.+\.(a|dSYM)$'
  elif chromium_utils.IsLinux():
    # object files, archives, and gcc (make build) dependency info.
    file_filter = '^.+\.(o|a|d)$'

  if re.match(file_filter, filename):
    return False

  # Skip files that the testers don't care about. Mostly directories.
  things_to_skip = []
  if chromium_utils.IsWindows():
    # Remove obj or lib dir entries
    things_to_skip = [ 'obj', 'lib', 'cfinstaller_archive', 'installer_archive']
  elif chromium_utils.IsMac():
    things_to_skip = [
      # We don't need the arm bits v8 builds.
      'd8_arm', 'v8_shell_arm',
      # pdfsqueeze is a build helper, no need to copy it to testers.
      'pdfsqueeze',
      # The inspector copies its resources into a resources folder in the build
      # output, but we only need the copy that ends up within the Chrome bundle.
      'resources',
      # We copy the framework into the app bundle, we don't need the second
      # copy outside the app.
      # TODO(mark): Since r28431, the copy in the build directory is actually
      # used by tests.  Putting two copies in the .zip isn't great, so maybe
      # we can find another workaround.
      # 'Chromium Framework.framework',
      # 'Google Chrome Framework.framework',
      # We copy the Helper into the app bundle, we don't need the second
      # copy outside the app.
      'Chromium Helper.app',
      'Google Chrome Helper.app',
    ]
  elif chromium_utils.IsLinux():
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
  src_dir = os.path.abspath(options.src_dir)
  build_dir = GetRealBuildDirectory(options.build_dir, options.target)

  staging_dir = slave_utils.GetStagingDir(src_dir)
  build_revision = slave_utils.SubversionRevision(src_dir)
  chromium_utils.MakeParentDirectoriesWorldReadable(staging_dir)

  print 'Full Staging in %s' % build_dir

  # Build the list of files to archive.
  zip_file_list = [f for f in os.listdir(build_dir)
                   if ShouldPackageFile(f, options.target)]
  if options.include_files is not None:
    zip_file_list.extend([f for f in os.listdir(build_dir)
                          if f in options.include_files])

  # Write out the revision number so we can figure it out in extract_build.py.
  build_revision_file_name = 'FULL_BUILD_REVISION'
  build_revision_path = os.path.join(build_dir, build_revision_file_name)
  try:
    build_revision_file = open(build_revision_path, 'w')
    build_revision_file.write('%d' % build_revision)
    build_revision_file.close()
    chromium_utils.MakeWorldReadable(build_revision_path)
    zip_file_list.append(build_revision_file_name)
  except IOError:
    print 'Writing to revision file %s failed ' % build_revision_path

  zip_file_name = 'full-build-%s' % chromium_utils.PlatformName()
  (zip_dir, zip_file) = chromium_utils.MakeZip(staging_dir,
                                               zip_file_name,
                                               zip_file_list,
                                               build_dir,
                                               raise_error=True)
  chromium_utils.RemoveDirectory(zip_dir)
  if not os.path.exists(zip_file):
    raise StagingError('Failed to make zip package %s' % zip_file)
  chromium_utils.MakeWorldReadable(zip_file)

  # Report the size of the zip file to help catch when it gets too big and
  # can cause bot failures from timeouts during downloads to testers.
  zip_size = os.stat(zip_file)[stat.ST_SIZE]
  print 'Zip file is %ld bytes' % zip_size

  zip_template = os.path.basename(zip_file)
  zip_base, zip_ext = os.path.splitext(zip_template)
  # Create a versioned copy of the file.
  versioned_file = zip_file.replace(zip_ext, '_%d%s' % (build_revision,
                                                        zip_ext))
  if os.path.exists(versioned_file):
    # This file already exists. Maybe we are doing a clobber build at the same
    # revision. We can move this file away.
    old_file = versioned_file.replace(zip_ext, '_old' + zip_ext)
    chromium_utils.MoveFile(versioned_file, old_file)
  shutil.copyfile(zip_file, versioned_file)
  chromium_utils.MakeWorldReadable(versioned_file)

  # Now before we finish, trim out old builds to make sure we don't
  # fill the disk completely.
  stage_dir = os.path.dirname(zip_file)
  zip_list = glob.glob(os.path.join(stage_dir, zip_base + '_*' + zip_ext))
  saved_zip_list = GetRecentBuildsByBuildNumber(zip_list, zip_base, zip_ext)
  saved_mtime_list = GetRecentBuildsByModificationTime(zip_list)

  # Trim old builds.
  trim_zip_list = []
  for zip_file in zip_list:
    if zip_file not in saved_zip_list and zip_file not in saved_mtime_list:
      trim_zip_list.append(zip_file)
  for trim_zip in trim_zip_list:
    print 'Pruning zip %s.' % trim_zip
    chromium_utils.RemoveFile(stage_dir, trim_zip)
  return 0


def main(argv):
  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--target', default='Release',
      help='build target to archive (Debug or Release)')
  option_parser.add_option('', '--src-dir', default='src',
                           help='path to the top-level sources directory')
  option_parser.add_option('', '--build-dir', default='chrome',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('', '--include-files', default=None,
                           help='files that should be included in the'
                                'zip, regardless of any exclusion patterns')

  options, args = option_parser.parse_args(argv)
  return archive(options, args)

if '__main__' == __name__:
  sys.exit(main(sys.argv))
