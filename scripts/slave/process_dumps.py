#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to collect crash signatures for builds.
"""

import optparse
import os
import sys

from common import chromium_utils
from slave import build_directory

# Deprecated magic return code that buildbot used to interpret as "warnings"
# instead of "error". Kept for backwards compatibility purposes, but essentially
# useless.
RETCODE_WARNINGS = 88


# Environment variables that could point to the location of Program Files.
PROGRAM_FILES_ENV_VARS = [
    'PROGRAMFILES',
    'PROGRAMFILES(X86)',
    'PROGRAMW6432',
]


# Places relative to Program Files that the debugger could be located.
DEBUGGER_DIRS = [
    'Debugging Tools For Windows',
    'Debugging Tools For Windows (x86)',
    'Debugging Tools For Windows (x64)',
    'Windows Kits\\8.0\\Debuggers\\x86',
    'Windows Kits\\8.1\\Debuggers\\x64',
    'Windows Kits\\10\\Debuggers\\x64',
]


def GetCrashDumpDir():
  """Returns the default crash dump directory used by chromium. """
  local_app_data = os.environ.get('LOCALAPPDATA')
  if not local_app_data:
    user_profile = os.environ.get('USERPROFILE')
    if not user_profile:
      sys.exit(0)
    local_app_data = '%s\\Local Settings\\Application Data' % user_profile
  return '%s\\Chromium\\User Data\\Crash Reports' % local_app_data


def CdbExistsAtLocation(candidate_dir):
  return (os.path.exists(candidate_dir) and
          os.path.isfile(os.path.join(candidate_dir, "cdb.exe")))


def ProbeDebuggerDir():
  """Probes the debugger installed path and returns the path."""
  for env_var in PROGRAM_FILES_ENV_VARS:
    program_files = os.environ.get(env_var)
    if program_files:
      for debugger_dir in DEBUGGER_DIRS:
        debugger_dir = os.path.join(program_files, debugger_dir)
        if CdbExistsAtLocation(debugger_dir):
          return debugger_dir
  return None


def GetStackTrace(debugger_dir, symbol_path, dump_file):
  """Gets and prints the stack trace from a crash dump file.

  Args:
    debugger_dir: the directory where the debugger is installed.
    symbol_path: symbol path for debugger.
    dump_file: the path to dump file.
  Returns:
    A string representing the stack trace.
  """
  # Run debugger to analyze crash dump.
  cmd = '%s\\cdb.exe -y "%s" -c ".ecxr;k30;q" -z "%s"' % (debugger_dir,
                                                          symbol_path,
                                                          dump_file)
  try:
    output = chromium_utils.GetCommandOutput(cmd)
  except chromium_utils.ExternalError:
    return 'Cannot get stack trace.'

  # Retrieve stack trace from debugger output.
  stack_start = output.find('ChildEBP')
  stack_end = output.find('quit:')
  return output[stack_start:stack_end]


def main():
  parser = optparse.OptionParser()
  parser.add_option('--dump-dir', type='string', default='',
                    help='The directory where dump files are stored.')
  parser.add_option('--debugger-dir', type='string', default='',
                    help='The directory where the debugger is installed.'
                         'The debugger is used to get stack trace from dumps.')
  parser.add_option('--build-dir', help='ignored')
  parser.add_option('--target', default='Release',
                    help='build target (Debug or Release)')
  parser.add_option('--archive-dir', type='string', default='',
                    help='If specified, save dump files to the archive'
                         'directory.')

  options, args = parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  if args:
    parser.error('Unknown args "%s"' % ' '.join(args))
    return 1
  debugger_dir = options.debugger_dir
  if not os.path.exists(debugger_dir):
    debugger_dir = ProbeDebuggerDir()
  if not debugger_dir:
    print 'Cannot find debugger.'
    return RETCODE_WARNINGS

  print 'Debugger directory: %s' % debugger_dir

  symbol_path = os.path.join(options.build_dir, options.target)
  dll_path = os.path.join(symbol_path, 'chrome.dll')

  if not os.path.exists(dll_path):
    print 'Cannot find chrome.dll.'
    return 0
  dll_time = os.path.getmtime(dll_path)

  dump_dir = options.dump_dir
  if not dump_dir:
    dump_dir = GetCrashDumpDir()

  if not os.path.exists(dump_dir):
    print 'The crash dump directory does not exist'
    return 0

  dump_count = 0
  for dump_basename in os.listdir(dump_dir):
    dump_file = os.path.join(dump_dir, dump_basename)
    file_time = os.path.getmtime(dump_file)
    if file_time < dll_time and os.path.isfile(dump_file):
      # Ignore dumps older than dll file.
      print 'Deleting old dump: %s' % dump_file
      os.remove(dump_file)
    elif dump_basename.endswith('.dmp'):
      print '-------------------------'
      print dump_basename
      stack = GetStackTrace(debugger_dir, symbol_path, dump_file)
      print stack
      dump_count += 1

  print '%s dumps found' % dump_count

  # TODO(huanr): add the functionality of archiving dumps.
  return 0


if '__main__' == __name__:
  sys.exit(main())
