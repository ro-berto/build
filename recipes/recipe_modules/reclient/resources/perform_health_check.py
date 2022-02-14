#!/usr/bin/env python3
# Copyright (c) 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys

from os import path


def check_for_reclient_fatals(log_dir):
  """Performs reclient health check by determining
  whether any FATAL log entries were produced
  during compilation

  Raises:
    Exception if FATAL log file is found in the log_dir
  """
  for tool_name in ['bootstrap', 'reproxy', 'rewrapper']:
    if path.exists(path.join(log_dir, tool_name + '.FATAL')):
      raise Exception("Found {} FATAL log entries".format(tool_name))

  print("no reclient's FATAL log entries found in %s" % log_dir)


def main():
  parser = argparse.ArgumentParser(description='Performs reclient health check')

  parser.add_argument(
      '--reclient-log-dir',
      required=True,
      help='Path to the reclient log directory')

  args = parser.parse_args()
  log_dir = args.reclient_log_dir

  try:
    check_for_reclient_fatals(log_dir)
  except Exception as err:
    print("There was a FATAL error during reclient execution: {}".format(err))
    return 1
  return 0


sys.exit(main())
