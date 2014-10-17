# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Create a CL to update the SKP version."""


import os
import subprocess
import sys

from common.skia.global_constants import SKIA_REPO

sys.path.insert(0, os.path.join(os.getcwd(), 'common'))
from py.utils import git_utils



CHROMIUM_SKIA = 'https://chromium.googlesource.com/skia.git'
COMMIT_MSG = '''Update SKP version

Automatic commit by the RecreateSKPs bot.

TBR=
'''
SKIA_COMMITTER_EMAIL = 'borenet@google.com'
SKIA_COMMITTER_NAME = 'Eric Boren'


def main(chrome_src_path, browser_executable):
  subprocess.check_call(['git', 'config', '--local', 'user.name',
                         SKIA_COMMITTER_NAME])
  subprocess.check_call(['git', 'config', '--local', 'user.email',
                         SKIA_COMMITTER_EMAIL])
  if CHROMIUM_SKIA in subprocess.check_output(['git', 'remote', '-v']):
    subprocess.check_call(['git', 'remote', 'set-url', 'origin', SKIA_GIT_URL,
                           CHROMIUM_SKIA])

  version_file = 'SKP_VERSION'
  with git_utils.GitBranch(branch_name='update_skp_version',
                           commit_msg=COMMIT_MSG,
                           commit_queue=True):
    subprocess.check_call(['python', os.path.join('tools', 'skp',
                                                  'recreate_skps.py'),
                           chrome_src_path, browser_executable])


if '__main__' == __name__:
  main(*sys.argv[1:])
