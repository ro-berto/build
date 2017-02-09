# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common twistd configuration for buildbot.

Use this with:
  twistd -y buildbot.tac -d path/to/master
"""

import argparse
import logging
import os

from buildbot.master import BuildMaster
from infra_libs import ts_mon
from twisted.application import service
from twisted.python import log


class TwistedLogHandler(logging.Handler):
  def emit(self, record):
    log.msg(self.format(record))


def setup_logging():
  # Redirect Python logging messages to the twistd.log file.
  logging.basicConfig(level=logging.INFO)
  logging.root.addHandler(TwistedLogHandler())


def setup_timeseries_monitoring():
  parser = argparse.ArgumentParser()
  ts_mon.add_argparse_options(parser)
  parser.set_defaults(
      ts_mon_target_type='task',
      ts_mon_task_service_name='buildmaster',
      ts_mon_task_job_name=os.path.basename(os.getcwd()),
      # Flushing is done by MonitoringStatusReceiver.  Using 'auto' here doesn't
      # work because the thread doesn't get forked along with the rest of the
      # process by twistd.
      ts_mon_flush='manual',
  )
  args = parser.parse_args([])
  ts_mon.process_argparse_options(args)


setup_logging()
application = service.Application('buildmaster')
BuildMaster(os.getcwd(), 'master.cfg').setServiceParent(application)
setup_timeseries_monitoring()
