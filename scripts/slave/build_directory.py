# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions for discovering the build directory."""

import os


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

# TODO(thakis): Move ConvertBuildDirToLegacy() into this module.
