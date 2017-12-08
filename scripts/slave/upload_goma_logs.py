#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""upload goma related logs."""

import argparse
import json
import os
import sys

from slave import goma_utils


def main():
  parser = argparse.ArgumentParser(description='Upload goma related logs')
  parser.add_argument('--upload-compiler-proxy-info',
                      action='store_true',
                      help='If set, the script will upload the latest '
                      'compiler_proxy.INFO.')
  parser.add_argument('--log-url-json-file',
                      help='If set, the script will write url of uploaded '
                      'log visualizer.')
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
  parser.add_argument('--goma-stats-file',
                      metavar='FILENAME',
                      help='Filename of a GomaStats binary protobuf. '
                      'If empty or non-existing file, it will report error '
                      'to chrome infra monitoring system.')
  parser.add_argument('--goma-crash-report-id-file',
                      metavar='FILENAME',
                      help='Filename that has a crash report id.')
  parser.add_argument('--build-data-dir',
                      metavar='DIR',
                      help='Directory that has build data used by event_mon.')

  parser.add_argument('--json-status',
                      metavar='JSON',
                      help='path of json file generated from'
                      ' ./goma_ctl.py jsonstatus')
  parser.add_argument('--skip-sendgomatsmon', action='store_true',
                      help='Represent whether send jsonstatus'
                      ' and goma or compile.py exit_status log to TsMon.'
                      ' This option is used when no need to send goma status'
                      ' to monitoring server.')

  parser.add_argument('--gsutil-py-path',
                      help='Specify path to gsutil.py script in depot_tools.')

  # Arguments set to os.environ
  parser.add_argument('--buildbot-buildername',
                      default='unknown',
                      help='buildbot buildername')
  parser.add_argument('--buildbot-mastername',
                      default='unknown',
                      help='buildbot mastername')
  parser.add_argument('--buildbot-slavename',
                      default='unknown',
                      help='buildbot slavename')
  parser.add_argument('--buildbot-clobber', default='',
                      help='buildbot clobber')

  args = parser.parse_args()
  tsmon_counters = []

  override_gsutil = None
  if args.gsutil_py_path:
    # Needs to add '--', otherwise gsutil options will be passed to gsutil.py.
    override_gsutil = [sys.executable, args.gsutil_py_path, '--']

  viewer_urls = {}

  if args.upload_compiler_proxy_info:
    viewer_url = goma_utils.UploadGomaCompilerProxyInfo(
        builder=args.buildbot_buildername,
        master=args.buildbot_mastername,
        slave=args.buildbot_slavename,
        clobber=args.buildbot_clobber,
        override_gsutil=override_gsutil
    )
    if viewer_url is not None:
      viewer_urls['compiler_proxy_log'] = viewer_url

  if args.ninja_log_outdir:
    viewer_url = goma_utils.UploadNinjaLog(
        args.ninja_log_outdir,
        args.ninja_log_compiler,
        args.ninja_log_command,
        args.ninja_log_exit_status,
        override_gsutil=override_gsutil
    )
    if viewer_url is not None:
      viewer_urls['ninja_log'] = viewer_url

  if args.log_url_json_file:
    with open(args.log_url_json_file, 'w') as f:
      f.write(json.dumps(viewer_urls))

  if args.goma_stats_file:
    # MakeGomaExitStatusCounter should be callbed before
    # goma_utils.SendGomaStats, since SendGomaStats removes stats file.
    counter = goma_utils.MakeGomaExitStatusCounter(
        args.goma_stats_file,
        args.build_data_dir,
        builder=args.buildbot_buildername,
        master=args.buildbot_mastername,
        slave=args.buildbot_slavename,
        clobber=args.buildbot_clobber)
    if counter:
      tsmon_counters.append(counter)
    goma_utils.SendGomaStats(args.goma_stats_file,
                             args.goma_crash_report_id_file,
                             args.build_data_dir)

  if not args.skip_sendgomatsmon:
    # In the case of goma_start is failed,
    # we want log to investigate failed reason.
    # So, let me send some logs instead of
    # error in parse_args() using required option.
    assert args.json_status is not None and os.path.exists(args.json_status)
    counter = goma_utils.MakeGomaStatusCounter(
        args.json_status,
        args.ninja_log_exit_status,
        builder=args.buildbot_buildername,
        master=args.buildbot_mastername,
        slave=args.buildbot_slavename,
        clobber=args.buildbot_clobber)
    if counter:
      tsmon_counters.append(counter)

  if tsmon_counters:
    goma_utils.SendCountersToTsMon(tsmon_counters)

  return 0


if '__main__' == __name__:
  sys.exit(main())
