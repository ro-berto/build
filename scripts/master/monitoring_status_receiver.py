# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.status.base import StatusReceiverMultiService
from twisted.internet import task
from twisted.python import log, threadpool

from infra_libs import ts_mon


class MonitoringStatusReceiver(StatusReceiverMultiService):
  """Flushes ts_mon metrics once per minute."""

  def __init__(self):
    StatusReceiverMultiService.__init__(self)
    self.status = None
    self.thread_pool = threadpool.ThreadPool(1, 1)
    self.loop = task.LoopingCall(self._flush)

  def startService(self):
    StatusReceiverMultiService.startService(self)
    self.status = self.parent.getStatus()
    self.status.subscribe(self)

    self.thread_pool.start()
    self.loop.start(60, now=False)

  def stopService(self):
    self.loop.stop()
    self.thread_pool.stop()
    return StatusReceiverMultiService.stopService(self)

  def _flush(self):
    self.thread_pool.callInThread(self._flush_and_log_exceptions)

  def _flush_and_log_exceptions(self):
    try:
      ts_mon.flush()
    except Exception:
      log.err(None, 'Automatic monitoring flush failed.')
