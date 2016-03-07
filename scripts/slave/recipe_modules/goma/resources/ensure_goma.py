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
        'revision': 'a9038be2338f0e1739f84c9e46e0b7f47d92c269',
    },
}


def get_platform():
  if sys.platform.startswith('linux'):
    return 'linux'

  return None


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--target-dir', required=True)

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
  subprocess.check_call(
      ['git', 'reset', '--hard', config['revision']], cwd=client_dir)

  subprocess.check_call(['download_from_google_storage',
                         '--directory',
                         '--recursive',
                         '--bucket', 'chrome-goma',
                         client_dir])

  subprocess.check_call(
      [sys.executable, os.path.join(client_dir, 'fix_file_modes.py')])

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
