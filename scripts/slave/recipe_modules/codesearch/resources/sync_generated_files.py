#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import errno
import os.path
import shutil
import subprocess
import sys

def has_whitelisted_extension(filename):
  """ Checks if this file has one of the approved extensions. """

  # Exclude everything except generated source code.
  # Note that we use a whitelist here instead of a blacklist, because:
  # 1. If we whitelist, the problem is that some legit files might be excluded.
  #    The solution to this is simple; we just whitelist the filetype and then
  #    they show up in CS a few hours later.
  # 2. If we blacklist, the problem is that some large binary files of a new
  #    filetype may show up. This could go undetected for a long time, causing
  #    the Git repo to start expanding until it gets too big for the builders to
  #    fetch. The fix in this case is essentially to blow away the generated Git
  #    repo and start again.
  # Since the problems caused by whitelisting are more easily managed than those
  # caused by blacklisting, we whitelist below.
  extension_whitelist = {'c', 'cc', 'cpp', 'css', 'h', 'html', 'java', 'js',
                         'json', 'proto', 'py', 'strings', 'txt', 'xml'}
  dot_index = filename.rfind(".")
  return dot_index != -1 and filename[dot_index + 1:] in extension_whitelist

def translate_root(source_root, target_root, filename):
  """ Given a root path (source_root), a path under that path (filename) and
      another root path (target_root), translate the path such that it has the
      new root instead of the old one, but is otherwise unchanged.

      For example:
      translate_root('/foo', '/bar', '/foo/baz') => '/bar/baz'
  """

  relative_to_root = os.path.join(filename[len(source_root) + 1:])
  return os.path.join(target_root, relative_to_root)

def copy_generated_files(source, dest, debug_dir):
  source_root = os.path.join(source, debug_dir, "gen")
  dest_root = os.path.join(dest, debug_dir, "gen")

  try:
    os.makedirs(dest_root)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

  # First, delete everything in dest that either isn't in source, or doesn't
  # match the whitelist.
  for dirpath, _, filenames in os.walk(dest_root):
    for filename in filenames:
      dest_file = os.path.join(dirpath, filename)
      source_file = translate_root(dest_root, source_root, dest_file)

      if not os.path.exists(source_file) or \
          not has_whitelisted_extension(source_file):
        print "DELETING FILE:", dest_file
        os.remove(dest_file)

  # Second, copy everything that matches the whitelist from source to dest.
  for dirpath, _, filenames in os.walk(source_root):
    if dirpath != source_root:
      try:
        os.mkdir(translate_root(source_root, dest_root, dirpath))
      except OSError as e:
        if e.errno != errno.EEXIST:
          raise

    for filename in filenames:
      if not has_whitelisted_extension(filename):
        continue

      source_file = os.path.join(dirpath, filename)
      dest_file = translate_root(source_root, dest_root, source_file)

      if not os.path.exists(dest_file):
        print "ADDING FILE:", dest_file
      shutil.copyfile(source_file, dest_file)

  # Finally, delete any empty directories. We keep going to a fixed point, to
  # remove directories that contain only other empty directories.
  dirs_to_examine = [dirpath for dirpath, _, _ in os.walk(dest_root)
                     if dirpath != dest_root]
  while dirs_to_examine != []:
    d = dirs_to_examine.pop()

    # We make no effort to deduplicate paths in dirs_to_examine, so we might
    # have already removed this path.
    if os.path.exists(d) and os.listdir(d) == []:
      print "DELETING DIRECTORY:", d
      os.rmdir(d)

      # The parent dir might be empty now, so add it back into the list.
      parent_dir = os.path.dirname(d.rstrip(os.sep))
      if parent_dir != dest_root:
        dirs_to_examine.append(parent_dir)

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
  parser.add_argument('--dry-run', action='store_true',
                      help='if set, does a dry run of push to remote repo.')
  parser.add_argument('source', help='directory to copy files from')
  parser.add_argument('dest', help='git checkout to copy files to')
  opts = parser.parse_args()

  copy_generated_files(opts.source, opts.dest, opts.debug_dir)

  # Add the files to the git index, exit if there were no changes.
  check_call(['git', 'add', '--', '.'], cwd=opts.dest)
  check_call(['git', 'status'], cwd=opts.dest)
  check_call(['git', 'diff'], cwd=opts.dest)
  status = subprocess.check_output(
      ['git', 'status', '--porcelain'], cwd=opts.dest)
  if not status:
    print 'No changes, exiting'
    return 0

  check_call(['git', 'commit', '-m', opts.message], cwd=opts.dest)
  if opts.dry_run:
    check_call(['git', 'push', '--dry-run', 'origin',
                'HEAD:%s' % opts.dest_branch], cwd=opts.dest)
  else:
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
