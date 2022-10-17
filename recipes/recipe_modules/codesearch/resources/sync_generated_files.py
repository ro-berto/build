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


def has_secrets(filepath):
  with open(filepath, 'r') as f:
    text = f.read()
    patterns = (
        # Patterns adapted from
        # https://www.ndss-symposium.org/wp-content/uploads/2019/02/ndss2019_04B-3_Meli_paper.pdf

        # OAuth
        r'\b4/[0-9A-Za-z-_]+\b',  # Auth Code
        r'\b1/[0-9A-Za-z-_]{43}\b|\b1/[0-9A-Za-z-_]{64}\b',  # Refresh Token
        r'\bya29\.[0-9A-Za-z-_]+\b',  # Access Token
        r'\bAIza[0-9A-Za-z-_]{35}\b',  # API Key

        # Private Key
        r'\bPRIVATE KEY( BLOCK)?-----',
    )
    return re.search(re.compile('|'.join(patterns)), text) is not None


def copy_generated_files(source_dir,
                         dest_dir,
                         kzip_input_suffixes=None,
                         ignore=None):
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

  def is_ignored(path):
    parts = os.path.normpath(path).split(os.sep)
    for i in range(len(parts)):
      if os.sep.join(parts[:i + 1]) in ignore:
        return True
    return False

  # First, delete everything in dest that:
  #   * isn't in source or
  #   * is ignored in the source directory or
  #   * doesn't match the allowed extensions or
  #   * may contain secrets or
  #   * (if kzip is provided,) isn't referenced in the kzip
  for dirpath, _, filenames in os.walk(dest_dir):
    for filename in filenames:
      dest_file = os.path.join(dirpath, filename)
      source_file = translate_root(dest_dir, source_dir, dest_file)

      delete = False
      if not os.path.exists(source_file):
        reason = 'source_file %s does not exist.' % source_file
        delete = True
      elif ignore and is_ignored(source_file):
        reason = 'source_file %s is ignored.' % source_file
        delete = True
      elif not has_allowed_extension(source_file):
        reason = \
            'source_file %s does not have an allowed extension.' % source_file
        delete = True
      elif has_secrets(dest_file):
        reason = 'dest_file %s may contain secrets.' % dest_file
        delete = True
      elif kzip_input_suffixes and not is_referenced(dest_file):
        reason = 'dest_file %s not referenced by kzip.' % dest_file
        delete = True

      if delete:
        print('Deleting dest_file %s: %s' % (dest_file, reason))
        os.remove(dest_file)

  # Second, copy everything that matches the allowlist from source to dest. If
  # kzip is provided, don't copy files that aren't referenced. Don't sync
  # ignored paths.
  for dirpath, _, filenames in os.walk(source_dir):
    if dirpath != source_dir:
      try:
        os.mkdir(translate_root(source_dir, dest_dir, dirpath))
      except OSError as e:
        if e.errno != errno.EEXIST:
          raise

    # Don't sync any temporary files. These aren't actually referenced.
    if 'tmp' in dirpath.split(os.sep):
      continue

    for filename in filenames:
      source_file = os.path.join(dirpath, filename)

      # arm-generic builder runs into an issue where source_file disappears by
      # the time it's copied. Check source_file so the builder doesn't fail.
      if not os.path.exists(source_file):
        print('File does not exist:', source_file)
        continue

      if not has_allowed_extension(filename) or has_secrets(source_file) \
          or ignore and is_ignored(source_file) \
          or kzip_input_suffixes and not is_referenced(filename):
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
      '--nokeycheck',
      action='store_true',
      help=('if set, skips keycheck on git push.'))
  parser.add_argument(
      '--dry-run',
      action='store_true',
      help='if set, does a dry run of push to remote repo.')
  parser.add_argument(
      '--ignore', action='append', help='source paths to ignore when copying')
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

  ignore_paths = None
  if opts.ignore:
    ignore_paths = set([os.path.normpath(i) for i in opts.ignore])

  for c in opts.copy:
    source, dest = c.split(';')
    copy_generated_files(source, os.path.join(opts.dest_repo, dest),
                         kzip_input_suffixes, ignore_paths)

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

  cmd = ['git', 'push']
  if opts.nokeycheck:
    cmd.extend(['-o', 'nokeycheck'])
  if opts.dry_run:
    cmd.append('--dry-run')
  cmd.extend(['origin', 'HEAD:%s' % opts.dest_branch])
  check_call(cmd, cwd=opts.dest_repo)


def check_call(cmd, cwd=None):
  if cwd is None:
    print('Running %s' % cmd)
  else:
    print('Running %s in %s' % (cmd, cwd))
  return subprocess.check_call(cmd, cwd=cwd)


if '__main__' == __name__:
  sys.exit(main())
