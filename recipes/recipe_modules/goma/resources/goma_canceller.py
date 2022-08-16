#!/usr/bin/env python3
# Copyright (c) 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script is used to detect cancellation of builds and run `goma_ctl.py ensure_stop`.

Run like
$ goma_canceller.py /path/to/goma_ctl.py

"""

import sys
import signal
import subprocess
import time

_IS_EXITED = False


def do_exit():
  global _IS_EXITED
  subprocess.check_call(['python3', sys.argv[1], 'ensure_stop'])
  _IS_EXITED = True
  print('goma_canceller stopped goma')


def main():
  print('goma_canceller started')
  signal.signal(
      (
          signal.SIGBREAK  # pylint: disable=no-member
          if sys.platform.startswith('win') else signal.SIGTERM),
      lambda _signum, _frame: do_exit())

  while not _IS_EXITED:
    time.sleep(1)

  print('goma_canceller exiting')


if '__main__' == __name__:
  sys.exit(main())
