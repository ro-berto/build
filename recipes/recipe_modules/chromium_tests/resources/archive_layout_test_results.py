#!/usr/bin/env python3
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A tool to archive layout test results.

To archive files on Google Storage, pass a GS bucket name via --gs-bucket.
To control access to archives, pass a value for --gs-acl (e.g. 'public-read',
see https://developers.google.com/storage/docs/accesscontrol#extension
for other supported canned-acl values). If no gs_acl key is given,
then the bucket's default object ACL will be applied (see
https://developers.google.com/storage/docs/accesscontrol#defaultobjects).

When this is run, the current directory (cwd) should be the outer build
directory (e.g., chrome-release/build/).

For a list of command-line options, call this script with '--help'.
"""

import logging
import argparse
import os
import re
import socket
import sys
import tempfile
import time

ROOT_DIR = os.path.normpath(
    os.path.join(__file__, '..', '..', '..', '..', '..'))
sys.path.extend([
    os.path.join(ROOT_DIR, 'recipes'),
    os.path.join(ROOT_DIR, 'scripts'),
])

from common import chromium_utils
import bot_utils
import build_directory


def _CollectZipArchiveFiles(output_dir):
  """Returns a list of layout test result files to archive in a zip file."""
  file_list = []
  for path, _, files in os.walk(output_dir):
    rel_path = path[len(output_dir + '\\'):]
    for name in files:
      file_list.append(os.path.join(rel_path, name))
  return file_list


def maybe_archive_results_html(args):
  start = time.time()

  version_file = 'results.html.version'
  pattern = 'Version=(\d+)\.(\d+)'
  # Get local major and minor version number
  try:
    with open(os.path.join(args.results_dir, version_file)) as fp:
      s = fp.readline()
      result = re.compile(pattern).match(s)
      major, minor = int(result[1]), int(result[2])
  except FileNotFoundError:
    # Do nothing when version file does not exist in result dir.
    return

  cache_control = 'no-cache'

  print("Fetch remote version file...")
  # Get the remote major and minor version number
  with tempfile.TemporaryDirectory() as tmp_dir:
    rc = bot_utils.GSUtilCopy(
        '/'.join([args.gs_bucket, version_file]),
        os.path.join(tmp_dir, version_file),
        mimetype='text/plain',
        gs_acl=args.gs_acl,
        cache_control=cache_control,
        add_quiet_flag=True,
        compress=False)
    if rc:
      print("Failed to fetch version file from remote: %d" % rc)
      do_update = True
    else:
      do_update = False
      try:
        with open(os.path.join(tmp_dir, version_file)) as fp:
          s = fp.readline()
          result = re.compile(pattern).match(s)
          old_major, old_minor = int(result[1]), int(result[2])
          print(f"Remote version: {old_major}.{old_minor}")
          do_update = (major, minor) > (old_major, old_minor)
      except FileNotFoundError:
        do_update = True
  print("took %.1f seconds" % (time.time() - start))

  if do_update:
    files_to_archive = ['results.html', 'results.html.version']
    mimetypes = ['text/html', 'text/plain']
    for file_to_archive, mimetype in zip(files_to_archive, mimetypes):
      start = time.time()
      print(f"Archive {file_to_archive}...")
      rc = bot_utils.GSUtilCopy(
          os.path.join(args.results_dir, file_to_archive),
          '/'.join([args.gs_bucket, file_to_archive]),
          mimetype=mimetype,
          gs_acl=args.gs_acl,
          cache_control=cache_control,
          add_quiet_flag=True,
          compress=False)
      print("took %.1f seconds" % (time.time() - start))
      sys.stdout.flush()
      if rc:
        print("cp failed: %d" % rc)
        return


def archive_layout(args):
  chrome_dir = os.path.abspath(args.build_dir)
  results_dir_basename = os.path.basename(args.results_dir)
  args.results_dir = os.path.abspath(args.results_dir)
  print('Archiving results from %s' % args.results_dir)
  staging_dir = args.staging_dir or bot_utils.GetStagingDir(chrome_dir)
  print('Staging in %s' % staging_dir)
  if not os.path.exists(staging_dir):
    os.makedirs(staging_dir)

  file_list = _CollectZipArchiveFiles(args.results_dir)
  print()
  print("Archiving %d files" % len(file_list))
  print()

  zip_file = chromium_utils.MakeZip(staging_dir, results_dir_basename,
                                    file_list, args.results_dir)[1]

  builder_name = re.sub('[ .()]', '_', args.builder_name)
  build_number = str(args.build_number)
  last_change = args.revision

  print('last change: %s' % last_change)
  print('build name: %s' % builder_name)
  print('build number: %s' % build_number)
  print('host name: %s' % socket.gethostname())

  # Create a file containing last_change revision. This file will be uploaded
  # after all layout test results are uploaded so the client can check this
  # file to see if the upload for the revision is complete.
  # See crbug.com/574272 for more details.
  last_change_basename = 'LAST_CHANGE'
  last_change_file = os.path.join(staging_dir, last_change_basename)
  with open(last_change_file, 'w') as f:
    f.write(last_change)

  # In addition to the last_change file, above, we upload a zip file containing
  # all of the results. And, we actually need two copies of each, one archived
  # by build number and one representing the "latest" version.
  # TODO: Get rid of the need for the "latest" version.

  gs_build_dir = '/'.join([args.gs_bucket, builder_name, build_number])
  if args.step_name:
    gs_build_dir += '/' + args.step_name
  gs_build_results_dir = gs_build_dir + '/' + results_dir_basename

  if args.step_name:
    gs_latest_dir = '/'.join(
        [args.gs_bucket, builder_name, args.step_name, 'results'])
  else:
    gs_latest_dir = '/'.join([args.gs_bucket, builder_name, 'results'])
  gs_latest_results_dir = gs_latest_dir + '/' + results_dir_basename

  gs_acl = args.gs_acl

  maybe_archive_results_html(args)

  # These files never change, cache for a year.
  cache_control = "public, max-age=31556926"

  start = time.time()
  file_to_archive = 'full_results_jsonp.js'
  if args.task_ids:
    task_ids = args.task_ids.split(',')
    data = "\nSET_TASK_IDS(['" + "','".join(task_ids) + "']);"
    with open(os.path.join(args.results_dir, file_to_archive), "a") as f:
      f.write(data)
  print(f"Archive {file_to_archive}...")
  rc = bot_utils.GSUtilCopy(
      os.path.join(args.results_dir, file_to_archive),
      '/'.join([gs_build_dir, file_to_archive]),
      mimetype='text/javascript',
      gs_acl=gs_acl,
      cache_control=cache_control,
      add_quiet_flag=True,
      compress=True)
  print("took %.1f seconds" % (time.time() - start))
  sys.stdout.flush()
  if rc:
    print("cp failed: %d" % rc)
    return rc

  start = time.time()
  rc = bot_utils.GSUtilCopyFile(
      zip_file,
      gs_build_dir,
      gs_acl=gs_acl,
      cache_control=cache_control,
      add_quiet_flag=True)
  print("took %.1f seconds" % (time.time() - start))
  sys.stdout.flush()
  if rc:
    print("cp failed: %d" % rc)
    return rc

  start = time.time()
  rc = bot_utils.GSUtilCopyFile(
      last_change_file,
      gs_build_results_dir,
      gs_acl=gs_acl,
      cache_control=cache_control,
      add_quiet_flag=True)
  print("took %.1f seconds" % (time.time() - start))
  sys.stdout.flush()
  if rc:
    print("cp failed: %d" % rc)
    return rc

  if args.store_latest:
    # The 'latest' results need to be not cached at all (Cloud Storage defaults
    # to caching w/ a max-age=3600), since they change with every build. We also
    # do cloud->cloud copies for these, to save on network traffic.
    cache_control = 'no-cache'

    start = time.time()
    rc = bot_utils.GSUtilCopyFile(
        zip_file,
        gs_latest_dir,
        gs_acl=gs_acl,
        cache_control=cache_control,
        add_quiet_flag=True)
    print("took %.1f seconds" % (time.time() - start))
    sys.stdout.flush()
    if rc:
      print("cp failed: %d" % rc)
      return rc

    start = time.time()
    rc = bot_utils.GSUtilCopyFile(
        last_change_file,
        gs_latest_results_dir,
        gs_acl=gs_acl,
        cache_control=cache_control,
        add_quiet_flag=True)
    print("took %.1f seconds" % (time.time() - start))
    sys.stdout.flush()
    if rc:
      print("cp failed: %d" % rc)
      return rc

  return 0


def _ParseArgs():
  parser = argparse.ArgumentParser()
  # TODO(crbug.com/655798): Make --build-dir not ignored.
  parser.add_argument('--build-dir', help='ignored')
  parser.add_argument(
      '--results-dir', required=True, help='path to layout test results')
  parser.add_argument(
      '--builder-name',
      required=True,
      help='The name of the builder running this script.')
  parser.add_argument(
      '--build-number',
      type=int,
      required=True,
      help='Build number of the builder running this script.')
  parser.add_argument(
      '--revision',
      type=str,
      required=True,
      help=('Revision checked out. If this is not passed in, it will use the '
            'head revision from the working dir checkout.'))
  parser.add_argument(
      '--step-name',
      help='The name of the test step that produced '
      'these results.')
  parser.add_argument(
      '--gs-bucket',
      required=True,
      help='The Google Storage bucket to upload to.')
  parser.add_argument(
      '--gs-acl', help='The access policy for Google Storage files.')
  parser.add_argument(
      '--store-latest',
      action='store_true',
      help='If this script should update the latest results in'
      'cloud storage.')
  parser.add_argument(
      '--staging-dir',
      help='Directory to use for staging the archives. '
      'Default behavior is to automatically detect '
      'slave\'s build directory.')
  parser.add_argument('--task-ids', help='Task ids used in this test step.')
  bot_utils_callback = bot_utils.AddArgs(parser)

  args = parser.parse_args()
  args.build_dir = build_directory.GetBuildOutputDirectory()
  bot_utils_callback(args)
  return args


def main():
  args = _ParseArgs()
  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s %(filename)s:%(lineno)-3d'
      ' %(levelname)s %(message)s',
      datefmt='%y%m%d %H:%M:%S')
  return archive_layout(args)


if '__main__' == __name__:
  sys.exit(main())
