# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import itertools
import os
import time

import buildbot.status.results

from buildbot.status.base import StatusReceiverMultiService
from twisted.internet import defer, reactor, task, threads
from twisted.python import log, threadpool

from infra_libs import ts_mon

uptime = ts_mon.FloatMetric('buildbot/master/uptime',
    'Time (in seconds) since the master was started',
    [ts_mon.StringField('master')])
accepting_builds = ts_mon.BooleanMetric('buildbot/master/accepting_builds',
    'Whether the master\'s BuildRequestDistributor is running',
    [ts_mon.StringField('master')])

connected = ts_mon.GaugeMetric('buildbot/master/builders/connected_slaves',
    'Number of slaves currently connected, per builder',
    [ts_mon.StringField('master'), ts_mon.StringField('builder')])
current_builds = ts_mon.GaugeMetric('buildbot/master/builders/current_builds',
    'Number of builds currently running, per builder',
    [ts_mon.StringField('master'), ts_mon.StringField('builder')])
pending_builds = ts_mon.GaugeMetric('buildbot/master/builders/pending_builds',
    'Number of builds pending, per builder',
    [ts_mon.StringField('master'), ts_mon.StringField('builder')])
last_build_status = ts_mon.StringMetric('buildbot/master/builders/last_result',
    'The build result of the last completed build.',
    [ts_mon.StringField('master'), ts_mon.StringField('builder')])
consecutive_failures = ts_mon.GaugeMetric(
    'buildbot/master/builders/consecutive_failures',
    'The number of consecutive failures until now.', [
        ts_mon.StringField('master'),
        ts_mon.StringField('builder'),
        ts_mon.StringField('failure_type')])
state = ts_mon.StringMetric('buildbot/master/builders/state',
    'State of this builder - building, idle, or offline',
    [ts_mon.StringField('master'), ts_mon.StringField('builder')])
total = ts_mon.GaugeMetric('buildbot/master/builders/total_slaves',
    'Number of slaves configured on this builder - connected or not',
    [ts_mon.StringField('master'), ts_mon.StringField('builder')])

reactor_queue = ts_mon.GaugeMetric('buildbot/master/reactor/queue',
    'Number of items in the reactor queue.',
    None)
reactor_queue_created = ts_mon.FloatMetric(
    'buildbot/master/reactor/queue_age_created',
    'Age of oldest item in the reactor queue by creation.',
    None,
    units=ts_mon.MetricsDataUnits.MILLISECONDS)
reactor_queue_modified = ts_mon.FloatMetric(
    'buildbot/master/reactor/queue_age_modified',
    'Age of oldest item in the reactor queue by last modified.',
    None,
    units=ts_mon.MetricsDataUnits.MILLISECONDS)

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
    self.thread_pool = threadpool.ThreadPool(1, 1, 'MonitoringStatusReceiver')
    self.loop = task.LoopingCall(self.updateMetricsAndFlush)

  def startService(self):
    StatusReceiverMultiService.startService(self)
    self.status = self.parent.getStatus()
    self.status.subscribe(self)

    self.thread_pool.start()
    log.msg('MonitoringStatusReceiver: starting looping call')
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
    except Exception as ex:
      log.err(ex, 'Updating monitoring metrics failed')

    try:
      log.msg('Flushing monitoring metrics')
      yield threads.deferToThreadPool(
          reactor, self.thread_pool, self._flush_and_log_exceptions)
      log.msg('Finished flushing monitoring metrics')
    except Exception as ex:
      log.err(ex, 'Flushing monitoring metrics failed')

  @staticmethod
  def callbackInfo(f, args, kwargs):
    # Return useful information (as a human readable string) about an item
    # in the reactor call queue.
    # First: Check if this is a deferred callback.
    d = getattr(f, 'im_self', None)
    if d:
      if isinstance(d, defer.Deferred):
        callchain = []
        for filename, line, func_name, _ in d._creator:
          # Only log things that led to this callchain from the buildbot
          # directory.
          if ('buildbot_8_4p1' in filename
              or os.path.join('scripts', 'master') in filename):
            shortname = os.path.basename(filename)
            callchain.append('%s:%d:%s' % (shortname, line, func_name))
        return str(callchain)
      return repr(d)
    # Otherwise, just return the __code__ information of the callable.
    return str(getattr(f, '__code__', 'Unknown'))

  @defer.inlineCallbacks
  def updateMetrics(self):
    # Log a few current items in the queue for debugging.
    log.msg('Reactor queue: len=%d ==Items:\n  %s' % (
        len(reactor.threadCallQueue),
        '\n  '.join(self.callbackInfo(f, args, kwargs)
                  for f, args, kwargs in reactor.threadCallQueue[:20]),
    ))
    uptime.set(time.time() - SERVER_STARTED, fields={'master': ''})
    accepting_builds.set(bool(self.status.master.botmaster.brd.running),
                         fields={'master': ''})
    reactor_queue.set(len(reactor.threadCallQueue))

    # Iterate through the reactor queue to figure out the oldest deferred.
    created = 0.0
    modified = 0.0
    now = time.time() * 1000
    for f, _, _ in reactor.threadCallQueue:
      d = getattr(f, 'im_self', None)
      if d:
        created = max(created, now - d._created)
        modified = max(modified, now - d._modified)
    reactor_queue_created.set(created)
    reactor_queue_modified.set(modified)

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

      for builder_name in builder_names:
        pending_builds.set(
            pending_per_builder[builder_name],
            fields={'builder': builder_name, 'master': ''})

  def _flush_and_log_exceptions(self):
    try:
      ts_mon.flush()
    except Exception:
      log.err(None, 'Automatic monitoring flush failed.')
