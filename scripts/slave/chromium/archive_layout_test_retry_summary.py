#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script is intended to archive retry summary results from
try bot retries of layout tests.

By keeping these retry summary results in the same place as the
layout test results from the first try (with patch), the retry
results can be easily fetched from the same location as the results.
"""

import argparse
import logging
import re
import socket
import sys

from slave import slave_utils


def ArchiveRetrySummary(args):
  args.builder_name = re.sub('[ .()]', '_', args.builder_name)
  print 'Builder name: %s' % args.builder_name
  print 'Build number: %s' % args.build_number
  print 'Host name: %s' % socket.gethostname()

  gs_base = '/'.join([args.gs_bucket, args.builder_name, args.build_number])
  slave_utils.GSUtilCopyFile(args.retry_summary_json, gs_base,
                             cache_control='public, max-age=31556926',
                             dest_filename=args.dest_filename)
  return 0


def _ParseArgs():
  parser = argparse.ArgumentParser()
  parser.add_argument('--retry-summary-json', type=str, required=True,
                      help='path to retry summary JSON file')
  parser.add_argument('--builder-name', type=str, required=True)
  parser.add_argument('--build-number', type=str, required=True)
  parser.add_argument('--gs-bucket', type=str, required=True)
  parser.add_argument('--dest-filename', type=str, required=True)
  slave_utils_callback = slave_utils.AddArgs(parser)
  args = parser.parse_args()
  slave_utils_callback(args)
  return args


def main():
  args = _ParseArgs()
  logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')
  return ArchiveRetrySummary(args)


if '__main__' == __name__:
  sys.exit(main())
