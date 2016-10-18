#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script is intended to archive retry summary results from
try bot retries for layout tests along with layout test results.

The purpose if this is so that these retry results can be fetched
from the same place that the first run results are fetched.
"""

import logging
import argparse
import os
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
  slave_utils.GSUtilCopyFile(args.retry_summary_json,
                             gs_base,
                             cache_control="public, max-age=31556926")
  slave_utils.GSUtilMoveFile(os.path.join(gs_base, args.retry_summary_json),
                             os.path.join(gs_base, 'retry_summary.json'))
  return 0


def _ParseArgs():
  parser = argparse.ArgumentParser()
  parser.add_argument('--retry-summary-json', type=str, required=True,
                      help='path to retry summary JSON file')
  parser.add_argument('--builder-name', type=str, required=True)
  parser.add_argument('--build-number', type=str, required=True)
  parser.add_argument('--gs-bucket', type=str, required=True)
  return parser.parse_args()


def main():
  args = _ParseArgs()
  logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')
  return ArchiveRetrySummary(args)


if '__main__' == __name__:
  sys.exit(main())
