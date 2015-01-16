# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""BuildBucketIntegrator integrates Buildbot and Buildbucket."""

import datetime
import json
import logging
import traceback

from buildbot.util import deferredLocked
from master.buildbucket import common, changestore
from master.buildbucket.common import log
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks, returnValue


# buildbucket API-related constants.
# time enough to schedule and start a build.
LEASE_DURATION = datetime.timedelta(minutes=5)
MAX_LEASE_DURATION = datetime.timedelta(minutes=10)

# Buildbot-related constants.
BUILD_ETA_UPDATE_INTERVAL = datetime.timedelta(seconds=5)
BUILD_ID_PROPERTY = 'build_id'
BUILDSET_REASON = 'buildbucket'
LEASE_KEY_PROPERTY = 'lease_key'
PROPERTY_SOURCE = 'buildbucket'


class BuildBucketIntegrator(object):
  """Integrates Buildbot with buildbucket.

  The |buildbot| and |buildbucket_service| parameters of the start() method
  represent the two systems BuildBucketIntegrator integrates. Here
  |buildbot| is BuildbotGateway, which encapsulates Buildbot API, and
  |buildbucket_service| is a DeferredResource for buildbucket API.

  BuildBucketIntegrator has to be explicitly started and stopped. Normally
  BuildbucketPoller does that in startService/stopService.
  """

  def __init__(self, buckets):
    """Creates a BuildBucketIntegrator.

    Args:
      buckets (list of str): poll only builds in any of |buckets|.
    """
    assert buckets, 'Buckets not specified'
    self.buckets = buckets[:]
    self.buildbot = None
    self.buildbucket_service = None
    self._find_change_cache = None
    self.started = False
    self.changes = None
    self.poll_lock = defer.DeferredLock()

  def log(self, message, level=None):
    common.log(message, level)

  def start(self, buildbot, buildbucket_service, change_store_factory=None):
    assert not self.started, 'BuildBucketIntegrator is already started'
    assert buildbot
    assert buildbucket_service
    change_store_factory = change_store_factory or changestore.ChangeStore
    self.buildbot = buildbot
    self.buildbucket_service = buildbucket_service
    self.buildbucket_service.start()
    self.changes = change_store_factory(buildbot)
    self.started = True
    self.log('integrator started')

  def stop(self):
    if not self.started:
      return
    self.buildbot = None
    self.buildbucket_service.stop()
    self.buildbucket_service = None
    self.started = False
    self.log('integrator stopped')

  @staticmethod
  def _validate_change(change):
    """Raises ValueError if change dict is invalid."""
    if not isinstance(change, dict):
      raise ValueError('change is not a dict')
    if 'id' in change:
      change_id = change['id']
      if not isinstance(change_id, basestring):
        raise ValueError('Id is not a string: "%s"' % change_id)
      if not change_id:
        raise ValueError('Invalid id: "%s"' % change_id)

    author = change.get('author')
    if author is None:
      raise ValueError('Author is not specified')
    if not isinstance(author, dict):
      raise ValueError('Author is not a dict')
    if not author.get('email'):
      raise ValueError('Author email is not specified')

  def _validate_build(self, build):
    """Raises ValueError in build dict is invalid."""
    if not build:
      raise ValueError('build is not specified')
    if build.get('id') is None:
      raise ValueError('Build id is not set')
    parameters_json = build.get('parameters_json')
    if parameters_json is None:
      raise ValueError('Build parameters (parameters_json) are not set')
    if not isinstance(parameters_json, basestring):
      raise ValueError('Build parameters_json is not a string')
    try:
      params = json.loads(parameters_json)
    except ValueError as ex:
      raise ValueError(
          'Could not parse parameters_json: %s.\nJSON: %s' %
          (ex, parameters_json))

    builder_name = params.get('builder_name')
    if not builder_name:
      raise ValueError('builder_name parameter is not set')
    builder = self.buildbot.get_builders().get(builder_name)
    if builder is None:
      raise ValueError('Builder %s not found' % builder_name)

    properties = params.get('properties')
    if properties is not None and not isinstance(properties, dict):
      raise ValueError('properties parameter is not a JSON object')

    changes = params.get('changes')
    if changes is not None:
      if not isinstance(changes, list):
        raise ValueError('changes parameter is not a list')
      for change in changes:
        try:
          self._validate_change(change)
        except ValueError as ex:
            raise ValueError(
                'A change is invalid: %s\nChange:%s' % (ex, change))

  def check_error(self, res):
    """If |res| contains an error, logs it and returns True.

    Args:
      res (dict): buildbucket response.

    Returns:
      True if the response contains an error. Otherwise False.
    """
    error = res.get('error')
    if not error:
      return False
    self.log('buildbucket response contains an error: "%s" (reason %s)' % (
        error.get('message', '<no message>'),
        error.get('reason', '<no reason>'),
    ))
    return True

  @inlineCallbacks
  def _builder_can_accept_more_builds(self, builder):
    """Returns True if there is space for one more build in a builder.

    There is space for one more build if capacity >= workload + 1,
    where capacity is the number of available slaves assigned to the |builder|
    and workload is the number of pending builds that these slaves will process.

    The builder-slave relationship is many-to-many. A slave assigned to the
    |builder| may be also assigned to other builders. Other builders may also
    have pending builds and _other_ slaves attached. Workload is the number of
    pending build that slaves of the |builder| will definitely process. We
    can't predict which slaves will run which pending build, so in this general
    case, we will compute the expected workload.

    For each builder B the expected number of its pending builds to be
    dispatched to slaves of |builder| is
      B.pending_build_count * percentage_of_common_slaves
    where "common slaves" are assigned to both B and |builder|.
    """
    slaves = set(builder.getSlaves())

    capacity = len(filter(self.buildbot.is_slave_available, slaves))

    workload = 0.0
    for b in self.buildbot.get_builders().itervalues():
      other_slaves = b.getSlaves()
      common_slaves = slaves.intersection(other_slaves)
      # What portion of other_builder's pending builds will be scheduled
      # to builder's slaves.
      ratio = float(len(common_slaves)) / len(slaves)
      build_requests = yield b.getPendingBuildRequestStatuses()
      workload += ratio * len(build_requests)
    returnValue(capacity >= workload + 1)

  @inlineCallbacks
  def _try_lease_build(self, build):
    lease_expiration_ts = common.datetime_to_timestamp(
        datetime.datetime.utcnow() + LEASE_DURATION)
    lease_resp = yield self.buildbucket_service.api.lease(
        id=build['id'],
        body=dict(lease_expiration_ts=lease_expiration_ts))
    lease_error = lease_resp.get('error')
    if lease_error and lease_error['reason'] == 'CANNOT_LEASE_BUILD':
      self.log('Could not lease build %s' % build['id'])
      return
    if self.check_error(lease_resp):
      return
    lease_key = lease_resp.get('build', {}).get('lease_key')
    if not lease_key:
      self.log(
          'A build has been leased, but lease_key is not provided',
          level=logging.WARNING)
      return
    returnValue(lease_key)

  @inlineCallbacks
  def _schedule(self, builder_name, properties, build_id, ssid, lease_key):
    """Schedules a build and returns (bsid, brid) tuple as Deferred."""
    info = {
        BUILD_ID_PROPERTY: build_id,
        LEASE_KEY_PROPERTY: lease_key,
    }

    properties = (properties or {}).copy()
    properties[common.INFO_PROPERTY] = info
    properties_with_source = {
        k:(v, PROPERTY_SOURCE) for k, v in properties.iteritems()
    }
    bsid, brid = yield self.buildbot.add_buildset(
        ssid=ssid,
        reason=BUILDSET_REASON,
        builderNames=[builder_name],
        properties=properties_with_source,
        external_idstring=build_id,
    )
    self.log(
        'Scheduled a buildset %s for buildbucket build %s' % (bsid, build_id))
    returnValue((bsid, brid))

  @inlineCallbacks
  def _try_schedule_build(self, build, ssid_cache):
    """Tries to schedule a build if it is valid and there is capacity.

    Args:
      build (dict): a build received from buildbucket.peek api.
    """
    self.log(
        'Will try to schedule buildbucket build %s' % build.get('id'),
        level=logging.DEBUG)

    try:
      self._validate_build(build)
    except ValueError as ex:
      self.log(
          'Build is invalid: %s.\nBuild definition: %s' %
          (ex, json.dumps(build)))
      return

    build_id = build['id']
    params = json.loads(build['parameters_json'])
    builder_name = params['builder_name']
    builder = self.buildbot.get_builders()[builder_name]
    has_capacity = yield self._builder_can_accept_more_builds(builder)
    if not has_capacity:
      self.log('Cannot schedule %s: no available slaves' % builder_name)
      return

    lease_key = yield self._try_lease_build(build)
    if not lease_key:
      self.log('Could not lease build %s' % build_id)
      return
    self.log('Scheduling build %s (%s)...' % (build_id, builder_name))

    changes = params.get('changes') or []
    ssid = yield self.changes.get_source_stamp(changes)

    properties = params.get('properties')
    yield self._schedule(builder_name, properties, build_id, ssid, lease_key)

  @deferredLocked('poll_lock')
  @inlineCallbacks
  def poll_builds(self):
    """Polls buildbucket and schedules builds."""
    assert self.started
    start_cursor = None
    ssid_cache = {}

    # Assume in the worst case 2 builds out of 3 will not be scheduled.
    # max_builds is computed only once, before the loop, because
    # query parameters must not be changed between pages.
    max_builds = len(self.buildbot.get_available_slaves()) * 3

    while True:
      if not self.buildbot.get_available_slaves():
        break

      self.log('peeking builds...')
      peek_resp = yield self.buildbucket_service.api.peek(
          bucket=self.buckets,
          max_builds=max_builds,
          start_cursor=start_cursor,
      )
      if self.check_error(peek_resp):
        break
      start_cursor = peek_resp.get('next_cursor')

      builds = peek_resp.get('builds', [])
      self.log('got %d builds' % len(builds))

      for build in builds:
        if build:
          yield self._try_schedule_build(build, ssid_cache)
      if not start_cursor:
        break

  @staticmethod
  def is_buildbucket_build(build):
    """Returns True if |build|'s origin is buildbucket."""
    info = build.properties.getProperty(common.INFO_PROPERTY)
    return info is not None

  @staticmethod
  def _get_build_id_and_lease_key(build):
    """Returns buildbucket build id and lease_key from a buildbot build."""
    info = build.properties.getProperty(common.INFO_PROPERTY)
    if info is None:
      return None, None
    build_id = info.get(BUILD_ID_PROPERTY)
    lease_key = info.get(LEASE_KEY_PROPERTY)
    assert build_id
    assert lease_key
    return build_id, lease_key

  @staticmethod
  def adjust_lease_duration(duration):
    """Increases lease duration, but not exceed buildbucket's limit.

    Increases lease duration 3 times or by 5 minutes, which ever is greater,
    to give buildbot an opportunity to hang a bit.
    """
    duration = max(
        duration * 3,
        duration + datetime.timedelta(minutes=5))
    return min(duration, MAX_LEASE_DURATION)

  @classmethod
  def get_lease_expiration_ts(cls, lease_duration):
    return common.datetime_to_timestamp(
        datetime.datetime.utcnow() + cls.adjust_lease_duration(lease_duration))

  def _stop_build(self, build, error_dict):
    if build.isFinished():
      return
    error_msg = (
        'Build %d (%s) has started, but an attempt to notify buildbucket about '
        'it has failed with error "%s" (reason: %s).' % (
            build.getNumber(), build.getBuilder().getName(),
            error_dict.get('message'),
            error_dict.get('reason')))
    self.log('%s Stopping the build.' % error_msg, level=logging.ERROR)
    self.buildbot.stop_build(build, reason=error_msg)

  @inlineCallbacks
  def _leased_build_call(self, method_name, build, body):
    build_id, lease_key = self._get_build_id_and_lease_key(build)
    if not build_id:
      return

    method = getattr(self.buildbucket_service.api, method_name)
    body = body.copy()
    body['lease_key'] = lease_key
    resp = yield method(id=build_id, body=body)
    if 'error' in resp:
      self._stop_build(build, resp['error'])

  def on_build_started(self, build):
    return self._leased_build_call('start', build, {
        'url': self.buildbot.get_build_url(build),
    })

  def on_build_eta_update(self, build, eta_seconds):
    lease_duration = max(
        BUILD_ETA_UPDATE_INTERVAL,
        datetime.timedelta(seconds=eta_seconds))
    return self._leased_build_call('hearbeat', build, {
        'lease_expiration_ts': self.get_lease_expiration_ts(lease_duration),
    })

  def on_build_finished(self, build, status):
    assert status in ('SUCCESS', 'FAILURE', 'EXCEPTION', 'RETRY', 'SKIPPED')
    if not self.is_buildbucket_build(build):
      return
    self.log(
        'Build %s finished with status "%s"' % (build, status),
        level=logging.DEBUG)
    if status == 'RETRY':
      # Do not mark this build as failed. Either it will be retried when master
      # starts again and the build lease is still held, or the build lease will
      # expire.
      return
    if status == 'SKIPPED':
      # Build lease will expire on its own.
      # TODO(nodir): implement unlease API http://crbug.com/448984 and call it
      # here.
      return

    properties_to_send = build.getProperties().asDict()
    del properties_to_send[common.INFO_PROPERTY]
    body = {
        'result_details_json': json.dumps({
            'properties': properties_to_send,
        }, sort_keys=True),
    }
    if status == 'SUCCESS':
      return self._leased_build_call('succeed', build, body)
    else:
      body['failure_reason'] = (
          'BUILD_FAILURE' if status == 'FAILURE'
          else 'INFRA_FAILURE')
      return self._leased_build_call('fail', build, body)
