#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import os
import shutil
import subprocess
import sys


CONFIG = {
    'linux': {
        'repo': ('https://chrome-internal.googlesource.com/chrome/tools/'
                 'goma/linux.git'),
        'revision': 'd401706dd3d6bb1559d0234ffacd6c17efbbc2d6',
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

  args = parser.parse_args()

  config = CONFIG[get_platform()]

  client_dir = args.target_dir
  if not os.path.exists(client_dir):
    os.makedirs(client_dir)

  current_repo = subprocess.check_output(
      ['git', 'ls-remote', '--get-url'], cwd=client_dir).strip()
  if current_repo != config['repo']:
    shutil.rmtree(client_dir)
    subprocess.check_call(['git', 'clone', config['repo'], client_dir])

  subprocess.check_call(['git', 'fetch'], cwd=client_dir)
  rev = config['revision']
  if args.canary:
    rev = 'refs/heads/master'
  subprocess.check_call(
      ['git', 'reset', '--hard', rev], cwd=client_dir)

  subprocess.check_call([sys.executable,
                         args.download_from_google_storage_path,
                         '--directory',
                         '--recursive',
                         '--bucket', 'chrome-goma',
                         client_dir])

  subprocess.check_call(
      [sys.executable, os.path.join(client_dir, 'fix_file_modes.py')])

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
