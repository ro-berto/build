#!/usr/bin/env python3
# Copyright (c) 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys
import io

from os import path

FAILURE_STATUS = "1"


def _is_win():
  """
  Returns true if the script runs on Windows platform
  """
  return sys.platform.startswith(('win', 'cygwin'))


def check_for_reclient_fatals(log_dir, exe_suffix):
  """Performs reclient health check by determining
  whether any FATAL log entries were produced
  during compilation

  Raises:
    Exception if FATAL log file is found in the log_dir
  """
  for tool_name in ['bootstrap', 'reproxy', 'rewrapper']:
    if path.exists(path.join(log_dir, tool_name + exe_suffix + '.FATAL')):
      raise Exception("Found {} FATAL log entries".format(tool_name))

  print("no reclient's FATAL log entries found in %s" % log_dir)


def check_for_ip_timeouts(log_dir, exe_suffix, build_exit_status):
  if build_exit_status != FAILURE_STATUS:
    print("build_exit_status({}) != {}, skipping IP timeouts check".format(
        build_exit_status, FAILURE_STATUS))
    return

  full_path = path.join(log_dir, 'reproxy' + exe_suffix + '.ERROR')
  if not path.exists(full_path):
    print("no reproxy errors found")
    return

  with io.open(full_path, mode='r', encoding='utf-8', errors='replace') as f:
    for l in [l.strip() for l in f.readlines()]:
      #TODO(b/233275188) replace with logic verifying LocalMetadata Stats once new entries are added
      if 'this build has encountered too many action input processing timeouts' in l:
        raise Exception("The build failed early due to IP timeouts")


def main():
  parser = argparse.ArgumentParser(description='Performs reclient health check')

  parser.add_argument(
      '--reclient-log-dir',
      required=True,
      help='Path to the reclient log directory')

  parser.add_argument(
      '--build-exit-status', required=True, help='Exit status of the build')

  args = parser.parse_args()
  log_dir = args.reclient_log_dir
  exe_suffix = '.exe' if _is_win() else ''

  try:
    check_for_reclient_fatals(log_dir, exe_suffix)
  except Exception as err:
    print("There was a FATAL error during reclient execution: {}".format(err))
    return 1

  try:
    check_for_ip_timeouts(log_dir, exe_suffix, args.build_exit_status)
  except Exception as err:
    print(err)
    return 1

  return 0


sys.exit(main())
