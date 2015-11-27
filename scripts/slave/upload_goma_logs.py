#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""upload goma related logs."""

import argparse
import sys

from slave import goma_utils


def main():
  parser = argparse.ArgumentParser(description='Upload goma related logs')
  parser.add_argument('--upload-compiler-proxy-info',
                      action='store_true',
                      help='If set, the script will upload the latest '
                      'compiler_proxy.INFO.')
  parser.add_argument('--ninja-log-outdir',
                      metavar='DIR',
                      help='Directory that has .ninja_log file.')
  parser.add_argument('--ninja-log-compiler',
                      metavar='COMPILER',
                      help='compiler name used for the build.')
  parser.add_argument('--ninja-log-command',
                      metavar='COMMAND',
                      help='command line options of the build.')
  parser.add_argument('--ninja-log-exit-status',
                      type=int,
                      metavar='EXIT_STATUS',
                      help='ninja exit status.')
  args = parser.parse_args()

  if args.upload_compiler_proxy_info:
    goma_utils.UploadGomaCompilerProxyInfo()
  if args.ninja_log_outdir:
    goma_utils.UploadNinjaLog(args.ninja_log_outdir,
                              args.ninja_log_compiler,
                              args.ninja_log_command,
                              args.ninja_log_exit_status)
  return 0


if '__main__' == __name__:
  sys.exit(main())
