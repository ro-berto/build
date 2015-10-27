#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import argparse
import os
import re
import subprocess
import sys
import time

from stat import S_ISDIR

DIR = "/b/build/slave"
WIN_PREFIX = "/cygdrive/c"
FULLNESS_LIMIT = 90   # Proceed if the disk is at least this percent full.
AGE_LIMIT = 86400  # Dirs can be deleted if they've been unchanged this long.
RE_SLAVE = re.compile(r"^[a-z_]+$")  # Matches the slave subdirectory names,
                                     # which are made only of a-z or _ chars.


# Need to provide a hook for overriding stat() and print() because neither can
# be mocked in the usual way.
def main(force=False, stat=os.stat, Print=print):
  """force(bool): if True, analysis is performed for any disk utilization."""
  now = time.time()

  # Change to the right build directory for the platform.
  try:
    os.chdir(WIN_PREFIX + DIR)
  except OSError:
    os.chdir(DIR)

  df = subprocess.Popen(["df", "."], stdout=subprocess.PIPE)
  output = df.communicate()[0]
  lines = filter(None, output.split("\n"))
  assert len(lines) == 2
  headers = lines[0].split()
  if headers[4] == "Use%":
    percent_full = lines[1].split()[4]
  elif len(headers) >= 8 and headers[7] == "%iused":
    percent_full = lines[1].split()[7]

  percent_full = int(percent_full.rstrip("%"))

  if not force:
    if percent_full < FULLNESS_LIMIT:
      Print("The disk is only %d%% full." % percent_full)
      return 0
    else:
      Print("The disk is %d%% full, and that's bad." % percent_full)

  eligible = {}
  max_len = 0
  for f in os.listdir("."):
    if not RE_SLAVE.match(f):
      continue
    if not os.path.exists(f + "/build"):
      continue
    statbuf = stat(f)
    mode = statbuf.st_mode
    if not S_ISDIR(mode):
      continue
    ctime = statbuf.st_ctime
    age = now - ctime
    if age < AGE_LIMIT:
      continue
    eligible[f] = age
    if len(f) > max_len:
      max_len = len(f)

  if eligible:
    Print("You should delete the following:")
    Print()
  else:
    Print("But there's nothing to delete.")
    return 1

  for slave, age in sorted(eligible.items(), key=lambda x: (-x[1], x[0])):
    days_old = age / 86400
    pad_len = max_len - len(slave)
    slave += " " * pad_len
    Print("rm -rf %s/%s # %d days old" % (DIR, slave, days_old))

  Print()
  Print()
  Print("Or, if you want to check their filesizes first:")
  Print()
  Print("cd %s && du -sh %s" % (DIR, " ".join(sorted(eligible))))

  return 0


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--force', default=False, action="store_true",
                      help="Force analysis even if the disk is not close "
                      "to full.")
  args = parser.parse_args()
  sys.exit(main(force=args.force))
