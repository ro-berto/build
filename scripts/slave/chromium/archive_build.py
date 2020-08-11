#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to archive a build and its symbols, executed by a buildbot slave.

  This script is used for developer builds.

  To archive files on Google Storage, set the --gs-bucket flag to
  'gs://<bucket-name>'. To control access to archives, set the --gs-acl flag to
  the desired canned-acl (e.g. 'public-read', see
  https://developers.google.com/storage/docs/accesscontrol#extension for other
  supported canned-acl values). If the --gs-acl flag is not set, the bucket's
  default object ACL will be applied (see
  https://developers.google.com/storage/docs/accesscontrol#defaultobjects).

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import glob
import json
import optparse
import os
import sys

from common import archive_utils
from common.chromium_utils import GS_COMMIT_POSITION_NUMBER_KEY, \
                                  GS_COMMIT_POSITION_KEY, \
                                  GS_GIT_COMMIT_KEY
from common import chromium_utils
from slave import build_directory
from slave import slave_utils

# TODO(mmoss): tests should be added to FILES.cfg, then TESTS can go away.
# The names of the files containing the list of tests to be archived for the
# build. This file can be present in self._tool_dir as well as in the path
# specifed by --extra-archive-paths.
TEST_FILE_NAME = 'TESTS'


class GSUtilError(Exception):
  pass


def Write(file_path, data):
  f = open(file_path, 'w')
  try:
    f.write(data)
  finally:
    f.close()


class StagerBase(object):
  """Handles archiving a build. Call the public ArchiveBuild() method."""

  def __init__(self, options, build_revision):
    """Sets a number of file and directory paths for convenient use."""

    self.options = options
    self._src_dir = os.path.abspath(options.src_dir)
    self._chrome_dir = os.path.join(self._src_dir, 'chrome')

    build_dir = build_directory.GetBuildOutputDirectory(self._src_dir or None)
    self._build_dir = os.path.join(build_dir, options.target)
    if chromium_utils.IsWindows():
      self._tool_dir = os.path.join(self._chrome_dir, 'tools', 'build', 'win')
    elif chromium_utils.IsLinux():
      # On Linux, we might have built for chromeos.  Archive the same.
      if options.target_os == 'chromeos':
        self._tool_dir = os.path.join(
            self._chrome_dir, 'tools', 'build', 'chromeos'
        )
      # Or, we might have built for Android.
      elif options.target_os == 'android':
        self._tool_dir = os.path.join(
            self._chrome_dir, 'tools', 'build', 'android'
        )
      else:
        self._tool_dir = os.path.join(
            self._chrome_dir, 'tools', 'build', 'linux'
        )
    elif chromium_utils.IsMac():
      self._tool_dir = os.path.join(self._chrome_dir, 'tools', 'build', 'mac')
    else:
      raise NotImplementedError(
          'Platform "%s" is not currently supported.' % sys.platform
      )
    self._staging_dir = (
        options.staging_dir or slave_utils.GetStagingDir(self._src_dir)
    )
    if not os.path.exists(self._staging_dir):
      os.makedirs(self._staging_dir)

    self._symbol_dir_base = options.dirs['symbol_dir_base']
    self._www_dir_base = options.dirs['www_dir_base']

    if options.build_name:
      self._build_name = options.build_name
    else:
      self._build_name = slave_utils.SlaveBuildName(self._src_dir)

    self._symbol_dir_base = os.path.join(
        self._symbol_dir_base, self._build_name
    )
    self._www_dir_base = os.path.join(self._www_dir_base, self._build_name)

    self._version_file = os.path.join(self._chrome_dir, 'VERSION')

    self._chromium_revision = chromium_utils.GetBuildSortKey(options)[1]

    self._v8_revision = chromium_utils.GetBuildSortKey(options, project='v8')[1]
    self._v8_revision_git = chromium_utils.GetGitCommit(options, project='v8')

    self.last_change_file = os.path.join(self._staging_dir, 'LAST_CHANGE')
    # The REVISIONS file will record the revisions information of the main
    # components Chromium/WebKit/V8.
    self.revisions_path = os.path.join(self._staging_dir, 'REVISIONS')
    self._build_revision = build_revision
    self._build_path_component = str(self._build_revision)

    # Will be initialized in GetLastBuildRevision.
    self.last_chromium_revision = None
    self.last_v8_revision = None

    self._files_file = os.path.join(
        self._tool_dir, archive_utils.FILES_FILENAME
    )
    self._test_files = self.BuildOldFilesList(TEST_FILE_NAME)

    self._archive_files = None

  def CopyFileToGS(
      self, filename, gs_base, gs_subdir, mimetype=None, gs_acl=None
  ):
    # normalize the subdir to remove duplicated slashes. This break newer
    # versions of gsutil. Also remove leading and ending slashes for the subdir,
    # gsutil adds them back autimatically and this can cause a double slash to
    # be added.
    if gs_subdir:
      gs_subdir = gs_subdir.replace('//', '/')
      gs_subdir = gs_subdir.strip('/')

    # Construct metadata from our revision information, as available.
    gs_metadata = {
        GS_COMMIT_POSITION_NUMBER_KEY: self._chromium_revision,
    }

    # Add the commit position, if available
    try:
      gs_metadata[GS_COMMIT_POSITION_KEY] = chromium_utils.BuildCommitPosition(
          *chromium_utils.GetCommitPosition(self.options)
      )
    except chromium_utils.NoIdentifiedRevision:
      pass

    # Add the git commit hash, if available
    try:
      gs_metadata[GS_GIT_COMMIT_KEY] = chromium_utils.GetGitCommit(self.options)
    except chromium_utils.NoIdentifiedRevision:
      pass

    status = slave_utils.GSUtilCopyFile(
        filename, gs_base, gs_subdir, mimetype, gs_acl, metadata=gs_metadata
    )
    if status != 0:
      dest = gs_base + '/' + gs_subdir
      raise GSUtilError(
          'GSUtilCopyFile error %d. "%s" -> "%s"' % (status, filename, dest)
      )

  def TargetPlatformName(self):
    return self.options.target_os or chromium_utils.PlatformName()

  def BuildOldFilesList(self, source_file_name):
    """Build list of files from the old "file of paths" style input.

    Combine any source_file_name inputs found in the default tools dir and in
    any dirs given with --extra-archive-paths.
    """
    default_source = os.path.join(self._tool_dir, source_file_name)
    if os.path.exists(default_source):
      file_list = open(default_source).readlines()
    else:
      print 'WARNING: No default %s list found at %s' % (
          source_file_name, default_source
      )
      file_list = []
    file_list = [f.strip() for f in file_list]
    file_list.extend(
        self.GetExtraFiles(self.options.extra_archive_paths, source_file_name)
    )
    file_list = archive_utils.ExpandWildcards(self._build_dir, file_list)
    return file_list

  def MyCopyFileToDir(
      self,
      filename,
      destination,
      gs_base,
      gs_subdir='',
      mimetype=None,
      gs_acl=None
  ):
    if gs_base:
      self.CopyFileToGS(
          filename, gs_base, gs_subdir, mimetype=mimetype, gs_acl=gs_acl
      )

    if not gs_base:
      chromium_utils.CopyFileToDir(filename, destination)

  def MyMaybeMakeDirectory(self, destination, gs_base):
    if not gs_base:
      chromium_utils.MaybeMakeDirectory(destination)

  def MyMakeWorldReadable(self, destination, gs_base):
    if not gs_base:
      chromium_utils.MakeWorldReadable(destination)

  def MySshMakeDirectory(self, host, destination, gs_base):
    if not gs_base:
      chromium_utils.SshMakeDirectory(host, destination)

  def MySshCopyFiles(
      self,
      filename,
      host,
      destination,
      gs_base,
      gs_subdir='',
      mimetype=None,
      gs_acl=None
  ):
    if gs_base:
      self.CopyFileToGS(
          filename, gs_base, gs_subdir, mimetype=mimetype, gs_acl=gs_acl
      )

    if not gs_base:
      chromium_utils.SshCopyFiles(filename, host, destination)

  def GetExtraFiles(self, extra_archive_paths, source_file_name):
    """Returns a list of extra files to package in the build output directory.

    For each of the paths in the extra_file_paths list, this function
    checks to see if path/source_file_name exists. If so, it expects these
    files to contain a list of newline-separated filenames that it returns
    in a list. The paths in extra_archive_paths are relative to the
    directory specified by --src-dir.
    """
    extra_files_list = []
    extra_path_list = extra_archive_paths.split(',')
    for path in extra_path_list:
      path = path.strip()
      source_file = os.path.join(self._src_dir, path, source_file_name)
      if os.path.exists(source_file):
        new_files_list = open(source_file).readlines()
        extra_files_list.extend(new_files_list)

    extra_files_list = [e.strip() for e in extra_files_list]
    extra_files_list = archive_utils.ExpandWildcards(
        self._build_dir, extra_files_list
    )
    return extra_files_list

  def GenerateRevisionFile(self):
    """Save chromium/webkit/v8's revision in a specified file. we will write a
    human readable format to save the revision information. The contents will be
    {"chromium_revision":chromium_revision,
     "v8_revision":v8_revision}
    It is also in json format.
    """

    print 'Saving revision to %s' % self.revisions_path
    Write(
        self.revisions_path,
        json.dumps({
            'chromium_revision': self._chromium_revision,
            'v8_revision': self._v8_revision,
            'v8_revision_git': self._v8_revision_git,
        })
    )

  def GetLastBuildRevision(self):
    """Reads the last staged build revision from last_change_file.

    If the last_change_file does not exist, returns None.
    We also try to get the last Chromium/WebKit/V8 revision from the REVISIONS
    file generated by GenerateRevisionFile
    """
    last_build_revision = None
    if os.path.exists(self.last_change_file):
      last_build_revision = open(self.last_change_file).read()

    if os.path.exists(self.revisions_path):
      fp = open(self.revisions_path)
      try:
        line = fp.readline()

        # TODO(markhuang): remove this block after all builders are updated
        line = line.replace('\'', '"')

        revisions_dict = json.loads(line)
        if revisions_dict:
          self.last_chromium_revision = revisions_dict['chromium_revision']
          self.last_v8_revision = revisions_dict['v8_revision']
      except (IOError, KeyError, ValueError), e:
        self.last_chromium_revision = None
        self.last_v8_revision = None
        print e
      fp.close()
    return last_build_revision

  def SaveBuildRevisionToSpecifiedFile(self, file_path):
    """Save build revision in the specified file"""

    print 'Saving revision to %s' % file_path
    Write(file_path, '%s' % self._build_revision)

  def CreateArchiveFile(self, zip_name, zip_file_list):
    return archive_utils.CreateArchive(
        self._build_dir, self._staging_dir, zip_file_list, zip_name
    )

  # TODO(mmoss): This could be simplified a bit if revisions_path were added to
  # archive_files. The only difference in handling seems to be that Linux/Mac
  # unlink archives after upload, but don't unlink those two files. Any reason
  # why deleting them would be a problem? They don't appear to be used elsewhere
  # in this script.
  def _UploadBuild(
      self, www_dir, revisions_path, archive_files, gs_base, gs_acl
  ):
    if chromium_utils.IsWindows():
      print 'os.makedirs(%s)' % www_dir

      for archive in archive_files:
        print 'chromium_utils.CopyFileToDir(%s, %s)' % (archive, www_dir)
      print 'chromium_utils.CopyFileToDir(%s, %s)' % (revisions_path, www_dir)

      if not self.options.dry_run:
        self.MyMaybeMakeDirectory(www_dir, gs_base)
        for archive in archive_files:
          self.MyCopyFileToDir(archive, www_dir, gs_base, gs_acl=gs_acl)
        self.MyCopyFileToDir(revisions_path, www_dir, gs_base, gs_acl=gs_acl)
    elif chromium_utils.IsLinux() or chromium_utils.IsMac():
      for archive in archive_files:
        print 'SshCopyFiles(%s, %s, %s)' % (
            archive, self.options.archive_host, www_dir
        )
      print 'SshCopyFiles(%s, %s, %s)' % (
          revisions_path, self.options.archive_host, www_dir
      )
      if not self.options.dry_run:
        print 'SshMakeDirectory(%s, %s)' % (self.options.archive_host, www_dir)
        self.MySshMakeDirectory(self.options.archive_host, www_dir, gs_base)
        for archive in archive_files:
          self.MyMakeWorldReadable(archive, gs_base)
          self.MySshCopyFiles(
              archive,
              self.options.archive_host,
              www_dir,
              gs_base,
              gs_acl=gs_acl
          )
          os.unlink(archive)
        # Files are created umask 077 by default, so make it world-readable
        # before pushing to web server.
        self.MyMakeWorldReadable(revisions_path, gs_base)
        self.MySshCopyFiles(
            revisions_path,
            self.options.archive_host,
            www_dir,
            gs_base,
            gs_acl=gs_acl
        )
    else:
      raise NotImplementedError(
          'Platform "%s" is not currently supported.' % sys.platform
      )

  def UploadTests(self, www_dir, gs_base, gs_acl):
    test_file_list = self._test_files
    if not test_file_list:
      return

    # Make test_file_list contain absolute paths.
    test_file_list = [os.path.join(self._build_dir, f) for f in test_file_list]
    UPLOAD_DIR = 'chrome-%s.test' % self.TargetPlatformName()

    # Filter out those files that don't exist.
    base_src_dir = os.path.join(self._build_dir, '')

    for test_file in test_file_list[:]:
      if os.path.exists(test_file):
        relative_dir = os.path.dirname(test_file[len(base_src_dir):])
        test_dir = os.path.join(www_dir, UPLOAD_DIR, relative_dir)
        print 'chromium_utils.CopyFileToDir(%s, %s)' % (test_file, test_dir)
      else:
        print '%s does not exist and is skipped.' % test_file
        test_file_list.remove(test_file)

    # Extract the list of test paths that will be created. These paths need
    # to be relative to the archive dir. We have to rebuild the relative
    # list from the now-pruned absolute test_file_list.
    relative_file_list = [tf[len(base_src_dir):] for tf in test_file_list]
    test_dirs = archive_utils.ExtractDirsFromPaths(relative_file_list)
    test_dirs = [os.path.join(www_dir, UPLOAD_DIR, d) for d in test_dirs]

    root_test_dir = os.path.join(www_dir, UPLOAD_DIR)
    print 'chromium_utils.MaybeMakeDirectory(%s)' % root_test_dir
    for test_dir in test_dirs:
      print 'chromium_utils.MaybeMakeDirectory(%s)' % test_dir

    if not self.options.dry_run:
      if chromium_utils.IsWindows():
        # Use Samba on Windows.
        self.MyMaybeMakeDirectory(root_test_dir, gs_base)
        for test_dir in test_dirs:
          self.MyMaybeMakeDirectory(test_dir, gs_base)
        for test_file in test_file_list:
          # TODO(robertshield): binaries and symbols are stored in a zip file
          # via CreateArchiveFile. Tests should be too.
          relative_dir = os.path.dirname(test_file[len(base_src_dir):])
          test_dir = os.path.join(www_dir, UPLOAD_DIR, relative_dir)
          self.MyCopyFileToDir(
              test_file,
              test_dir,
              gs_base,
              gs_subdir='/'.join([UPLOAD_DIR, relative_dir]),
              gs_acl=gs_acl
          )
      else:
        # Otherwise use scp.
        self.MySshMakeDirectory(
            self.options.archive_host, root_test_dir, gs_base
        )
        for test_dir in test_dirs:
          self.MySshMakeDirectory(self.options.archive_host, test_dir, gs_base)
        for test_file in test_file_list:
          self.MyMakeWorldReadable(test_file, gs_base)
          # TODO(robertshield): binaries and symbols are stored in a zip file
          # via CreateArchiveFile. Tests should be too.
          relative_dir = os.path.dirname(test_file[len(base_src_dir):])
          test_dir = os.path.join(www_dir, UPLOAD_DIR, relative_dir)
          self.MySshCopyFiles(
              test_file,
              self.options.archive_host,
              test_dir,
              gs_base,
              gs_subdir='/'.join([UPLOAD_DIR, relative_dir]),
              gs_acl=gs_acl
          )

  def ArchiveBuild(self):
    """Zips build files and uploads them, their symbols, and a change log."""
    result = 0
    if self._build_revision is None:
      raise archive_utils.StagingError('No build revision was provided')
    print 'Staging in %s' % self._staging_dir

    fparser = archive_utils.FilesCfgParser(
        self._files_file, self.options.mode, self.options.arch
    )
    files_list = fparser.ParseLegacyList()
    self._archive_files = archive_utils.ExpandWildcards(
        self._build_dir, files_list
    )
    archives_list = fparser.ParseArchiveLists()
    archives_files_list = [
        item['filename']
        for sublist in archives_list.values()
        for item in sublist
    ]
    archives_files_list = archive_utils.ExpandWildcards(
        self._build_dir, archives_files_list
    )

    # Check that all the files for all the archives exist.
    all_files_list = self._archive_files + archives_files_list
    all_files_list.append(self._version_file)
    not_found = archive_utils.VerifyFiles(
        all_files_list, self._build_dir, self.options.ignore
    )
    not_found_optional = []
    for bad_fn in not_found[:]:
      if fparser.IsOptional(bad_fn):
        not_found_optional.append(bad_fn)
        not_found.remove(bad_fn)
        # Remove it from all file lists so we don't try to process it.
        if bad_fn in self._archive_files:
          self._archive_files.remove(bad_fn)
        for archive_list in archives_list.values():
          archive_list[:] = [x for x in archive_list if bad_fn != x['filename']]
    # TODO(mmoss): Now that we can declare files optional in FILES.cfg, should
    # we only allow not_found_optional, and fail on any leftover not_found
    # files?

    print 'last change: %s' % self._build_revision
    print 'build name: %s' % self._build_name

    archive_name = 'chrome-%s.zip' % self.TargetPlatformName()
    archive_file = self.CreateArchiveFile(archive_name, self._archive_files)[1]

    # Handle any custom archives.
    # TODO(mmoss): Largely copied from stage_build.py. Maybe refactor more of
    # this into archive_utils.py.
    archive_files = [archive_file]
    for archive_name in archives_list:
      # The list might be empty if it was all 'not_found' optional files.
      if not archives_list[archive_name]:
        continue
      if fparser.IsDirectArchive(archives_list[archive_name]):
        fileobj = archives_list[archive_name][0]
        # Copy the file to the path specified in archive_name, which might be
        # different than the dirname or basename in 'filename' (allowed by
        # 'direct_archive').
        stage_subdir = os.path.dirname(archive_name)
        stage_fn = os.path.basename(archive_name)
        chromium_utils.MaybeMakeDirectory(
            os.path.join(self._staging_dir, stage_subdir)
        )
        print 'chromium_utils.CopyFileToDir(%s, %s, dest_fn=%s)' % (
            os.path.join(self._build_dir, fileobj['filename']),
            os.path.join(self._staging_dir, stage_subdir), stage_fn
        )
        if not self.options.dry_run:
          chromium_utils.CopyFileToDir(
              os.path.join(self._build_dir, fileobj['filename']),
              os.path.join(self._staging_dir, stage_subdir),
              dest_fn=stage_fn
          )
        archive_files.append(os.path.join(self._staging_dir, archive_name))
      else:
        custom_archive = self.CreateArchiveFile(
            archive_name, [f['filename'] for f in archives_list[archive_name]]
        )[1]
        print 'Adding %s to be archived.' % (custom_archive)
        archive_files.append(custom_archive)

    # Generate a revisions file which contains the Chromium/WebKit/V8's
    # revision information.
    self.GenerateRevisionFile()

    www_dir = os.path.join(self._www_dir_base, self._build_path_component)
    gs_bucket = self.options.gs_bucket
    gs_acl = self.options.gs_acl
    gs_base = None
    if gs_bucket:
      gs_base = '/'.join([
          gs_bucket, self._build_name, self._build_path_component
      ])
    self._UploadBuild(
        www_dir, self.revisions_path, archive_files, gs_base, gs_acl
    )

    # Archive Linux packages (if any -- only created for Chrome builds).
    if chromium_utils.IsLinux():
      linux_packages = (
          glob.glob(
              os.path.join(
                  self._build_dir, '*-r%s_*.deb' % self._chromium_revision
              )
          )
      )
      linux_packages.extend(
          glob.glob(
              os.path.join(
                  self._build_dir, '*-%s.*.rpm' % self._chromium_revision
              )
          )
      )
      for package_file in linux_packages:
        print 'SshCopyFiles(%s, %s, %s)' % (
            package_file, self.options.archive_host, www_dir
        )
      if not self.options.dry_run:
        print 'SshMakeDirectory(%s, %s)' % (self.options.archive_host, www_dir)
        self.MySshMakeDirectory(self.options.archive_host, www_dir, gs_base)

        for package_file in linux_packages:
          self.MyMakeWorldReadable(package_file, gs_base)
          self.MySshCopyFiles(
              package_file,
              self.options.archive_host,
              www_dir,
              gs_base,
              gs_acl=gs_acl
          )
          # Cleanup archived packages, otherwise they keep accumlating since
          # they have different filenames with each build.
          os.unlink(package_file)

    self.UploadTests(www_dir, gs_base, gs_acl)

    if not self.options.dry_run:
      # Save the current build revision locally so we can compute a changelog
      # next time
      self.SaveBuildRevisionToSpecifiedFile(self.last_change_file)

      # Record the latest revision in the developer archive directory.
      latest_file_path = os.path.join(self._www_dir_base, 'LATEST')
      if chromium_utils.IsWindows():
        print 'Saving revision to %s' % latest_file_path
        if gs_base:
          self.CopyFileToGS(
              self.last_change_file,
              gs_base,
              '..',
              mimetype='text/plain',
              gs_acl=gs_acl
          )
        if not gs_base:
          self.SaveBuildRevisionToSpecifiedFile(latest_file_path)
      elif chromium_utils.IsLinux() or chromium_utils.IsMac():
        # Files are created umask 077 by default, so make it world-readable
        # before pushing to web server.
        self.MyMakeWorldReadable(self.last_change_file, gs_base)
        print 'Saving revision to %s:%s' % (
            self.options.archive_host, latest_file_path
        )
        self.MySshCopyFiles(
            self.last_change_file,
            self.options.archive_host,
            latest_file_path,
            gs_base,
            '..',
            mimetype='text/plain',
            gs_acl=gs_acl
        )
      else:
        raise NotImplementedError(
            'Platform "%s" is not currently supported.' % sys.platform
        )

    if len(not_found_optional):
      sys.stderr.write(
          '\n\nINFO: Optional File(s) not found: %s\n' %
          ', '.join(not_found_optional)
      )
    if len(not_found):
      sys.stderr.write(
          '\n\nWARNING: File(s) not found: %s\n' % ', '.join(not_found)
      )
    return result


class StagerByChromiumRevision(StagerBase):
  """Handles archiving a build. Call the public ArchiveBuild() method.
  Archive a build according to its chromium revision if it is because of
  the chromium change.
  """

  def __init__(self, options):
    """Overwrite _build_revision for archiving build by Chromium revision."""

    StagerBase.__init__(self, options, None)
    self._build_revision = self._chromium_revision
    self._build_path_component = chromium_utils.GetSortableUploadPathForSortKey(
        *chromium_utils.GetBuildSortKey(options)
    )


class StagerByBuildNumber(StagerBase):
  """Handles archiving a build. Call the public ArchiveBuild() method.
  Archive a build according to the build number if it is because of
  the changes happened on multiple components like chromium/webkit/v8.
  """

  def __init__(self, options):
    """Overwrite _build_revision for archiving build by build number."""

    StagerBase.__init__(self, options, options.build_number)


def main():
  option_parser = optparse.OptionParser()

  option_parser.add_option(
      '--mode',
      default='dev',
      help='switch indicating how to archive build (dev is only valid value)'
  )
  option_parser.add_option(
      '--target',
      default='Release',
      help='build target to archive (Debug or Release)'
  )
  option_parser.add_option('-target-os', help='os target to archive')
  option_parser.add_option(
      '--arch',
      default=archive_utils.BuildArch(),
      help='specify that target architecure of the build'
  )
  option_parser.add_option(
      '--src-dir',
      default='src',
      help='path to the top-level sources directory'
  )
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option(
      '--extra-archive-paths',
      default='',
      help='comma-separated lists of paths containing '
      'files named FILES, SYMBOLS and TESTS. These '
      'files contain lists of extra files to be '
      'that will be archived. The paths are relative '
      'to the directory given in --src-dir.'
  )
  option_parser.add_option(
      '--build-number',
      type='int',
      help='The build number of the builder running '
      'this script. we use it as the name of build '
      'archive directory'
  )
  option_parser.add_option(
      '--dry-run',
      action='store_true',
      help='Avoid making changes, for testing'
  )
  option_parser.add_option(
      '--ignore', default=[], action='append', help='Files to ignore'
  )
  option_parser.add_option(
      '--archive_host', default=archive_utils.Config.archive_host
  )
  option_parser.add_option(
      '--gs-bucket', help='The Google Storage bucket to archive the build to'
  )
  option_parser.add_option(
      '--gs-acl', help='The Google Storage ACL to apply to the archived build'
  )
  option_parser.add_option(
      '--build-name',
      default=None,
      help="Name to use for build directory instead of "
      "the slave build name"
  )
  option_parser.add_option(
      '--staging-dir',
      help='Directory to use for staging the archives. '
      'Default behavior is to automatically detect '
      'slave\'s build directory.'
  )
  chromium_utils.AddPropertiesOptions(option_parser)
  slave_utils_callback = slave_utils.AddOpts(option_parser)
  options, args = option_parser.parse_args()

  if args:
    raise archive_utils.StagingError('Unknown arguments: %s' % args)
  slave_utils_callback(options)

  if not options.ignore:
    # Independent of any other configuration, these exes and any symbol files
    # derived from them (i.e., any filename starting with these strings) will
    # not be archived or uploaded, typically because they're not built for the
    # current distributon.
    options.ignore = archive_utils.Config.exes_to_skip_entirely

  if options.mode == 'official':
    option_parser.error('Official mode is not supported here')
  elif options.mode == 'dev':
    options.dirs = {
        # Built files are stored here, in a subdir. named for the build version.
        'www_dir_base': archive_utils.Config.www_dir_base + 'snapshots',

        # Symbols are stored here, in a subdirectory named for the build
        # version.
        'symbol_dir_base': archive_utils.Config.www_dir_base + 'snapshots',
    }
  else:
    option_parser.error('Invalid options mode %s' % options.mode)

  if options.build_number is not None:
    s = StagerByBuildNumber(options)
  else:
    s = StagerByChromiumRevision(options)
  return s.ArchiveBuild()


if '__main__' == __name__:
  sys.exit(main())
