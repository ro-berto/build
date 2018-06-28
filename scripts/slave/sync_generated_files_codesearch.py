#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import os.path
import subprocess
import sys


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--message', help='commit message', required=True)
  parser.add_argument('--dest-branch',
                      help='git branch in the destination repo to sync to',
                      default='master')
  parser.add_argument('--debug-dir',
                      help='optional dir containing the gen folder to include '
                           'in the checked-in repo',
                      default='Debug')
  parser.add_argument('source', help='directory to copy files from')
  parser.add_argument('dest', help='git checkout to copy files to')
  opts = parser.parse_args()


  # We pass --relative to rsync below, which treats the '/./' as the beginning
  # of the path for copying purposes. Everything after the '.' is recreated in
  # the destination directory.
  relative_source_path = os.path.join(opts.source, '.', opts.debug_dir,
                                      'gen')
  check_call([
      'rsync',
      '--recursive',
      '--stats',

      # Delete files in the git checkout that no longer exist in the build
      # output directory.
      '--delete-delay',
      '--delete-excluded',
      '--prune-empty-dirs',

      # Exclude everything except generated source code.
      # Note that we use a whitelist here instead of a blacklist, because:
      # 1. If we whitelist, the problem is that some legit files might be
      #    excluded. The solution to this is simple; we just whitelist the
      #    filetype and then they show up in CS a few hours later.
      # 2. If we blacklist, the problem is that some large binary files of a new
      #    filetype may show up. This could go undetected for a long time,
      #    causing the Git repo to start expanding until it gets too big for the
      #    builders to fetch. The fix in this case is essentially to blow away
      #    the generated Git repo and start again.
      # Since the problems caused by whitelisting are more easily managed than
      # those caused by blacklisting, we whitelist below.
      '--include=*.c',
      '--include=*.cc',
      '--include=*.cpp',
      '--include=*.css',
      '--include=*.h',
      '--include=*.html',
      '--include=*.java',
      '--include=*.js',
      '--include=*.json',
      '--include=*.proto',
      '--include=*.py',
      '--include=*.strings',
      '--include=*.txt',
      '--include=*.xml',
      '--include=*/',
      '--exclude=*',

      # Treat the '/./' in the SRC as the beginning of the path, so a
      # 'Debug/gen' directory is created in the destination.
      '--relative',

      relative_source_path,
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
  check_call(['git', 'push', 'origin', 'HEAD:%s' % opts.dest_branch],
              cwd=opts.dest)


def check_call(cmd, cwd=None):
  if cwd is None:
    print 'Running %s' % cmd
  else:
    print 'Running %s in %s' % (cmd, cwd)
  return subprocess.check_call(cmd, cwd=cwd)


if '__main__' == __name__:
  sys.exit(main())
