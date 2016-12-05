#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

#
# This script can be run using below command from
# directory where this script locates.
#
# 1. Calculate the number of build job running in parallel
#    using goma for buildbots.
#
# $ ../../../../tools/runit.py ./utils.py jobs --file-path job.txt
#

import argparse
import sys

from slave import goma_utils

def main():
  parser = argparse.ArgumentParser(
      description='utility for goma recipe module.')

  subparsers = parser.add_subparsers(help='commands for goma utils')

  parser_jobs = subparsers.add_parser(
      'jobs', help='subcommand to get recommended or '
      'hostname specific goma jobs')
  parser_jobs.set_defaults(command='jobs')
  parser_jobs.add_argument('--file-path', required=True,
                           help='path of file job number written')

  args = parser.parse_args()

  if args.command == 'jobs':
    with open(args.file_path, 'w') as f:
      f.write('%d' % goma_utils.DetermineGomaJobs())


if '__main__' == __name__:
  sys.exit(main())
