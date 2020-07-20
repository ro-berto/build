#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Clean up acculumated cruft, including tmp directory."""

import collections
import contextlib
import ctypes
import getpass
import glob
import logging
import os
import socket
import sys
import tempfile
import urllib

from common import chromium_utils
from slave import slave_utils


class FullDriveException(Exception):
  """A disk is almost full."""

  def __init__(self, path, free_space):
    super(FullDriveException, self).__init__()
    self.path = path
    self.free_space = free_space


class UnknownPlatform(Exception):
  """Don't know how to cleanup current platform."""
  pass


Options = collections.namedtuple('Options', ('preserve_tempdir',))


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
        str(e)
    )


def cleanup_directory(directory_to_clean):
  """Cleans up a directory.

  This is a best effort attempt to clean up, since some files will be held
  open for some reason.

  Args:
    directory_to_clean: directory to clean, the directory itself is not deleted.
  """
  try:
    chromium_utils.RemoveDirectory(directory_to_clean)
  except OSError as e:
    print 'Exception removing %s: %s' % (directory_to_clean, e)


@contextlib.contextmanager
def function_logger(header):
  print '%s...' % header.capitalize()
  try:
    yield
  finally:
    print 'Done %s!' % header


def remove_old_isolate_directories(slave_path):
  """Removes all the old isolate directories."""
  with function_logger('removing any old isolate directories'):
    for path in glob.iglob(os.path.join(slave_path, '*', 'build', 'isolate*')):
      print 'Removing %s' % path
      cleanup_directory(path)


def remove_old_isolate_execution_directories_impl_(directory):
  """Removes all the old directories from past isolate executions."""
  for path in glob.iglob(os.path.join(directory, 'run_tha_test*')):
    print 'Removing %s' % path
    cleanup_directory(path)


def remove_old_isolate_execution_directories(slave_path):
  """Removes all the old directories from past isolate executions."""
  with function_logger('removing any old isolate execution directories'):
    remove_old_isolate_execution_directories_impl_(tempfile.gettempdir())
    remove_old_isolate_execution_directories_impl_(slave_path)


def remove_build_dead(slave_path):
  """Removes all the build.dead directories."""
  with function_logger('removing any build.dead directories'):
    for path in glob.iglob(os.path.join(slave_path, '*', 'build.dead')):
      print 'Removing %s' % path
      cleanup_directory(path)


def remove_temp():
  """Removes all the temp files on Windows."""
  with function_logger('removing TEMP'):
    root = os.environ['TEMP']
    if os.path.isdir(root):
      for path in os.listdir(root):
        if path.startswith('goma'):
          # Work around http://crbug.com/449511
          continue
        try:
          chromium_utils.RemovePath(os.path.join(root, path))
        except OSError:
          pass
    else:
      print 'TEMP directory missing: %s' % root


def get_free_space(path):
  """Returns the number of free bytes."""
  if sys.platform == 'win32':
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes)
    )
    return free_bytes.value
  f = os.statvfs(path)
  return f.f_bfree * f.f_frsize


def check_free_space_path(path, min_free_space=1024 * 1024 * 1024):
  """Returns 1 if there isn't enough free space on |path|.

  Defaults to 1gb.
  """
  free_space = get_free_space(path)
  if free_space < min_free_space:
    send_alert(path, free_space)
    raise FullDriveException(path, free_space)


def _CleanupWindows(b_dir=None):
  """Main function for Windows platform."""
  with function_logger('removing any Chrome temporary files'):
    slave_utils.RemoveChromeTemporaryFiles()
  if not b_dir:
    if os.path.isdir('e:\\'):
      b_dir = 'e:\\b'
    else:
      b_dir = 'c:\\b'
  slave_path = os.path.join(b_dir, 'build', 'slave')

  remove_build_dead(slave_path)
  remove_old_isolate_directories(slave_path)
  remove_old_isolate_execution_directories(slave_path)
  remove_temp()
  check_free_space_path('c:\\')
  if os.path.isdir('e:\\'):
    check_free_space_path('e:\\')
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  # Do not add the following cleanup in slaves_utils.py since we don't want to
  # clean them between each test, as the crash dumps may be processed by
  # 'process build' step.
  with function_logger('removing any crash reports'):
    if 'LOCALAPPDATA' in os.environ:
      crash_reports = os.path.join(
          os.environ['LOCALAPPDATA'], 'Chromium', 'User Data', 'Crash Reports'
      )
      if os.path.isdir(crash_reports):
        for filename in os.listdir(crash_reports):
          filepath = os.path.join(crash_reports, filename)
          if os.path.isfile(filepath):
            os.remove(filepath)


def _CleanupMac(b_dir=None):
  """Main function for Mac platform."""
  with function_logger('removing any Chrome temporary files'):
    slave_utils.RemoveChromeTemporaryFiles()
  if not b_dir:
    b_dir = '/b'
  slave_path = os.path.join(b_dir, 'build', 'slave')

  remove_build_dead(slave_path)
  remove_old_isolate_directories(slave_path)
  remove_old_isolate_execution_directories(slave_path)
  # On the Mac, clearing out the entire tmp folder could be problematic,
  # as it might remove files in use by apps not related to the build.
  if os.path.isdir(b_dir):
    check_free_space_path(b_dir)
  check_free_space_path(os.environ['HOME'])
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))


def _CleanupLinux(b_dir=None):
  """Main function for linux platform."""
  with function_logger('removing any Chrome temporary files'):
    slave_utils.RemoveChromeTemporaryFiles()
  if not b_dir:
    b_dir = '/b'
  slave_path = os.path.join(b_dir, 'build', 'slave')

  remove_build_dead(slave_path)
  remove_old_isolate_directories(slave_path)
  remove_old_isolate_execution_directories(slave_path)
  # TODO(maruel): Temporary, add back.
  # cleanup_directory('/tmp')
  if os.path.isdir(b_dir):
    check_free_space_path(b_dir)
  check_free_space_path(os.environ['HOME'])
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))


def Cleanup(b_dir=None):
  """Performs the cleanup operation for the current platform.

  Raises:
    UnknownPlatform: If the current platform is unknown.
    FullDriveException: If one of the target drives was too full to operate.
  """
  if os.environ.get('SWARMING_HEADLESS'):
    # On Swarming, this script is run from a temporary directory. Eh.
    print('Skipping temp cleanup when run from Swarming.')
    return

  if chromium_utils.IsWindows():
    _CleanupWindows(b_dir=b_dir)
  elif chromium_utils.IsMac():
    _CleanupMac(b_dir=b_dir)
  elif chromium_utils.IsLinux():
    _CleanupLinux(b_dir=b_dir)
  else:
    raise UnknownPlatform('Unknown platform: %s' % (sys.platform,))


def main():
  """Main application entry point."""
  # When running as an application, do not presume full ownership of the
  # temporary directory.
  try:
    Cleanup()
  except FullDriveException, e:
    print >> sys.stderr, 'Not enough free space on %s: %d bytes left' % (
        e.path, e.free_space
    )


if '__main__' == __name__:
  sys.exit(main())
