#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Clean up acculumated cruft, including tmp directory."""

import ctypes
import os
import sys

from common import chromium_utils


def CleanupTempDirectory(temp_dir):
  """Cleans up the TEMP directory.

  This is a best effort attempt to clean up, since some files will be held
  open for some reason.

  Args:
    temp_dir: A string representing the root of the temporary directory.
  """
  removed_file_count = 0
  for root, dirs, files in os.walk(temp_dir, topdown=False):
    for name in files:
      try:
        os.remove(os.path.join(root, name))
        removed_file_count = removed_file_count + 1
      except OSError:
        pass  # Ignore failures, this is best effort only
    for name in dirs:
      try:
        os.rmdir(os.path.join(root, name))
      except OSError:
        pass  # Ignore failures, this is best effort only
  print 'Removed %d files from %s' % (removed_file_count, temp_dir)


def get_free_space(path):
  """Returns the number of free bytes."""
  if sys.platform == 'win32':
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
    return free_bytes.value
  f = os.statvfs(path)
  return f.f_bfree * f.f_frsize


def check_path(path, min_free_space):
  """Returns 1 if there isn't enough free space on |path|."""
  free_space = get_free_space(path)
  if free_space < min_free_space:
    print >> sys.stderr, 'Not enough free space on %s: %d bytes left' % (
        path, free_space)
    return 1
  return 0


def check_free_space():
  """Returns 1 if there isn't enough free space left on the slave."""
  # 1 gb
  min_free_space = 1024*1024*1024
  if chromium_utils.IsWindows():
    if check_path('c:\\', min_free_space):
      return 1
    if os.path.isdir('e:\\'):
      if check_path('e:\\', min_free_space):
        return 1
  elif chromium_utils.IsMac():
    if os.path.isdir('/b'):
      if check_path('/b', min_free_space):
        return 1
  elif chromium_utils.IsLinux():
    if os.path.isdir('/b'):
      if check_path('/b', min_free_space):
        return 1
    if check_path('/home', min_free_space):
      return 1
  return 0


def main_win():
  """Main function for Windows platform."""
  chromium_utils.RemoveChromeTemporaryFiles()
  # TODO(maruel): Temporary, add back.
  #CleanupTempDirectory(os.environ['TEMP'])
  return check_free_space()


def main_mac():
  """Main function for Mac platform."""
  chromium_utils.RemoveChromeTemporaryFiles()
  # On the Mac, clearing out the entire tmp folder could be problematic,
  # as it might remove files in use by apps not related to the build.
  return check_free_space()


def main_linux():
  """Main function for linux platform."""
  chromium_utils.RemoveChromeTemporaryFiles()
  # TODO(maruel): Temporary, add back.
  # CleanupTempDirectory('/tmp')
  return check_free_space()


def main():
  if chromium_utils.IsWindows():
    return main_win()
  elif chromium_utils.IsMac():
    return main_mac()
  elif chromium_utils.IsLinux():
    return main_linux()
  else:
    print 'Unknown platform: ' + sys.platform
    return 1


if '__main__' == __name__:
  sys.exit(main())
