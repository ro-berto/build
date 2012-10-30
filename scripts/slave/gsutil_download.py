#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module for downloading files from Google Storage."""

import distutils.version
import optparse

from slave import slave_utils


def DownloadLatestFile(base_url, partial_name, dst):
  """Get the latest archived object with the given base url and partial name.

  Args:
    base_url: Base Google Storage archive URL (gs://...) containing the build.
    partial_name: Partial name of the archive file to download.
    dst: Destination file/directory where the file will be downloaded.

  Raises:
    Exception: If unable to find or download a file.
  """
  base_url_glob = '%s/**' % base_url.rstrip('/')
  result = slave_utils.GSUtilListBucket(base_url_glob, ['-l'])

  if not result or result[0]:
    raise Exception('Could not find any archived files.')

  files = [b.split()[2] for b in result[1].split('\n')
           if partial_name in b]

  files = [distutils.version.LooseVersion(x) for x in files]
  newest_file = str(max(files))
  slave_utils.GSUtilDownloadFile(newest_file, dst)


def main():
  desc = ('Download the file with the given base URL and partial name. '
          'If there are multiple matching files, the newest is downloaded '
          'assuming the full URL follows a loose versioning format.')
  parser = optparse.OptionParser(description=desc)

  parser.add_option('--base-url',
                    help='Google Storage base URL (gs://...) containing the '
                         'file.')
  parser.add_option('--partial-name',
                    help='Partial name of the file to download.')
  parser.add_option('--dst', help='Path to the destination file/directory.')
  (options, args) = parser.parse_args()

  if args:
    parser.error('Unknown arguments: %s.' % args)

  if not (options.base_url and options.partial_name and options.dst):
    parser.error('Missing one or more required arguments.')

  DownloadLatestFile(base_url=options.base_url,
                     partial_name=options.partial_name,
                     dst=options.dst)


if __name__ == '__main__':
  main()
