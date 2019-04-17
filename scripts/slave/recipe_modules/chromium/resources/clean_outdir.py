#!/usr/bin/env python
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import argparse
import os
import sys
from datetime import datetime
from datetime import timedelta


def get_time_now():
  """Get current time.

  This is put into a seperate method to make writing tests easier

  Returns:
    datetime object representing time at the point the method was executed
  """
  return datetime.now()


def get_files_recursive(dir_path):
  """Get all the files under the given directory.

  Recursively retrive all the files under the given directory

  Args:
    dir_path: cannonical path to the directory

  Returns:
    A list containing absolute paths for all the files in the directory
  """
  all_files = []
  for root, _, fnames in os.walk(dir_path):
    for fname in fnames:
      all_files.append(os.path.join(root, fname))
  return all_files


def get_old_files_in_dir(directory, time_diff):
  """Get iterator of old files in the directory.

  Collects the list of all files in the directory and filters out the 'new' ones
  based on time_diff

  Args:
    directory: cannonical path to the out directory
    time_diff: timedelta object, time difference for old files

  Returns:
    A iterator of files that are 'old' in given directory wrt time_diff
  """
  curr_t = get_time_now()

  out_dir_files = []
  for fname in get_files_recursive(directory):
    fage = curr_t - datetime.fromtimestamp(os.path.getmtime(fname))
    if not os.path.islink(fname) and fage > time_diff:
      out_dir_files.append((fname, fage))

  return out_dir_files


def main(argv):
  """Delete old files from the out directory.

  The available options are to specify number of days and build directory.
  In case no input is given default value of 7 days is used.
  """
  descr = 'Delete old files from the out directory'
  arg_parser = argparse.ArgumentParser(description=descr)
  arg_parser.add_argument('--days-old',
                          type=int,
                          help ='Files older than or as old as this limit'
                                'are deleted, default=7 (days)',
                          default=7)
  arg_parser.add_argument('out_directory',
                          metavar='out_directory',
                          nargs=1,
                          help='path to the out directory')

  args = arg_parser.parse_args(argv[1:])

  out_dir = args.out_directory[0]

  time_diff = timedelta(days=args.days_old)

  if time_diff < timedelta(milliseconds=0):
    print('Cannot delete files from future', file=sys.stderr)
    return -1

  if not os.path.exists(out_dir):
    print("Error: {} doesn't exist".format(out_dir), file=sys.stderr)
    return -1
  else:
    print('Deleting files from {} directory'.format(out_dir), file=sys.stderr)

  # Delete the files that are old enough and print them
  for fname, fage in get_old_files_in_dir(out_dir, time_diff):
    print('({} old)\t Would have deleted:\t {}'.format(fage, fname))
    # NOTE: This is commented out to observe what files will be deleted, It
    #       will be enabled once it is determined that it is safe to delete
    #       the corresponding files
    # os.remove(fname)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
