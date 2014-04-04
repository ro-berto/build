#!/usr/bin/python
#
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Wrapper that does auto-retry for gsutil.

Pass the path to the real gsutil as the first argument.

Deletes ~/.gsutil after failures, which sometimes helps.
"""


import logging
import argparse
import os
import shutil
import subprocess
import sys


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument(
      'command', metavar='ARG', nargs='+',
      help='the gsutil command (including the gsutil path) to run')
  parser.add_argument('--retries', metavar='N', nargs=1, default=2, type=int,
                      help='number of times to retry on failure (default 2)')
  args = parser.parse_args()
  cmd = args.command

  for r in range(args.retries):
    retcode = subprocess.call(cmd)

    if retcode == 0: return 0
    logging.warning('Command %s failed with retcode %d, try %d.' % (
        ' '.join(cmd), retcode, r + 1))

    # Failed at least once, try deleting the tracker files
    try:
      gsutil_dir = os.path.join(os.environ['HOME'], '.gsutil')
      logging.info('Removing %s' % gsutil_dir)
      shutil.rmtree(gsutil_dir)
    except BaseException as e:
      logging.warning('Deleting tracker files failed: %s' % e)

  logging.error('Command %s failed %d retries, giving up.' % (
      ' '.join(args.command), args.retries))

  return retcode


if __name__ == '__main__':
  sys.exit(main(sys.argv))
