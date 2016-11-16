#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import subprocess
import sys


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--message', help='commit message', required=True)
  parser.add_argument('source', help='directory to copy files from')
  parser.add_argument('dest', help='git checkout to copy files to')
  opts = parser.parse_args()

  check_call([
      'rsync',
      '--recursive',
      '--stats',

      # Delete files in the git checkout that no longer exist in the build
      # output directory.
      '--delete-delay',
      '--delete-excluded',
      '--prune-empty-dirs',

      # Exclude some common binary files.
      '--cvs-exclude',
      '--exclude=*.bin',
      '--exclude=*.cache',
      '--exclude=*.pak',
      '--exclude=*.pyc',
      '--exclude=*.srcjar',

      # Treat the '/./' in the SRC as the beginning of the path, so a
      # 'Debug/gen' directory is created in the destination.
      '--relative',

      '%s/./Debug/gen' % opts.source,
      opts.dest,
  ])

  # Add the files to the git index, exit if there were no changes.
  check_call(['git', 'add', '--', '.'], cwd=opts.dest)
  status = subprocess.check_output(
      ['git', 'status', '--porcelain'], cwd=opts.dest)
  if not status:
    print 'No changes, exiting'
    return 0

  check_call(['git', 'commit', '-m', opts.message], cwd=opts.dest)
  check_call(['git', 'push', 'origin', 'master'], cwd=opts.dest)


def check_call(cmd, cwd=None):
  if cwd is None:
    print 'Running %s' % cmd
  else:
    print 'Running %s in %s' % (cmd, cwd)
  return subprocess.check_call(cmd, cwd=cwd)


if '__main__' == __name__:
  sys.exit(main())
