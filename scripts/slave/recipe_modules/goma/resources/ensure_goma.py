#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import datetime
import os
import shutil
import subprocess
import sys


CONFIG = {
    'linux': {
        'repo': ('https://chrome-internal.googlesource.com/chrome/tools/'
                 'goma/linux.git'),
        'revision': '2c3d7c054dd17ad126be74c502ebb81acae4994f',
    },
}


def get_platform():
  if sys.platform.startswith('linux'):
    return 'linux'

  return None


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--target-dir', required=True)
  parser.add_argument('--download-from-google-storage-path', required=True)
  parser.add_argument('--canary', action='store_true')
  parser.add_argument('--depth', default=50,
                      help='number of depth for shallow clone')

  args = parser.parse_args()

  config = CONFIG[get_platform()]

  start = datetime.datetime.utcnow()
  client_dir = args.target_dir
  if not os.path.exists(client_dir):
    os.makedirs(client_dir)

  current_repo = subprocess.check_output(
      ['git', 'ls-remote', '--get-url'], cwd=client_dir).strip()
  if current_repo != config['repo']:
    print '[%s]: repo mismatch. initial clone' % (
        datetime.datetime.utcnow() - start)
    shutil.rmtree(client_dir)
    subprocess.check_call(['git', 'retry', 'clone', '--depth', str(args.depth),
                           config['repo'], client_dir])

  print '[%s]: fetch' % (datetime.datetime.utcnow() - start)
  subprocess.check_call(['git', 'retry', 'fetch'], cwd=client_dir)
  rev = config['revision']
  if args.canary:
    rev = 'refs/remotes/origin/HEAD'
  print '[%s]: reset %s' % (datetime.datetime.utcnow() - start, rev)
  subprocess.check_call(
      ['git', 'reset', '--hard', rev], cwd=client_dir)

  print '[%s]: download binaries' % (datetime.datetime.utcnow() - start)
  subprocess.check_call([sys.executable,
                         args.download_from_google_storage_path,
                         '--directory',
                         '--recursive',
                         '--bucket', 'chrome-goma',
                         client_dir])

  subprocess.check_call(
      [sys.executable, os.path.join(client_dir, 'fix_file_modes.py')])

  print '[%s]: done' % (datetime.datetime.utcnow() - start)
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
