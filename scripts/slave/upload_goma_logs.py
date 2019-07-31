#!/usr/bin/env vpython
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""upload goma related logs."""

from __future__ import print_function

import argparse
import collections
import json
import os
import sys

from infra_libs import luci_auth
from slave import goma_utils

GOMA_LOGS_PROJECT = 'goma-logs'


def GetBigQueryClient(service_account_json):
  """Returns bigquery client for goma logs.

  Args:
    service_account_json: a JSON file for BigQuery service account.
  """
  if service_account_json:
    # TODO(yyanagisawa): remove following debug print.
    #                    (crbug.com/822042)

    for env in ('PYTHONPATH', 'VPYTHON_CLEAR_PYTHONPATH'):
      print('%s=%s' % (env, os.environ.get(env, '<not set>')),
            file=sys.stderr)
    print('sys.path=%s' % sys.path, file=sys.stderr)

    # TODO(yyanagisawa): move this back to the top line when flakiness solved
    #                    (crbug.com/822042)
    try:
      from google.cloud import bigquery
      from google.oauth2 import service_account
    except ImportError as e:
      print(e, file=sys.stderr)
      for p in sys.path:
        print('path=%s' % p, file=sys.stderr)
        for root, dirs, files in os.walk(p):
          print(' root=%s, dirs=%s, files=%s' % (root, dirs, files),
                file=sys.stderr)
        print()
      raise

    creds = service_account.Credentials.from_service_account_file(
        service_account_json)
  elif luci_auth.available():
    creds = luci_auth.LUCICredentials()
  else:
    return None
  return bigquery.client.Client(project=GOMA_LOGS_PROJECT, credentials=creds)


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
  # TODO(shinyak): Remove this when everyone is using --ninja-log-command-file.
  parser.add_argument('--ninja-log-command',
                      metavar='COMMAND',
                      help='command line options of the build.')
  parser.add_argument('--ninja-log-command-file',
                      metavar='FILE',
                      help='command line options of the build, which is '
                      'written in the file. this option is preferred to '
                      '--ninja-log-command.')
  parser.add_argument('--build-exit-status',
                      type=int,
                      metavar='EXIT_STATUS',
                      help='build command exit status.')
  parser.add_argument('--goma-stats-file',
                      metavar='FILENAME',
                      help='Filename of a GomaStats binary protobuf. '
                      'If empty or non-existing file, it will report error '
                      'to chrome infra monitoring system.')
  parser.add_argument('--goma-counterz-file',
                      help='Filename of a CounterzStats binary protobuf. '
                      'If empty or non-existing file, it will report error '
                      'to chrome infra monitoring system.')
  parser.add_argument('--goma-crash-report-id-file',
                      metavar='FILENAME',
                      help='Filename that has a crash report id.')

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

  # For CompileEvents.
  parser.add_argument('--build-id', default=0, type=long,
                      help='unique ID of the current build')
  parser.add_argument('--build-step-name', default='',
                      help='step name of the current build')
  parser.add_argument('--bigquery-service-account-json', default='',
                      metavar='FILENAME',
                      help='Service account json for BigQuery')
  parser.add_argument('--bigquery-upload', action='store_true',
                      help='upload to BigQuery')

  # Builder ID.
  parser.add_argument('--builder-id-json', default='',
                      metavar='FILENAME',
                      help='path to Builder ID json file')

  # From Runtime API.
  parser.add_argument('--is-luci',
                      action='store_true',
                      help='True if this runs on LUCI')
  parser.add_argument('--is-experimental',
                      action='store_true',
                      help='True if experimental')

  args = parser.parse_args()
  tsmon_counters = []

  override_gsutil = None
  if args.gsutil_py_path:
    # Needs to add '--', otherwise gsutil options will be passed to gsutil.py.
    override_gsutil = ['python', args.gsutil_py_path, '--']

  viewer_urls = {}

  builder_id = {}
  if args.builder_id_json:
    with open(args.builder_id_json) as f:
      builder_id = json.load(f)

  if args.upload_compiler_proxy_info:
    viewer_url = goma_utils.UploadGomaCompilerProxyInfo(
        builder=args.buildbot_buildername,
        master=args.buildbot_mastername,
        slave=args.buildbot_slavename,
        builder_id=builder_id,
        is_luci=args.is_luci,
        is_experimental=args.is_experimental,
        override_gsutil=override_gsutil
    )
    if viewer_url is not None:
      viewer_urls['compiler_proxy_log'] = viewer_url

  if args.ninja_log_command_file:
    # TODO(shinyak): Assuming file exists.
    with open(args.ninja_log_command_file, 'r') as f:
      ninja_log_command = f.read()
  else:
    ninja_log_command = args.ninja_log_command

  if args.ninja_log_outdir:
    viewer_url = goma_utils.UploadNinjaLog(
        outdir=args.ninja_log_outdir,
        compiler=args.ninja_log_compiler,
        command=ninja_log_command,
        exit_status=args.build_exit_status,
        build_id=args.build_id,
        step_name=args.build_step_name,
        override_gsutil=override_gsutil
    )
    if viewer_url is not None:
      viewer_urls['ninja_log'] = viewer_url

  if args.log_url_json_file:
    with open(args.log_url_json_file, 'w') as f:
      f.write(json.dumps(viewer_urls))

  bqclient = None
  # TODO(yyanagisawa): remove move this when flakiness is solved
  #                    (crbug.com/822042)
  # Without Build ID, we do not use BigQuery.  Let me minimize the
  # points that cause crbug.com/822042.
  if args.build_id and args.bigquery_upload:
    bqclient = GetBigQueryClient(args.bigquery_service_account_json)
    if not bqclient:
      raise Exception('Unable to create BigQuery client.')

  if args.goma_stats_file and args.build_id and bqclient:
    # TODO(yyanagisawa): move this back to the top line when flakiness is solved
    #                    (crbug.com/822042)
    from slave import goma_bq_utils
    goma_bq_utils.SendCompileEvent(args.goma_stats_file,
                                   args.goma_counterz_file,
                                   args.json_status,
                                   args.build_exit_status,
                                   args.goma_crash_report_id_file,
                                   args.build_id,
                                   args.build_step_name,
                                   bqclient)

  if args.goma_stats_file:
    counter = goma_utils.MakeGomaExitStatusCounter(
        args.goma_stats_file,
        goma_crash_report=args.goma_crash_report_id_file,
        builder=args.buildbot_buildername,
        master=args.buildbot_mastername,
        slave=args.buildbot_slavename,
        builder_id=builder_id,
        is_luci=args.is_luci)
    if counter:
      tsmon_counters.append(counter)

  if not args.skip_sendgomatsmon:
    # In the case of goma_start is failed,
    # we want log to investigate failed reason.
    # So, let me send some logs instead of
    # error in parse_args() using required option.
    assert args.json_status is not None and os.path.exists(args.json_status)
    counter = goma_utils.MakeGomaStatusCounter(
        args.json_status,
        args.build_exit_status,
        builder=args.buildbot_buildername,
        master=args.buildbot_mastername,
        slave=args.buildbot_slavename,
        builder_id=builder_id,
        is_luci=args.is_luci)
    if counter:
      tsmon_counters.append(counter)

    counter = goma_utils.MakeGomaFailureReasonCounter(
        args.json_status,
        args.build_exit_status,
        builder=args.buildbot_buildername,
        master=args.buildbot_mastername,
        slave=args.buildbot_slavename,
        builder_id=builder_id,
        is_luci=args.is_luci)
    if counter:
      tsmon_counters.append(counter)

  if tsmon_counters:
    goma_utils.SendCountersToTsMon(tsmon_counters)

  return 0


if '__main__' == __name__:
  sys.exit(main())
