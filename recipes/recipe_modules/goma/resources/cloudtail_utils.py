#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys

from recipes import cloudtail_utils
from recipes import goma_utils


def start_cloudtail(args):
  args.cloudtail_project_id = 'goma-logs'
  args.cloudtail_log_id = 'goma_compiler_proxy'
  args.cloudtail_log_path = goma_utils.GetLatestGomaCompilerProxyInfo()
  return cloudtail_utils.start_cloudtail(args)


def main():
  parser = argparse.ArgumentParser(
      description='cloudtail utility for goma recipe module.')

  subparsers = parser.add_subparsers(help='commands for cloudtail')

  parser_start = subparsers.add_parser(
      'start', help='subcommand to start cloudtail')
  parser_start.set_defaults(command='start')
  parser_start.add_argument(
      '--cloudtail-path', required=True, help='path of cloudtail binary')
  parser_start.add_argument(
      '--cloudtail-service-account-json',
      help='path of cloudtail service account json file')

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
