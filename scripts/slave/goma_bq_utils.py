# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions specific to upload goma related info to BigQuery.
"""

import os

from infra_libs import bigquery
from slave.goma import compile_events_pb2
from slave import goma_utils

# The Google BigQuery dataset and table for CompileEvent.
COMPILE_EVENTS_DATASET = 'client_events'
COMPILE_EVENTS_TABLE = 'compile_events'


def SendCompileEvent(goma_stats_file, goma_crash_report, build_id, step_name,
                     bqclient):
  """Insert CompileEvent to BigQuery table.

  Args:
    goma_stats_file: a file that has binary representation of GomaStats.
    goma_crash_report: a file that has compiler_proxy crash report id
                       if it crashed.
    build_id: Build ID string.
    step_name: a name of a compile step.
    bqclient: an instance of BigQuery client.
  """
  event = compile_events_pb2.CompileEvent()
  event.build_id = build_id
  event.step_name = step_name or ''
  event.exit_status = compile_events_pb2.CompileEvent.DIED_WITH_UNKOWN_REASON
  try:
    if goma_stats_file and os.path.exists(goma_stats_file):
      with open(goma_stats_file) as f:
        event.stats.ParseFromString(f.read())
        event.exit_status = compile_events_pb2.CompileEvent.OK
    else:
      if goma_crash_report and os.path.exists(goma_crash_report):
        with open(goma_crash_report) as f:
          event.crash_id = f.read().strip()
        event.exit_status = compile_events_pb2.CompileEvent.CRASHED
      if goma_utils.IsCompilerProxyKilledByFatalError():
        event.exit_status = compile_events_pb2.CompileEvent.DIED_WITH_LOG_FATAL

    # BQ uploader.
    bigquery.helper.send_rows(bqclient,
                              COMPILE_EVENTS_DATASET,
                              COMPILE_EVENTS_TABLE,
                              [event])
    print 'Uploaded CompileEvent to BQ %s.%s' % (
        COMPILE_EVENTS_DATASET, COMPILE_EVENTS_TABLE)
  except Exception, inst:  # safety net
    print('failed to send CompileEvent to BQ: %s' % inst)
