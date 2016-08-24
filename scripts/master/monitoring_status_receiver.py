# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import time

from buildbot.status.base import StatusReceiverMultiService
from twisted.internet import defer, reactor, task
from twisted.python import log, threadpool

from infra_libs import ts_mon

uptime = ts_mon.FloatMetric('buildbot/master/uptime',
    description='Time (in seconds) since the master was started')
accepting_builds = ts_mon.BooleanMetric('buildbot/master/accepting_builds',
    description='Whether the master\'s BuildRequestDistributor is running')

connected = ts_mon.GaugeMetric('buildbot/master/builders/connected_slaves',
    description='Number of slaves currently connected, per builder')
current_builds = ts_mon.GaugeMetric('buildbot/master/builders/current_builds',
    description='Number of builds currently running, per builder')
pending_builds = ts_mon.GaugeMetric('buildbot/master/builders/pending_builds',
    description='Number of builds pending, per builder')
state = ts_mon.StringMetric('buildbot/master/builders/state',
    description='State of this builder - building, idle, or offline')
total = ts_mon.GaugeMetric('buildbot/master/builders/total_slaves',
    description='Number of slaves configured on this builder - connected or '
                'not')

pool_queue = ts_mon.GaugeMetric('buildbot/master/thread_pool/queue',
    description='Number of runnables queued in the database thread pool')
pool_waiting = ts_mon.GaugeMetric('buildbot/master/thread_pool/waiting',
    description='Number of idle workers for the database thread pool')
pool_working = ts_mon.GaugeMetric('buildbot/master/thread_pool/working',
    description='Number of running workers for the database thread pool')

SERVER_STARTED = time.time()


class MonitoringStatusReceiver(StatusReceiverMultiService):
  """Flushes ts_mon metrics once per minute."""

  def __init__(self):
    StatusReceiverMultiService.__init__(self)
    self.status = None
    self.thread_pool = threadpool.ThreadPool(1, 1)
    self.loop = task.LoopingCall(self.updateMetricsAndFlush)

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

  @defer.inlineCallbacks
  def updateMetricsAndFlush(self):
    try:
      yield self.updateMetrics()
    finally:
      self.thread_pool.callInThread(self._flush_and_log_exceptions)

  @defer.inlineCallbacks
  def updateMetrics(self):
    uptime.set(time.time() - SERVER_STARTED)
    accepting_builds.set(bool(self.status.master.botmaster.brd.running))
    pool = self.status.master.db.pool
    pool_queue.set(pool.q.qsize())
    pool_waiting.set(len(pool.waiters))
    pool_working.set(len(pool.working))

    for builder_name in self.status.getBuilderNames():
      fields = {'builder': builder_name}
      builder = self.status.getBuilder(builder_name)
      slaves = builder.getSlaves()

      connected.set(sum(1 for x in slaves if x.connected), fields=fields)
      current_builds.set(len(builder.getCurrentBuilds()), fields=fields)
      state.set(builder.currentBigState, fields=fields)
      total.set(len(slaves), fields=fields)

    # Get pending build requests directly from the db for all builders at
    # once.
    d = self.status.master.db.buildrequests.getBuildRequests(claimed=False)

    # Timeout the database request after 5 seconds.
    def timeout():
      if not d.called:
        d.cancel()
    reactor.callLater(5, timeout)

    try:
      brdicts = yield d
    except Exception as ex:
      log.err(ex, 'getBuildRequests failed while failed populating metrics')
    else:
      pending_per_builder = collections.defaultdict(int)
      for brdict in brdicts:
        pending_per_builder[brdict['buildername']] += 1

      for builder_name, count in pending_per_builder.iteritems():
        pending_builds.set(count, fields={'builder': builder_name})

  def _flush_and_log_exceptions(self):
    try:
      ts_mon.flush()
    except Exception:
      log.err(None, 'Automatic monitoring flush failed.')
