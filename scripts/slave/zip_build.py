#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
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

import chromium_utils
import slave_utils

class StagingError(Exception): pass


def archive(options, args):
  # Create some variables
  src_dir = os.path.abspath(options.src_dir)

  # TODO: need to get the build *output* directory passed in instead so Linux
  # and Mac don't have to walk up a directory to get to the right directory.
  if chromium_utils.IsWindows():
    build_dir = os.path.join(options.build_dir, options.target)
  elif chromium_utils.IsLinux():
    build_dir = os.path.join(os.path.dirname(options.build_dir), 'out',
                             options.target)
  elif chromium_utils.IsMac():
    build_dir = os.path.join(os.path.dirname(options.build_dir), 'xcodebuild',
                             options.target)
  else:
    raise NotImplementedError('%s is not supported.' % sys.platform)

  staging_dir = slave_utils.GetStagingDir(src_dir)
  build_revision = slave_utils.SubversionRevision(src_dir)

  if chromium_utils.IsMac() or chromium_utils.IsLinux():
    # Files are created umask 077 by default, we need to make sure the staging
    # dir can be fetch from, do this by recursively chmoding back up to the root
    # before pushing to web server.
    a_path = staging_dir
    while a_path != '/':
      current_permissions = os.stat(a_path)[0]
      if current_permissions & 0555 == 0555:
        break
      print 'Fixing permissions (%o) for \'%s\'' % (current_permissions, a_path)
      os.chmod(a_path, current_permissions | 0555)
      a_path = os.path.dirname(a_path)

  print 'Full Staging in %s' % build_dir

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

  # Build the list of files to archive
  zip_file_list = [file for file in os.listdir(build_dir)
                   if not re.match(file_filter, file)]

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
  # Depending on what the build target was, the unwanted files may or may not be
  # in the output dir, so we have to test before removing them.
  for x in things_to_skip:
    if x in zip_file_list:
      zip_file_list.remove(x)

  if chromium_utils.IsWindows():
    # Special case for chrome. Add back all the chrome*.pdb files to the list.
    # Also add browser_test*.pdb, ui_tests.pdb and ui_tests.pdb.
    # TODO(nsylvain): This should really be defined somewhere else.
    expression = (r"^(chrome_dll|chrome_exe|browser_test.+|unit_tests|"
                  r"chrome_frame_.*tests)"
                  r"\.pdb$")
    zip_file_list.extend([file for file in os.listdir(build_dir)
                          if re.match(expression, file)])

  if options.include_files is not None:
    zip_file_list.extend([file for file in os.listdir(build_dir)
                          if file in options.include_files])

  # Write out the revision number so we can figure it out in extract_build.py.
  build_revision_file_name = 'FULL_BUILD_REVISION'
  build_revision_path = os.path.join(build_dir, build_revision_file_name)
  try:
    build_revision_file = open(build_revision_path, 'w')
    build_revision_file.write('%d' % build_revision)
    build_revision_file.close()
    if chromium_utils.IsMac() or chromium_utils.IsLinux():
      os.chmod(build_revision_path, 0644)
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
  if chromium_utils.IsMac() or chromium_utils.IsLinux():
    os.chmod(zip_file, 0644)

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
  if chromium_utils.IsMac() or chromium_utils.IsLinux():
    os.chmod(versioned_file, 0644)

  # Now before we finish, trim out old builds to make sure we don't
  # fill the disk completely.

  stage_dir = os.path.dirname(zip_file)
  regexp = re.compile(zip_base + '_([0-9]+)(_old)?' + zip_ext)
  zip_list = glob.glob(os.path.join(stage_dir, zip_base + '_*' + zip_ext))
  # Build an ordered list of build numbers we have zip files for.
  build_list = []
  for x in zip_list:
    regexp_match = regexp.match(os.path.basename(x))
    if regexp_match:
      build_list.append(int(regexp_match.group(1)))
  # Since we match both ###.zip and ###_old.zip, bounce through a set and back
  # to a list to get an order list of build numbers.
  build_list = list(set(build_list))
  build_list.sort()
  # Only keep the last 15 number (that means we could have 30 due to _old files
  # if someone forced a respin of every single one)
  trim_build_list = build_list[:-15]
  for x in trim_build_list:
    prune_name = zip_base + ('_%d' % x) + zip_ext
    print 'Pruning build %d' % x
    chromium_utils.RemoveFile(stage_dir, prune_name)
    chromium_utils.RemoveFile(stage_dir,
                              prune_name.replace(zip_ext, '_old' + zip_ext))

  # Make sure there is enough disk space left for the next run (a rough estimate
  # is that 5X the last zip file size is enough to hold the next staging_dir and
  # zip_file). If disk space is running low, trim more old builds.
  # TODO(mmoss): Does this work on other platforms? I'm mainly worried about
  # Chromium Linux Builder (dbg), since that's always low on space, but there's
  # no reason this shouldn't run everywhere if it can.
  if chromium_utils.IsLinux():
    # Keep at least three old builds for lagging testers. If disk space gets too
    # low even to allow that, then it's time to resize the bots.
    min_space = zip_size * 5
    bonus_build_list = build_list[-15:-3]
    disk_stat = os.statvfs(zip_file)
    disk_space = disk_stat.f_bsize * disk_stat.f_bavail
    while (disk_space < min_space) and bonus_build_list:
      x = bonus_build_list.pop(0)
      prune_name = zip_base + ('_%d' % x) + zip_ext
      print 'Low disk space: Pruning build %d' % x
      chromium_utils.RemoveFile(stage_dir, prune_name)
      chromium_utils.RemoveFile(stage_dir,
                                prune_name.replace(zip_ext, '_old' + zip_ext))
      disk_stat = os.statvfs(zip_file)
      disk_space = disk_stat.f_bsize * disk_stat.f_bavail
    if (disk_space < min_space) and not bonus_build_list:
      print ('Disk space is very low (%.1fGB) with no builds to prune.' %
             (disk_space / float(1000000000)))
      return WARNING_EXIT_CODE
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
