#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Clean up acculumated cruft, including tmp directory."""

import ctypes
import getpass
import logging
import os
import socket
import sys
import urllib

from common import chromium_utils


class FullDriveException(Exception):
  """A disk is almost full."""
  pass


def send_alert(path, left):
  """Sends information about full drive to the breakpad server."""
  url = 'https://chromium-status.appspot.com/breakpad'
  try:
    host = socket.getfqdn()
    params = {
        # args must not be empty.
        'args': '-',
        'stack': 'Only %d bytes left in %s on %s' % (left, path, host),
        'user': getpass.getuser(),
        'exception': 'FullDriveException',
        'host': host,
        'cwd': path,
    }
    request = urllib.urlopen(url, urllib.urlencode(params))
    request.read()
    request.close()
  except IOError, e:
    logging.error(
        'There was a failure while trying to send the stack trace.\n%s' %
            str(e))


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


def check_free_space_path(path, min_free_space=1024*1024*1024):
  """Returns 1 if there isn't enough free space on |path|.

  Defaults to 1gb.
  """
  free_space = get_free_space(path)
  if free_space < min_free_space:
    raise FullDriveException(path, free_space)


def main_win():
  """Main function for Windows platform."""
  chromium_utils.RemoveChromeTemporaryFiles()
  # TODO(maruel): Temporary, add back.
  #CleanupTempDirectory(os.environ['TEMP'])
  check_free_space_path('c:\\')
  if os.path.isdir('e:\\'):
    check_free_space_path('e:\\')
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  return 0


def main_mac():
  """Main function for Mac platform."""
  chromium_utils.RemoveChromeTemporaryFiles()
  # On the Mac, clearing out the entire tmp folder could be problematic,
  # as it might remove files in use by apps not related to the build.
  if os.path.isdir('/b'):
    check_free_space_path('/b')
  check_free_space_path(os.environ['HOME'])
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  return 0


def main_linux():
  """Main function for linux platform."""
  chromium_utils.RemoveChromeTemporaryFiles()
  # TODO(maruel): Temporary, add back.
  # CleanupTempDirectory('/tmp')
  if os.path.isdir('/b'):
    check_free_space_path('/b')
  check_free_space_path(os.environ['HOME'])
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  return 0


def main():
  try:
    if chromium_utils.IsWindows():
      return main_win()
    elif chromium_utils.IsMac():
      return main_mac()
    elif chromium_utils.IsLinux():
      return main_linux()
    else:
      print 'Unknown platform: ' + sys.platform
      return 1
  except FullDriveException, e:
    print >> sys.stderr, 'Not enough free space on %s: %d bytes left' % (
        e.args[0], e.args[1])
    send_alert(e.args[0], e.args[1])


if '__main__' == __name__:
  sys.exit(main())
