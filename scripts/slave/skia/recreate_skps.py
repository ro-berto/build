# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Create a CL to update the SKP version."""


import argparse
import os
import subprocess
import sys

from common.skia.global_constants import SKIA_REPO

sys.path.insert(0, os.path.join(os.getcwd(), 'common'))
# pylint:disable=F0401
from py.utils import git_utils



CHROMIUM_SKIA = 'https://chromium.googlesource.com/skia.git'
COMMIT_MSG = '''Update SKP version

Automatic commit by the RecreateSKPs bot.

TBR=
'''
SKIA_COMMITTER_EMAIL = 'skia.buildbots@gmail.com'
SKIA_COMMITTER_NAME = 'skia.buildbots'


def main(chrome_src_path, browser_executable, dry_run=False):
  if dry_run:
    print 'Not committing results since --dry-run was provided'

  subprocess.check_call(['git', 'config', '--local', 'user.name',
                         SKIA_COMMITTER_NAME])
  subprocess.check_call(['git', 'config', '--local', 'user.email',
                         SKIA_COMMITTER_EMAIL])
  if CHROMIUM_SKIA in subprocess.check_output(['git', 'remote', '-v']):
    subprocess.check_call(['git', 'remote', 'set-url', 'origin', SKIA_REPO,
                           CHROMIUM_SKIA])

  with git_utils.GitBranch(branch_name='update_skp_version',
                           commit_msg=COMMIT_MSG,
                           commit_queue=not dry_run):
    subprocess.check_call(['python', os.path.join('tools', 'skp',
                                                  'recreate_skps.py'),
                           chrome_src_path, browser_executable])


if '__main__' == __name__:
  parser = argparse.ArgumentParser()
  parser.add_argument("chrome_src_path")
  parser.add_argument("browser_executable")
  parser.add_argument("--dry-run", action="store_true")
  args = parser.parse_args()
  main(args.chrome_src_path, args.browser_executable, args.dry_run)
