#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to extract a build, executed by a buildbot slave.
"""

import optparse
import os
import shutil
import sys
import traceback
import urllib
import urllib2

from common import chromium_utils
from slave import slave_utils


# Exit code to use for warnings, to distinguish script issues.
WARNING_EXIT_CODE = 88


@chromium_utils.RunAndPrintDots
def urlretrieve(*args, **kwargs):
  return urllib.urlretrieve(*args, **kwargs)


def real_main(options, args):
  """ Download a build, extract it to build\BuildDir\full-build-win32
      and rename it to build\BuildDir\Target
  """
  # TODO: need to get the build *output* directory passed in also so Linux
  # and Mac don't have to walk up a directory to get to the right directory.
  build_output_dir = None
  if chromium_utils.IsWindows() or chromium_utils.IsWine():
    build_output_dir = options.build_dir
  elif chromium_utils.IsLinux():
    build_output_dir = os.path.join(os.path.dirname(options.build_dir),
                                   'sconsbuild')
  elif chromium_utils.IsMac():
    build_output_dir = os.path.join(os.path.dirname(options.build_dir),
                                   'xcodebuild')
  else:
    raise NotImplementedError('%s is not supported.' % sys.platform)

  abs_build_dir = os.path.abspath(options.build_dir)
  abs_build_output_dir = os.path.abspath(build_output_dir)
  target_build_output_dir = os.path.join(abs_build_output_dir, options.target)

  # Find the revision that we need to download.
  current_revision = slave_utils.SubversionRevision(abs_build_dir)

  # Generic name for the archive.
  # TODO(thestig) We could use OverridePlatformName, but this is really the
  # only place where we need it right now.
  if chromium_utils.IsWine():
    archive_name = 'full-build-win32.zip'
  else:
    archive_name = 'full-build-%s.zip' % chromium_utils.PlatformName()

  # Just take the zip off the name for the output directory name.
  output_dir = os.path.join(abs_build_output_dir,
                            archive_name.replace('.zip', ''))

  # URL containing the version number.
  url = options.build_url.replace('.zip', '_%d.zip' % current_revision)

  # We try to download and extract 3 times.
  for tries in range(1, 4):
    print 'Try %d: Fetching build from %s...' % (tries, url)

    failure = False

    # Check if the url exists.
    try:
      content = urllib2.urlopen(url)
      content.close()
    except urllib2.HTTPError:
      print '%s is not found' % url
      failure = True

      # If 'revision' is set in build properties, we assume the build is
      # triggered automatically and so we halt on a missing build zip.  The
      # other case is if the build is forced, in which case we keep trying
      # later by looking for the latest build that's available.
      if ('revision' in options.build_properties and
          options.build_properties['revision'] != ''):
        return -1

    # If the url is valid, we download the file.
    if not failure:
      try:
        urlretrieve(url, archive_name)
        print '\nDownload complete'
      except IOError:
        print '\nFailed to download archived build'
        failure = True

    # If the versioned url failed, we try to get the latest build.
    if failure:
      print 'Fetching latest build...'
      try:
        urlretrieve(options.build_url, archive_name)
        print '\nDownload complete'
      except IOError:
        print '\nFailed to download generic archived build'
        # Try again...
        continue

    print 'Extracting build %s to %s...' % (archive_name, abs_build_output_dir)
    try:
      chromium_utils.RemoveDirectory(target_build_output_dir)
      chromium_utils.ExtractZip(archive_name, abs_build_output_dir)
      shutil.move(output_dir, target_build_output_dir)
    except (OSError, IOError):
      print 'Failed to extract the build.'
      # Print out the traceback in a nice format
      traceback.print_exc()
      # Try again...
      continue

    # If we got the latest build, then figure out its revision number.
    if failure:
      print "Trying to determine the latest build's revision number..."
      try:
        build_revision_file_name = os.path.join(target_build_output_dir,
                                                'FULL_BUILD_REVISION')
        build_revision_file = open(build_revision_file_name, 'r')
        print 'Latest build is revision: %s' % build_revision_file.read()
        build_revision_file.close()
      except IOError:
        print "Could not determine the latest build's revision number"

    if failure:
      # We successfully extracted the archive, but it was the generic one.
      return WARNING_EXIT_CODE
    return 0

  # If we get here, that means that it failed 3 times. We return a failure.
  return -1


def main():
  option_parser = optparse.OptionParser()

  option_parser.add_option('', '--target',
                           help='build target to archive (Debug or Release)')
  option_parser.add_option('', '--build-dir',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('', '--build-url',
                           help='url where to find the build to extract')
  # TODO(cmp): Remove --halt-on-missing-build when the buildbots are upgraded
  #            to not use this argument.
  option_parser.add_option('--halt-on-missing-build', action='store_true',
                           default=False,
                           help='whether to halt on a missing build')
  option_parser.add_option('--build-properties', action='callback',
                           callback=chromium_utils.convert_json, type='string',
                           nargs=1, default={},
                           help='build properties in JSON format')
  option_parser.add_option('--factory-properties', action='callback',
                           callback=chromium_utils.convert_json, type='string',
                           nargs=1, default={},
                           help='factory properties in JSON format')

  options, args = option_parser.parse_args()
  return real_main(options, args)


if '__main__' == __name__:
  sys.exit(main())
