#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import glob
import os
import socket
import subprocess

TIMESTAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M')
HOSTNAME = socket.getfqdn().split('.', 1)[0]
BUILD_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir))


def GSUtil(from_path, to_path):
  print from_path, to_path
  subprocess.call([
      os.path.join(BUILD_DIR, 'third_party', 'gsutil', 'gsutil'),
      'cp', '-z', from_path.split('.')[-1], from_path,
      'gs://chromium-logs/%s/%s/%s' % (HOSTNAME, TIMESTAMP, to_path)])


def main():
  # See also: crbug.com/177922
  lkgr_path = os.path.join(BUILD_DIR, 'master.chromium.lkgr', 'lkgr_finder.log')
  if os.path.isfile(lkgr_path):
    GSUtil(lkgr_path, 'lkgr.log')
  for logpath in glob.glob(os.path.join(BUILD_DIR, 'masters', '*',
                                        'actions.log')):
    master = logpath.split(os.sep)[-2]
    print master
    if master.startswith('master.'):
      master = master[7:]
    GSUtil(logpath, '%s-actions.log' % master)

if __name__ == '__main__':
  main()
