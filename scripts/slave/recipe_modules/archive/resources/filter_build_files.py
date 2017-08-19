#!/usr/bin/python
#
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Filter out unneeded files from the given build directory.

Generates json output of the filepaths relative to the given build directory.
"""

import argparse
import json
import os
import re
import sys


# TODO(machenbach): Chromium specific data should move out of the archive
# module, into e.g. the chromium test configs.

# Excluded top level directories located exactly inside the build dir. Example:
# 'obj' will filter out 'out/Release/obj' but not 'out/Release/x64/obj'.
EXCLUDED_TOP_LEVEL_DIRS_ALL_PLATFORMS = [
  'gen',
  'obj',
]

EXCLUDED_TOP_LEVEL_DIRS = {
  'win': set(EXCLUDED_TOP_LEVEL_DIRS_ALL_PLATFORMS + [
    'cfinstaller_archive',
    'installer_archive',
    'lib',
  ]),
  'mac': set(EXCLUDED_TOP_LEVEL_DIRS_ALL_PLATFORMS + [
    '.deps',
    'App Shim Socket',
    # We copy the framework into the app bundle, we don't need the second
    # copy outside the app.
    # TODO(mark): Since r28431, the copy in the build directory is actually
    # used by tests.  Putting two copies in the .zip isn't great, so maybe
    # we can find another workaround.
    # 'Chromium Framework.framework',
    # 'Google Chrome Framework.framework',
    # We copy the Helper into the app bundle, we don't need the second
    # copy outside the app.
    'Chromium Helper.app',
    'Google Chrome Helper.app',
    'lib',
    'mksnapshot.dSYM',
    'v8_shell.dSYM',
  ]),
  'linux': set(EXCLUDED_TOP_LEVEL_DIRS_ALL_PLATFORMS + [
    '.deps',
    'appcache',
    'glue',
    'src',
  ]),
}

# Subdirectories located anywhere inside of build_dir. For example, 'obj' will
# filter out all subdirectories named 'obj' of any depth inside the build dir.
EXCLUDED_SUBDIRS_ALL_PLATFORMS = [
  'gen',
  'obj',
]

EXCLUDED_SUBDIRS = {
  'win': set(EXCLUDED_SUBDIRS_ALL_PLATFORMS + []),
  'mac': set(EXCLUDED_SUBDIRS_ALL_PLATFORMS + []),
  'linux': set(EXCLUDED_SUBDIRS_ALL_PLATFORMS + []),
}

# Basenames of the files to be excluded from the archive.
EXCLUDED_FILES_ALL_PLATFORMS = [
  '.landmines',
  '.ninja_deps',
  '.ninja_log',
  'mksnapshot',
  'v8_shell',
]

# Excluded files on specific platforms.
EXCLUDED_FILES = {
  'win': set(EXCLUDED_FILES_ALL_PLATFORMS + [
    'mksnapshot.exe',
    'mksnapshot.exe.pdb',
    'v8_shell.exe',
    'v8_shell.exe.pdb',
  ]),
  # TODO: figure out which files we can skip on Mac.
  'mac': set(EXCLUDED_FILES_ALL_PLATFORMS + [
    # We don't need the arm bits v8 builds.
    'd8_arm',
    'v8_shell_arm',
    'obj.host',
    'obj.target',
    # pdfsqueeze is a build helper, no need to copy it to testers.
    'pdfsqueeze',
  ]),
  'linux': set(EXCLUDED_FILES_ALL_PLATFORMS + [
    # Scons build cruft.
    '.sconsign.dblite',
    # Intermediate build directories (full of .o, .d, etc.).
    'lib.host',
    'obj.host',
    'obj.target',
  ]),
}

# Pattern for excluded files on specific platforms.
EXCLUDED_FILES_PATTERN = {
  'win': re.compile(r'^.+\.(o|a|d|obj|lib|pch|exp|ninja|stamp)$'),
  'mac': re.compile(r'^.+\.(a|ninja|stamp)$'),
  'linux': re.compile(r'^.+\.(o|a|d|ninja|stamp)$'),
}


def walk_and_filter(dir_path, platform_name):
  result = []

  for root, dirnames, filenames in os.walk(dir_path, followlinks=True):
    relative_root = os.path.relpath(root, dir_path)

    # Clear relative_root to avoid top-level paths looking like './path'.
    if relative_root == '.':
      relative_root = ''

    for d in list(dirnames):
      # Filter out unneeded directories.
      if (not relative_root and d in EXCLUDED_TOP_LEVEL_DIRS[platform_name] or
          d in EXCLUDED_SUBDIRS[platform_name]):
        dirnames.remove(d)
        continue

      # We want to archive symlinks pointing to directories (crbug.com/693624).
      # Symlinks pointing to directories should be passed explicitly to `zip`.
      # Otherwise, the build archive for Mac doesn't have a proper structure.
      if os.path.islink(os.path.join(root, d)):
        result.append(os.path.join(relative_root, d))

        # There is no need to walk through symlinks pointing to directories,
        # as every link will be copied prior to creating an archive.
        dirnames.remove(d)

    # Filter out unneeded files.
    for filename in filenames:
      # Filter files by filename pattern.
      if EXCLUDED_FILES_PATTERN[platform_name].match(filename):
        continue

      # Filter certain files.
      if filename in EXCLUDED_FILES[platform_name]:
        continue

      path = os.path.join(relative_root, filename)
      result.append(path)

  return result


def main(argv):
  parser = argparse.ArgumentParser(
      description='Exclude unneeded files from the given build directory.')

  parser.add_argument('-d', '--dir', required=True,
                      help='Path to a build directory.')
  parser.add_argument('-p', '--platform', required=True,
                      help='Platform name: win/mac/linux.')
  parser.add_argument('-o', '--output', required=True,
                      help='Path to an output file.')
  args = parser.parse_args()

  build_dir = args.dir
  if not os.path.exists(build_dir) or not os.path.isdir(build_dir):
    raise Exception('%s is not an existing directory.' % build_dir)

  list_of_files = walk_and_filter(build_dir, args.platform)

  with open(args.output, 'w') as f:
    json.dump(list_of_files, f)

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
