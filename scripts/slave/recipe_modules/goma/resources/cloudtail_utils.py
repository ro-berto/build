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
    raise e
  return True


class NotDiedError(Exception):
  def __str__(self):
    return "NotDiedError"


def wait_termination(pid):
  """Send SIGINT to pid and wait termination of pid.

  Args:
    pid(int): pid of process which this function waits termination.

  Raises:
    OSError: is_running_posix, os.waitpid and os.kill may throw OSError.
    NotDiedError: if cloudtail is running after 10 seconds waiting,
                  NotDiedError is raised.
  """
  try:
    os.kill(pid, signal.SIGINT)
  except OSError as e:
    # Already dead?
    if e.errno in (errno.ECHILD, errno.EPERM, errno.ESRCH):
      return
    raise

  print('SIGINT has been sent to process %d. '
        'Going to wait for the process finishes.' % pid)
  if os.name == 'nt':
    try:
      os.waitpid(pid, 0)
    except OSError as e:
      if e.errno == errno.ECHILD:
        print('process %d died before waitpitd' % pid)
        return
      raise e
  else:
    for _ in xrange(10):
      time.sleep(1)
      if not is_running_posix(pid):
        return

    print('process %d running more than 10 seconds' % pid)
    raise NotDiedError()


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
      pid = int(f.read())
    try:
      wait_termination(pid)
    except (OSError, NotDiedError) as e:
      print('Going to send SIGTERM to process %d due to Error %s' % (pid, e))
      # Since Windows does not have SIGKILL, we need to use SIGTERM.
      try:
        os.kill(pid, signal.SIGTERM)
      except OSError as e:
        print('Failed to send SIGTERM to process %d: %s' % (pid, e))
      # We do not reraise because I believe not suspending the process
      # is more important than completely killing cloudtail.


if '__main__' == __name__:
  sys.exit(main())
