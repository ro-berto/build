# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions for discovering the build directory."""

import os
import sys


def AreNinjaFilesNewerThanXcodeFiles(src_dir=None):
  """Returns True if the generated ninja files are newer than the generated
  xcode files.
  
  Parameters:
    src_dir: The path to the src directory.  If None, it's assumed to be
             at src/ relative to the current working directory.
  """
  xcode_stat = 0
  ninja_stat = 0

  src_dir = src_dir or 'src'

  ninja_path = os.path.join(src_dir, 'out', 'Release', 'build.ninja')
  try:
    ninja_stat = os.path.getmtime(ninja_path)
  except os.error:
    pass

  xcode_path = os.path.join(
      src_dir, 'build', 'all.xcodeproj', 'project.pbxproj')
  try:
    xcode_stat = os.path.getmtime(xcode_path)
  except os.error:
    pass

  return ninja_stat > xcode_stat


def ConvertBuildDirToLegacy(build_dir, use_out=False):
  """Returns a tuple of (build_dir<str>, legacy<bool>).
  """
  # TODO(thakis): Make this the canonical source of truth for build_dir for
  # slave scripts, remove all parameters.
  legacy_paths = {
    'darwin': 'xcodebuild',
    'linux': 'sconsbuild',
  }
  bad = False

  platform_key = None
  for key in legacy_paths:
    if sys.platform.startswith(key):
      platform_key = key
      break

  if (build_dir == 'src/build' and platform_key):
    print >> sys.stderr, (
        'WARNING: Passed "%s" as --build-dir option on %s. '
        'This is almost certainly incorrect.' % (build_dir, platform_key))
    if use_out:
      legacy_path = 'out'
    else:
      legacy_path = legacy_paths[platform_key]
    build_dir = os.path.join(os.path.dirname(build_dir), legacy_path)
    print >> sys.stderr, ('Assuming you meant "%s"' % build_dir)
    bad = True

  return (build_dir, bad)
