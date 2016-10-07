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
import time

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

def is_running_posix(pid):
  """Return True if process of pid is running.

  Args:
    pid(int): pid of process which this function checks
              whether it is running or not.

  Returns:
    bool: True if process of pid is running.

  Raises:
    OSError if something happens in os.kill(pid, 0)
  """

  try:
    os.kill(pid, 0)
  except OSError as e:
    if e.errno == errno.ESRCH or e.errno == errno.EPERM:
      return False
    os.kill(pid, signal.SIGKILL)
    print('killed process %d due to OSError %s' % (pid, e))
    raise e
  return True

def wait_termination(pid):
  """Send SIGINT to pid and wait termination of pid.

  Args:
    pid(int): pid of process which this function waits termination.

  Raises:
    OSError: is_running_posix, os.waitpid and os.kill may throw OSError.
  """

  try:
    os.kill(pid, signal.SIGINT)
  except:
    os.kill(pid, signal.SIGKILL)
    raise

  if os.name == 'nt':
    os.waitpid(pid, 0)
  else:
    for _ in xrange(10):
      if not is_running_posix(pid):
        break
      time.sleep(1)

    if is_running_posix(pid):
      os.kill(pid, signal.SIGKILL)
      print('killed process %d running more than 10 seconds' % pid)

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
      wait_termination(int(f.read()))

if '__main__' == __name__:
  sys.exit(main())
