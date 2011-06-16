#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to package a checkout's source and upload it to Google Storage."""


import os
import re
import sys

from common import chromium_utils
from slave import slave_utils


FILENAME = 'chromium-src.tgz'
GSBASE = 'gs://chromium-browser-csindex'


def main(argv):
  if not os.path.exists('src'):
    raise Exception('ERROR: no src directory to package, exiting')

  chromium_utils.RunCommand(['rm', '-f', FILENAME])
  if os.path.exists(FILENAME):
    raise Exception('ERROR: %s cannot be removed, exiting' % FILENAME)

  if chromium_utils.RunCommand(['tar', 'czvf', FILENAME, '--exclude=.svn',
                                'src/', 'tools/', 'o3d/']) != 0:
    raise Exception('ERROR: failed to create %s, exiting' % FILENAME)

  status = slave_utils.GSUtilCopyFile(FILENAME, GSBASE)
  if status != 0:
    raise Exception('ERROR: GSUtilCopyFile error %d. "%s" -> "%s"' % (
        status, FILENAME, GSBASE))

  (status, output) = slave_utils.GSUtilListBucket(GSBASE)
  if status != 0:
    raise Exception('ERROR: failed to get list of GSBASE, exiting' % GSBASE)

  regex = re.compile('\s*\d+\s+([-:\w]+)\s+%s/%s\n' % (GSBASE, FILENAME))
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
