#!/usr/bin/env python3
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
from __future__ import print_function

import argparse
import errno
import os.path
import re
import shutil
import subprocess
import sys
import zipfile

from kythe.proto import analysis_pb2


def has_allowed_extension(filename):
  """ Checks if this file has one of the approved extensions. """

  # Exclude everything except generated source code.
  # Note that we use a allowlist here instead of a blacklist, because:
  # 1. If we allowlist, the problem is that some legit files might be excluded.
  #    The solution to this is simple; we just allowlist the filetype and then
  #    they show up in CS a few hours later.
  # 2. If we blacklist, the problem is that some large binary files of a new
  #    filetype may show up. This could go undetected for a long time, causing
  #    the Git repo to start expanding until it gets too big for the builders to
  #    fetch. The fix in this case is essentially to blow away the generated Git
  #    repo and start again.
  # Since the problems caused by allowlisting are more easily managed than those
  # caused by blacklisting, we allowlist below.
  allowed_extensions = {
      'c', 'cc', 'cpp', 'css', 'desugardeps', 'h', 'html', 'inc', 'java', 'js',
      'json', 'proto', 'py', 'strings', 'txt', 'xml'
  }
  dot_index = filename.rfind(".")
  return dot_index != -1 and filename[dot_index + 1:] in allowed_extensions


def translate_root(source_root, target_root, filename):
  """ Given a root path (source_root), a path under that path (filename) and
      another root path (target_root), translate the path such that it has the
      new root instead of the old one, but is otherwise unchanged.

      For example:
      translate_root('/foo', '/bar', '/foo/baz') => '/bar/baz'
  """

  relative_to_root = os.path.join(filename[len(source_root) + 1:])
  return os.path.join(target_root, relative_to_root)


def kzip_input_paths(kzip_path):
  """ Get the set of all required_inputs in the kzip. """

  required_inputs = set()
  try:
    with zipfile.ZipFile(
        kzip_path, 'r', zipfile.ZIP_DEFLATED, allowZip64=True) as kzip:

      for zip_info in kzip.infolist():
        # kzip should contain following structure:
        # foo/
        # foo/files
        # foo/files/bar
        # foo/pbunits
        # foo/pbunits/bar
        # We only care for the compilation units in foo/pbunits/*. See
        # https://kythe.io/docs/kythe-kzip.html for more on kzips.
        if not re.match(r'.*/pbunits/\w*', zip_info.filename):
          continue

        cu = analysis_pb2.IndexedCompilation()
        with kzip.open(zip_info, 'r') as f:
          cu.ParseFromString(f.read())

        for r in cu.unit.required_input:
          p = r.v_name.path

          # Absolute paths refer to libraries. Ignore these.
          if not os.path.isabs(p) and has_allowed_extension(p):
            # package_index may adjust vname paths. Add possible adjustments to
            # the required_inputs set.
            parts = p.split(os.sep)

            # Don't sync any temporary files. These aren't actually referenced.
            if 'tmp' in parts:
              continue

            for i in range(len(parts)):
              # Kzips use forward slashes.
              required_inputs.add('/'.join(parts[i:]))
  except zipfile.BadZipfile as e:
    print('Error reading kzip file %s: %s' % (kzip_path, e))

  return required_inputs


def copy_generated_files(source_dir, dest_dir, kzip_input_suffixes=None):
  try:
    os.makedirs(dest_dir)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

  def is_referenced(path):
    # Since kzip_input_suffixes is a set of path endings, check each ending
    # of dest_file for membership in the set. Checking this way is faster than
    # linear time search with endswith.
    dest_parts = path.split(os.sep)
    for i in range(len(dest_parts)):
      # Kzips use forward slashes.
      check = '/'.join(dest_parts[i:])
      if check in kzip_input_suffixes:
        return True
    return False

  # First, delete everything in dest that:
  #   * isn't in source or
  #   * doesn't match the allowed extensions or
  #   * (if kzip is provided,) isn't referenced in the kzip
  for dirpath, _, filenames in os.walk(dest_dir):
    for filename in filenames:
      dest_file = os.path.join(dirpath, filename)
      source_file = translate_root(dest_dir, source_dir, dest_file)

      if not os.path.exists(source_file) or \
          not has_allowed_extension(source_file):
        print('Deleting file:', dest_file)
        os.remove(dest_file)
      elif kzip_input_suffixes and not is_referenced(dest_file):
        print('Deleting file not referenced by kzip:', dest_file)
        os.remove(dest_file)

  # Second, copy everything that matches the allowlist from source to dest. If
  # kzip is provided, don't copy files that aren't referenced.
  for dirpath, _, filenames in os.walk(source_dir):
    if dirpath != source_dir:
      try:
        os.mkdir(translate_root(source_dir, dest_dir, dirpath))
      except OSError as e:
        if e.errno != errno.EEXIST:
          raise

    for filename in filenames:
      # Don't sync any temporary files. These aren't actually referenced.
      file_parts = filename.split(os.sep)
      if 'tmp' in file_parts:
        continue

      if not has_allowed_extension(filename) \
          or kzip_input_suffixes and not is_referenced(filename):
        continue

      source_file = os.path.join(dirpath, filename)

      # arm-generic builder runs into an issue where source_file disappears by
      # the time it's copied. Check source_file so the builder doesn't fail.
      if not os.path.exists(source_file):
        print('File does not exist:', source_file)
        continue

      dest_file = translate_root(source_dir, dest_dir, source_file)

      if not os.path.exists(dest_file):
        print('Adding file:', dest_file)
      shutil.copyfile(source_file, dest_file)

  # Finally, delete any empty directories. We keep going to a fixed point, to
  # remove directories that contain only other empty directories.
  dirs_to_examine = [
      dirpath for dirpath, _, _ in os.walk(dest_dir) if dirpath != dest_dir
  ]
  while dirs_to_examine != []:
    d = dirs_to_examine.pop()

    # We make no effort to deduplicate paths in dirs_to_examine, so we might
    # have already removed this path.
    if os.path.exists(d) and os.listdir(d) == []:
      print('Deleting empty directory:', d)
      os.rmdir(d)

      # The parent dir might be empty now, so add it back into the list.
      parent_dir = os.path.dirname(d.rstrip(os.sep))
      if parent_dir != dest_dir:
        dirs_to_examine.append(parent_dir)

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--message', help='commit message', required=True)
  parser.add_argument(
      '--dest-branch',
      help='git branch in the destination repo to sync to',
      default='main')
  parser.add_argument(
      '--kzip-prune',
      help='kzip to reference when selecting which source files to copy',
      default='')
  parser.add_argument(
      '--dry-run',
      action='store_true',
      help='if set, does a dry run of push to remote repo.')
  parser.add_argument(
      '--copy',
      action='append',
      help=('a copy configuration that maps a source dir to a target dir in '
            'dest_repo. takes the format /path/to/src;dest_dir'),
      required=True)
  parser.add_argument('dest_repo', help='git checkout to copy files to')
  opts = parser.parse_args()

  kzip_input_suffixes = None
  if opts.kzip_prune:
    kzip_input_suffixes = kzip_input_paths(opts.kzip_prune)

  for c in opts.copy:
    source, dest = c.split(';')
    copy_generated_files(source, os.path.join(opts.dest_repo, dest),
                         kzip_input_suffixes)

  # Add the files to the git index, exit if there were no changes.
  check_call(['git', 'add', '--', '.'], cwd=opts.dest_repo)
  check_call(['git', 'status'], cwd=opts.dest_repo)
  check_call(['git', 'diff'], cwd=opts.dest_repo)
  status = subprocess.check_output(['git', 'status', '--porcelain'],
                                   cwd=opts.dest_repo)
  if not status:
    print('No changes, exiting')
    return 0

  check_call(['git', 'commit', '-m', opts.message], cwd=opts.dest_repo)
  if opts.dry_run:
    check_call([
        'git', 'push', '-o', 'nokeycheck', '--dry-run', 'origin',
        'HEAD:%s' % opts.dest_branch
    ],
               cwd=opts.dest_repo)
  else:
    check_call([
        'git', 'push', '-o', 'nokeycheck', 'origin',
        'HEAD:%s' % opts.dest_branch
    ],
               cwd=opts.dest_repo)


def check_call(cmd, cwd=None):
  if cwd is None:
    print('Running %s' % cmd)
  else:
    print('Running %s in %s' % (cmd, cwd))
  return subprocess.check_call(cmd, cwd=cwd)


if '__main__' == __name__:
  sys.exit(main())
