# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import itertools
import time

import buildbot.status.results

from buildbot.status.base import StatusReceiverMultiService
from twisted.internet import defer, reactor, task, threads
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
last_build_status = ts_mon.StringMetric('buildbot/master/builders/last_result',
    description='The build result of the last completed build.')
consecutive_failures = ts_mon.GaugeMetric(
    'buildbot/master/builders/consecutive_failures',
    description='The number of consecutive failures until now.')
state = ts_mon.StringMetric('buildbot/master/builders/state',
    description='State of this builder - building, idle, or offline')
total = ts_mon.GaugeMetric('buildbot/master/builders/total_slaves',
    description='Number of slaves configured on this builder - connected or '
                'not')

reactor_queue = ts_mon.GaugeMetric('buildbot/master/reactor/queue',
    description='Number of items in the reactor queue.')

pool_queue = ts_mon.GaugeMetric('buildbot/master/thread_pool/queue',
    description='Number of runnables queued in the database thread pool')
pool_waiting = ts_mon.GaugeMetric('buildbot/master/thread_pool/waiting',
    description='Number of idle workers for the database thread pool')
pool_working = ts_mon.GaugeMetric('buildbot/master/thread_pool/working',
    description='Number of running workers for the database thread pool')

SERVER_STARTED = time.time()


def generateFailureFields(fields, failure_type):
  """Make a copy of the metric fields with failure type added."""
  copied_fields = fields.copy()
  copied_fields['failure_type'] = buildbot.status.results.Results[failure_type]
  return copied_fields


def calculateConsecutiveFailures(failure_type, build, cache_factor=0.5):
  """Counts consecutive failure types going backward in time.

  Limit oursevles to half the cache (by default) to prevent issues like what
  happened in https://codereview.chromium.org/18429003#msg1. We use iterators
  here to be 'lazy' and not access builds if we don't have to.
  """

  def buildResultIterator(build):
    while build:
      yield build.getResults()
      build = build.getPreviousBuild()

  # How many builds back we'll look.
  backward_seek_limit = int(build.getBuilder().buildCacheSize * cache_factor)

  # An iterator that only gives us up to backward_seek_limit builds.
  cache_limited_iterator = itertools.islice(
      buildResultIterator(build),
      backward_seek_limit)

  # Filter out unfinished builds.
  finished_build_iterator = itertools.ifilter(
      lambda x: x is not None,
      cache_limited_iterator)

  # Find the first string of consecutive builds matching the failure_type.
  most_recent_consecutive_builds = itertools.takewhile(
      lambda x: x == failure_type,
      finished_build_iterator)

  return len(list(most_recent_consecutive_builds))


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
    log.msg('MonitoringStatusReceiver: stopping looping call')
    self.loop.stop()
    log.msg('MonitoringStatusReceiver: stopping thread pool')
    self.thread_pool.stop()
    log.msg('MonitoringStatusReceiver: stopped')
    return StatusReceiverMultiService.stopService(self)

  @defer.inlineCallbacks
  def updateMetricsAndFlush(self):
    try:
      log.msg('Updating monitoring metrics')
      yield self.updateMetrics()
    finally:
      log.msg('Flushing monitoring metrics')
      yield threads.deferToThreadPool(
          reactor, self.thread_pool, self._flush_and_log_exceptions)
      log.msg('Finished flushing monitoring metrics')

  @staticmethod
  def callbackInfo(f, args, kwargs):
    # Return useful information (as a human readable string) about an item
    # in the reactor call queue.
    # First: Check if this is a deferred callback.
    d = getattr(f, 'im_self', None)
    if d:
      if isinstance(d, defer.Deferred):
        if d.callbacks:
          # Callbacks contains a list of (success), (errback) callback tuples.
          callback, _ = d.callbacks[0]
          # Each callback tuple contains a function, args, kwargs.
          # We just need the function.
          cf, _, _ = callback
          # Print out the code location for the first callback of the
          # deferred chain.
          return '<Deferred of %s>' % getattr(cf, '__code__', 'Unknown')
      return repr(d)
    # Otherwise, just return the __code__ information of the callable.
    return str(getattr(f, '__code__', 'Unknown'))

  @defer.inlineCallbacks
  def updateMetrics(self):
    uptime.set(time.time() - SERVER_STARTED, fields={'master': ''})
    accepting_builds.set(bool(self.status.master.botmaster.brd.running),
                         fields={'master': ''})
    pool = self.status.master.db.pool
    pool_queue.set(pool.q.qsize(), fields={'master': ''})
    pool_waiting.set(len(pool.waiters), fields={'master': ''})
    pool_working.set(len(pool.working), fields={'master': ''})
    reactor_queue.set(len(reactor.threadCallQueue))
    # Log a few current items in the queue for debugging.
    log.msg('Reactor queue: len=%d [%s, ...]' % (
        len(reactor.threadCallQueue),
        ', '.join(self.callbackInfo(f, args, kwargs)
                  for f, args, kwargs in reactor.threadCallQueue[:10])[:300],
    ))

    builder_names = set()
    for builder_name in self.status.getBuilderNames():
      builder_names.add(builder_name)
      fields = {'builder': builder_name, 'master': ''}
      builder = self.status.getBuilder(builder_name)
      slaves = builder.getSlaves()

      connected.set(sum(1 for x in slaves if x.connected), fields=fields)
      current_builds.set(len(builder.getCurrentBuilds()), fields=fields)
      state.set(builder.currentBigState, fields=fields)
      total.set(len(slaves), fields=fields)

      last_build = builder.getLastFinishedBuild()
      if last_build:
        result_code = last_build.getResults()
        result_string = buildbot.status.results.Results[result_code]

        last_build_status.set(result_string, fields=fields)

        for failure_type in (
            buildbot.status.results.EXCEPTION,
            buildbot.status.results.FAILURE):

          consecutive_failures.set(
              calculateConsecutiveFailures(failure_type, last_build),
              generateFailureFields(fields, failure_type)
          )

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
        if brdict['buildername'] not in builder_names:
          continue  # Maybe the builder's configuration was removed.
        pending_per_builder[brdict['buildername']] += 1

      for builder_name, count in pending_per_builder.iteritems():
        pending_builds.set(count,
                           fields={'builder': builder_name, 'master': ''})

  def _flush_and_log_exceptions(self):
    try:
      ts_mon.flush()
    except Exception:
      log.err(None, 'Automatic monitoring flush failed.')
