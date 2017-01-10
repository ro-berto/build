# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import collections
import datetime
import functools
import json
import os
import time
import zlib

from buildbot.status.base import StatusReceiverMultiService
from buildbot.util.lru import SyncLRUCache
from master import auth
from master.deferred_resource import DeferredResource
from twisted.internet import defer, reactor
from twisted.python import log


PUBSUB_SCOPES = ['https://www.googleapis.com/auth/pubsub']


class PubSubClient(object):
  """A client residing in a separate process to send data to PubSub."""

  def __init__(self, topic, service_account_file):
    self.closed = False
    self.topic = topic
    self.service_account_file = '/' + os.path.join(
        'creds', 'service_accounts', service_account_file)
    try:
      self.credentials = auth.create_service_account_credentials(
          self.service_account_file, scope=PUBSUB_SCOPES)
    except auth.Error as e:
      log.err(
          'PubSub: Could not load credentials %s: %s.' % (
              self.service_account_file, e))
      self.closed = True
      raise e
    self.resource = None
    log.msg('PubSub client for topic %s created' % self.topic)

  @defer.inlineCallbacks
  def start(self):
    self.resource = yield DeferredResource.build(
        'pubsub', 'v1', credentials=self.credentials)
    self.resource.start()
    # Check to see if the topic exists.  Anything that's not a 200 means it
    # doesn't exist or is inaccessable.
    res = yield self.resource.api.projects.topics.get(topic=self.topic)
    log.msg('PubSub client for topic %s started: %s' % (self.topic, res))

  def close(self):
    self.resource.stop()
    self.closed = True

  def send(self, data):
    # TODO(hinoka): Sign messages so that they can be verified to originate
    # from buildbot.
    assert self.resource

    body = { 'messages': [{'data': data }] }

    log.msg('PubSub: Sending %d bytes' % len(data))
    return self.resource.api.projects.topics.publish(
        topic=self.topic, body=body)

# Annotation that wraps an event handler.
def event_handler(func):
  """Annotation to simplify 'StatusReceiver' event callback methods.

  This annotation uses the wrapped function's name as the event name and
  logs the event if the 'StatusPush' is configured to be verbose.
  """
  status = func.__name__
  @functools.wraps(func)
  def wrapper(self, *args, **kwargs):
    if self.verbose:
      log.msg('Status update (%s): %s %s' % (
          status, args, ' '.join(['%s=%s' % (k, kwargs[k])
                                  for k in sorted(kwargs.keys())])))
    return func(self, *args, **kwargs)
  return wrapper


class ConfigError(ValueError):
  pass
class NotEnabled(Exception):
  """Raised when PubSub is purposely not enabled."""


_BuildBase = collections.namedtuple(
    '_BuildBase', ('builder_name', 'build_number'))
class _Build(_BuildBase):
  # Disable "no __init__ method" warning | pylint: disable=W0232
  def __repr__(self):
    return '%s/%s' % (self.builder_name, self.build_number)


class MessageTooBigError(Exception):
  pass


class StatusPush(StatusReceiverMultiService):
  """
  Periodically push builder status updates to pubsub.
  """

  DEFAULT_PUSH_INTERVAL_SEC = 30

  # Perform verbose logging.
  verbose = True

  @classmethod
  def CreateStatusPush(cls, activeMaster, pushInterval=None):
    assert activeMaster, 'An active master must be supplied.'
    if not (
          activeMaster.is_production_host or os.environ.get('TESTING_MASTER')):
      log.msg(
          'Not a production host or testing, not loading the PubSub '
          'status listener.')
      return None

    topic = getattr(activeMaster, 'pubsub_topic', None)
    if not topic:
      log.msg('PubSub: Missing pubsub_topic, not enabling.')
      return None

    # Set the master name, for indexing purposes.
    name = getattr(activeMaster, 'name', None)
    if not name:
      raise ConfigError(
          'A master name must be supplied for pubsub push support.')

    service_account_file = getattr(
        activeMaster, 'pubsub_service_account_file', None)
    if not service_account_file:
      raise ConfigError('A service account file must be specified.')

    return cls(topic, service_account_file, name, pushInterval)


  def __init__(self, topic, service_account_file, name, pushInterval=None):
    """Instantiates a new StatusPush service.

    Args:
      topic: Pubsub topic to push updates to.
      service_account_file: Credentials to use to push to pubsub.
      pushInterval: (number/timedelta) The data push interval. If a number is
          supplied, it is the number of seconds.
    """
    StatusReceiverMultiService.__init__(self)

    # Parameters.
    self.pushInterval = self._getTimeDelta(pushInterval or
                                           self.DEFAULT_PUSH_INTERVAL_SEC)

    self.name = name  # Master name, since builds don't include this info.
    self.topic = topic
    self._service_account_file = service_account_file
    self._client = None
    self._status = None
    self._res = None
    self._updated_builds = set()
    self._pushTimer = None
    self._splits = 1
    # Cache pending builds by brid, because they are expensive to query.
    self._pending_build_lru = SyncLRUCache(
        self._get_build_request, max_size=200)
    log.msg('Creating PubSub service.')

  @staticmethod
  def _getTimeDelta(value):
    """Returns: A 'datetime.timedelta' representation of 'value'."""
    if isinstance(value, datetime.timedelta):
      return value
    elif isinstance(value, (int, long)):
      return datetime.timedelta(seconds=value)
    raise TypeError('Unknown time delta type; must be timedelta or number.')

  @defer.inlineCallbacks
  def startService(self):
    """Twisted service is starting up."""
    StatusReceiverMultiService.startService(self)

    # Subscribe to get status updates.
    self._status = self.parent.getStatus()
    self._status.subscribe(self)

    # Init the client.
    self._client = PubSubClient(self.topic, self._service_account_file)
    yield self._client.start()

    # Schedule our first push.
    self._schedulePush()

    # Register our final push to happen when the reactor exits.
    reactor.addSystemEventTrigger('during', 'shutdown', self._stop)

  def stopService(self):
    """Twisted service is shutting down.

    We do nothing here because events still fire after stopService is called.
    """
    log.msg("PubSub: stopService called...")

  @defer.inlineCallbacks
  def _stop(self):
    """Do a final push and close our resource."""
    self._clearPushTimer()

    # Do one last status push.
    log.msg("PubSub: One last status push.")
    yield self._doStatusPush(self._updated_builds)

    # Stop our resource.
    log.msg("PubSub: Closing client.")
    self._client.close()
    log.msg("PubSub: Client closed.")

  @staticmethod
  def _build_pubsub_message(obj):
    data = base64.b64encode(zlib.compress(json.dumps(obj)))
    if len(data) > 9 * 1024 * 1024:
      # Pubsub's total publish limit per message is 10MB, we want to be below
      # that.  Making this 9MB to account for potential overhead.
      raise MessageTooBigError()
    return data

  def _get_pubsub_messages(self, master, builds):
    splits = min(self._splits, max(len(builds), 1))
    for i in xrange(splits):
      start = int((i) * len(builds) / splits)
      end = int((i + 1) * len(builds) / splits)
      data = {}
      if builds:
        data['builds'] = builds[start:end]
      if i == 0:
        data['master'] = master
      try:
        yield self._build_pubsub_message(data)
      except MessageTooBigError:
        self._splits += 1
        raise

  def _send_messages(self, master, builds):
    done = False
    while not done:
      try:
        messages = list(self._get_pubsub_messages(master, builds))
        done = True
      except MessageTooBigError as e:
        log.msg('PubSub: Unable to send: could not break down: %s.' % (e,))
        if self._splits >= len(builds):
          log.err('PubSub: Split greater than number of builds (%d >= %d).' % (
              self._splits, len(builds)))
          raise
        else:
          log.msg('PubSub: Increasing split to %d', self._splits)
        continue

    # Send message pieces in parallel. We need to pass DeferredList a real
    # list, not a generator.
    return defer.DeferredList(list(self._client.send(msg) for msg in messages))

  @defer.inlineCallbacks
  def _doStatusPush(self, updated_builds):
    """Pushes the current state of the builds in 'updated_builds'.

    Args:
      updated_builds: (collection) A collection of _Build instances to push.
    """
    # Load all build information for builds that we're pushing.
    t_start = time.time()
    builds = sorted(updated_builds)
    if self.verbose:
      log.msg('PusSub: Pushing status for builds: %s' % (builds,))
    loaded_builds = yield defer.DeferredList([self._loadBuild(b)
                                              for b in builds])

    t_load_build = time.time()
    d_load_build = t_load_build - t_start
    send_builds = []
    for i, build in enumerate(builds):
      success, result = loaded_builds[i]
      if not success:
        log.err('Failed to load build for [%s]: %s' % (build, result))
        continue

      # result is a (build, build_dict) tuple.
      _, send_build = result
      send_build['master'] = self.name
      send_builds.append(send_build)

    # Add in master builder state into the message.
    master_data = yield self._getMasterData()
    t_master_data = time.time()
    d_master = t_master_data - t_load_build

    # Gather on statistics on how many pending builds we have, for logging.
    num_build_requests = sum([
        bi['pendingBuilds'] for bi in master_data['builders'].itervalues()])
    num_build_states = sum([
        len(bi['pendingBuildStates']) for bi
        in master_data['builders'].itervalues()])

    # Split the data into batches because PubSub has a message limit of 10MB.
    res = yield self._send_messages(master_data, send_builds)
    t_send_messages = time.time()
    d_send_messages = t_send_messages - t_master_data
    for success, result in res:
      if success:
        log.msg('PubSub: Send successful: %s' % result)
      else:
        log.msg('PubSub: Failed to push: %s' % result)

    # Log how long everything took.
    t_complete = time.time()
    d_total = t_complete - t_start
    len_tcq = len(reactor.threadCallQueue)
    log.msg('PubSub: Last send session took total %.1fs, %.1f load build, '
            '%.1f master, %.1f send. len_tcq %d. br %d. bs %d' % (
                d_total, d_load_build, d_master, d_send_messages, len_tcq,
                num_build_requests, num_build_states))

  def _pushTimerExpired(self):
    """Callback invoked when the push timer has expired.

    This function takes a snapshot of updated builds and begins a push.
    """
    self._clearPushTimer()

    # Collect this round of updated builds. We clear our updated builds in case
    # more accumulate during the send interval. If the send fails, we will
    # re-add them back in the errback.
    updates = self._updated_builds.copy()
    self._updated_builds.clear()

    if self.verbose:
      log.msg('PubSub: Status push timer expired. Pushing updates for: %s' % (
              sorted(updates)))

    # Upload them. Reschedule our send timer after this push completes. If it
    # fails, add the builds back to the 'updated_builds' list so we don't lose
    # them.
    d = self._doStatusPush(updates)

    def eb_status_push(failure, updates):
      # Re-add these builds to our 'updated_builds' list.
      log.msg('PubSub: ERROR - Failed to do status push for %s:\n%s' % (
          sorted(updates), failure))
      self._updated_builds.update(updates)
    d.addErrback(eb_status_push, updates)

    def cb_schedule_next_push(ignored):
      self._schedulePush()
    d.addBoth(cb_schedule_next_push)

  def _schedulePush(self):
    """Schedules the push timer to perform a push."""
    if self._pushTimer:
      return
    if self.verbose:
      log.msg('PubSub: Scheduling push timer in: %s' % (self.pushInterval,))
    self._pushTimer = reactor.callLater(self.pushInterval.total_seconds(),
        self._pushTimerExpired)

  def _clearPushTimer(self):
    """Cancels any current push timer and clears its state."""
    if self._pushTimer:
      if self._pushTimer.active():
        self._pushTimer.cancel()
      self._pushTimer = None

  def _loadBuild(self, b):
    """Loads the build dictionary associated with a '_Build' object.

    Returns: (build, build_data), via Deferred.
      build: (_Build) The build object that was loaded.
      build_data: (dict) The build data for 'build'.
    """
    builder = self._status.getBuilder(b.builder_name)
    build = builder.getBuild(b.build_number)
    return defer.succeed((b, build.asDict()))

  @staticmethod
  def _get_build_request(_key, pb_request_status):
    """Retrieves source, reason, builderName, and submittedAt from a pbrs.

    the key param is not used.  It's just there to satisfy the function
    signature for SyncLRUCache's miss_fn.

    This takes a pending build request status object, and runs a query
    against postgres.  This is fairly expensive.
    """
    return pb_request_status._getBuildRequest()

  @defer.inlineCallbacks
  def _get_pending_build(self, pb_request_status):
    """Returns a pending build.

    This tries to fetch the pending build first from the in-memory cache,
    then tries postgres.  If it goes into postgres, it gets pretty expensive.
    """
    result = {}

    br = yield self._pending_build_lru.get(
        pb_request_status.brid, pb_request_status=pb_request_status)
    if not br:
      log.msg(
          'PubSub: WARNING - no build request found for %s'
          % pb_request_status.brid)
      defer.returnValue(None)
    result['builderName'] = pb_request_status.getBuilderName()
    result['source'] = br.source.asDict()
    result['reason'] = br.reason
    result['submittedAt'] = br.submittedAt

    defer.returnValue(result)

  @defer.inlineCallbacks
  def _getBuilderData(self, name, builder, get_pending=True):
    # This requires a deferred call since the data is queried from
    # the postgres DB (sigh).
    pending = []
    if get_pending:
      pending = yield builder.getPendingBuildRequestStatuses()
    # Optimization cheat: only get the first 25 pending builds.
    # This caps the amount of postgres db calls and json size for really out
    # of control builders
    num_pending = len(pending)
    pending = pending[:25]
    pendingStates = yield defer.DeferredList([
        self._get_pending_build(p) for p in pending])
    # Not included: basedir, cachedBuilds.
    # cachedBuilds isn't useful and takes a ton of resources to compute.
    builder_info = {
      'slaves': builder.slavenames,
      'currentBuilds': sorted(b.getNumber() for b in builder.currentBuilds),
      'pendingBuilds': num_pending,
      # p is a tuple of (success, payload)
      'pendingBuildStates': [p[1] for p in pendingStates if p[0] and p[1]],
      'state': builder.getState()[0],
      'category': builder.category,
    }
    defer.returnValue((name, builder_info))

  @defer.inlineCallbacks
  def _getMasterData(self):
    """Loads and returns a subset of the master data as a JSON.

    This includes:
    * builders: List of builders (builbot.status.builder.Builder).
    * slaves: List of slaves (buildbot.status.slave).
    """
    builders = {builder_name: self._status.getBuilder(builder_name)
                for builder_name in self._status.getBuilderNames()}
    builder_infos = {}

    # TODO(hinoka): Re-enable getting pending build info for masters when
    #               performance issues are fixed crbug.com/679563
    get_pending = False

    # Fetch all builder info in parallel.
    builder_info_list = yield defer.DeferredList([
        self._getBuilderData(name, builder, get_pending)
        for name, builder in builders.iteritems()])
    builder_infos = {
        data[0]: data[1] for success, data in builder_info_list if success}

    slaves = {slave_name: self._status.getSlave(slave_name).asDict()
              for slave_name in self._status.getSlaveNames()}
    defer.returnValue({
        'builders': builder_infos, 'slaves': slaves, 'name': self.name})


  def _recordBuild(self, build):
    """Records an update to a 'buildbot.status.build.Build' object.

    Args:
      build: (Build) The BuildBot Build object that was updated.
    """
    if self._client.closed:
      log.msg("PubSub: WARNING - _recordBuild called after resource closed.")
    build = _Build(
        builder_name=build.builder.name,
        build_number=build.number,
    )
    self._updated_builds.add(build)

  #### Events

  @event_handler
  def builderAdded(self, _builderName, _builder):
    return self

  @event_handler
  def buildStarted(self, _builderName, build):
    # This info is included in the master json.
    return self

  def stepStarted(self, build, _step):
    # This info is included in the master json.  No need to log this.
    return self

  @event_handler
  def buildFinished(self, _builderName, build, _results):
    self._recordBuild(build)
