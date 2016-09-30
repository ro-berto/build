#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import errno
import os
import signal
import subprocess
import sys

from slave import goma_utils


def start_cloudtail(args):
  """Write process id of started cloudtail to file object f"""

  proc = subprocess.Popen([args.cloudtail_path,
                           'tail',
                           '--log-id', 'goma_compiler_proxy',
                           '--path',
                           goma_utils.GetLatestGomaCompilerProxyInfo()])
  with open(args.pid_file, 'w') as f:
    f.write(str(proc.pid))

def main():
  parser = argparse.ArgumentParser(
      description='cloudtail utility for goma recipe module.')

  subparsers = parser.add_subparsers(help='commands for cloudtail')

  parser_start = subparsers.add_parser('start',
                                       help='subcommand to start cloudtail')
  parser_start.set_defaults(command='start')
  parser_start.add_argument('--cloudtail-path', required=True,
                            help='path of cloudtail binary')
  parser_start.add_argument('--pid-file', required=True,
                            help='file written pid')

  parser_stop = subparsers.add_parser('stop',
                                      help='subcommand to stop cloudtail')
  parser_stop.set_defaults(command='stop')
  parser_stop.add_argument('--killed-pid-file', required=True,
                           help='file written the pid to be killed.')

  args = parser.parse_args()

  if args.command == 'start':
    start_cloudtail(args)
  elif args.command == 'stop':
    with open(args.killed_pid_file) as f:
      # cloudtail flushes log and terminates
      # within 5 seconds when it recieves SIGINT.
      os.kill(int(f.read()), signal.SIGINT)

if '__main__' == __name__:
  sys.exit(main())
