#!/usr/bin/env python3
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys

from recipes import cloudtail_utils


def start_cloudtail(args):
  args.cloudtail_log_id = 'chromium_reclient'
  args.cloudtail_service_account_json = None
  return cloudtail_utils.start_cloudtail(args)


def main():
  parser = argparse.ArgumentParser(
      description='cloudtail utility for the reclient recipe module.')

  subparsers = parser.add_subparsers(help='commands for cloudtail')

  parser_start = subparsers.add_parser(
      'start', help='subcommand to start cloudtail')
  parser_start.set_defaults(command='start')
  parser_start.add_argument(
      '--cloudtail-path', required=True, help='path of cloudtail binary')
  parser_start.add_argument(
      '--cloudtail-project-id',
      required=True,
      help='ID of the cloud project to send the logs to')
  parser_start.add_argument(
      '--cloudtail-log-path', required=True, help='path of the log to send')
  parser_start.add_argument(
      '--pid-file', required=True, help='file written pid')

  parser_stop = subparsers.add_parser(
      'stop', help='subcommand to stop cloudtail')
  parser_stop.set_defaults(command='stop')
  parser_stop.add_argument(
      '--killed-pid-file',
      required=True,
      help='file written the pid to be killed.')

  args = parser.parse_args()

  if args.command == 'start':
    start_cloudtail(args)
  elif args.command == 'stop':
    cloudtail_utils.stop_cloudtail(args)


if '__main__' == __name__:
  sys.exit(main())
