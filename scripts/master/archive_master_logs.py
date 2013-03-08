#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Upload buildbot logfiles to google storage."""

import datetime
import glob
import os
import socket
import subprocess

TIMESTAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M')
HOSTNAME = socket.getfqdn().split('.', 1)[0]
BUILD_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir))


def GSUtilCopy(from_path, to_path):
  """Upload a file to Google Storage."""
  # -z <ext> instructs gsutil to gzip files with that extension
  # and add 'Content-Encoding: gzip' to header.
  # gsutil determines file extension by looking a last segment
  # after spliting path on '.'.
  return subprocess.call([
      os.path.join(BUILD_DIR, 'third_party', 'gsutil', 'gsutil'),
      'cp', '-z', from_path.split('.')[-1], from_path,
      'gs://chromium-logs/%s/%s/%s' % (HOSTNAME, TIMESTAMP, to_path)])


def main():
  returncode = 0
  # See also: crbug.com/177922
  lkgr_path = os.path.join(
      BUILD_DIR, 'masters', 'master.chromium.lkgr', 'lkgr_finder.log')
  if os.path.isfile(lkgr_path):
    returncode |= GSUtilCopy(lkgr_path, 'lkgr.log')
  for logpath in glob.glob(
      os.path.join(BUILD_DIR, 'masters', '*', 'actions.log')):
    master = logpath.split(os.sep)[-2]
    if master.startswith('master.'):
      master = master[7:]
    returncode |= GSUtilCopy(logpath, '%s-actions.log' % master)
  return returncode


if __name__ == '__main__':
  exit(main())
