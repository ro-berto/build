#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to package a checkout's source and upload it to Google Storage."""


import os
import re
import sys
from time import strftime

from common import chromium_utils
from slave import slave_utils


FILENAME = 'chromium-src.tar.bz2'
GSBASE = 'gs://chromium-browser-csindex'
GSACL = 'public-read'


def main(argv):
  if not os.path.exists('src'):
    raise Exception('ERROR: no src directory to package, exiting')

  completed_hour = strftime('%H')
  completed_filename = '%s.%s' % (FILENAME, completed_hour)
  partial_filename = '%s.partial' % completed_filename

  chromium_utils.RunCommand(['rm', '-f', partial_filename])
  if os.path.exists(partial_filename):
    raise Exception('ERROR: %s cannot be removed, exiting' % partial_filename)

  if chromium_utils.RunCommand(['tar', 'cjvf', partial_filename,
                                '--exclude=.svn', 'src/', 'tools/',
                                'o3d/']) != 0:
    raise Exception('ERROR: failed to create %s, exiting' % partial_filename)

  status = slave_utils.GSUtilDeleteFile('%s/%s' % (GSBASE, completed_filename))
  if status != 0:
    raise Exception('ERROR: GSUtilDeleteFile error %d. "%s"' % (
        status, '%s/%s' % (GSBASE, completed_filename)))

  status = slave_utils.GSUtilDeleteFile('%s/%s' % (GSBASE, partial_filename))
  if status != 0:
    raise Exception('ERROR: GSUtilDeleteFile error %d. "%s"' % (
        status, '%s/%s' % (GSBASE, partial_filename)))

  status = slave_utils.GSUtilCopyFile(partial_filename, GSBASE, gs_acl=GSACL)
  if status != 0:
    raise Exception('ERROR: GSUtilCopyFile error %d. "%s" -> "%s"' % (
        status, partial_filename, GSBASE))

  status = slave_utils.GSUtilMoveFile('%s/%s' % (GSBASE, partial_filename),
                                      '%s/%s' % (GSBASE, completed_filename))
  if status != 0:
    raise Exception('ERROR: GSUtilMoveFile error %d. "%s" -> "%s"' % (
        status, '%s/%s' % (GSBASE, partial_filename),
        '%s/%s' % (GSBASE, completed_filename)))

  (status, output) = slave_utils.GSUtilListBucket(GSBASE)
  if status != 0:
    raise Exception('ERROR: failed to get list of GSBASE, exiting' % GSBASE)

  regex = re.compile('\s*\d+\s+([-:\w]+)\s+%s/%s\n' % (GSBASE,
                                                       completed_filename))
  match_data = regex.match(output)
  modified_time = None
  if match_data:
    modified_time = match_data.group(1)
  if not modified_time:
    raise Exception('ERROR: could not get modified_time, exiting')
  print 'Last modified time: %s' % modified_time

  return 0


if '__main__' == __name__:
  sys.exit(main(None))
