# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""CrbuildIntegrator integrates Buildbot and Crbuild."""

from datetime import datetime
import logging
import traceback

from master.crbuild.common import log
from twisted.internet.defer import inlineCallbacks, returnValue


# crbuild API-related constants.
PROBE_LEASE_SECONDS = 20 # time enough to schedule and start a build.


# Buildbot-related constants.
BUILD_ETA_UPDATE_INTERVAL_SECONDS = 10
BUILD_KEY_PROPERTY = 'build_key'
BUILDSET_REASON = 'crbuild'
CHANGE_CACHE_NAME = 'crbuild_changes'
CHANGE_CATEGORY = 'crbuild'
CHANGE_REASON = 'crbuild'
COMMIT_KEY_PROPERTY = 'commit_key'
STATE_PROPERTY = 'crbuild'  # A Buildbot property for crbuild-specific info.
STATE_PROPERTY_SOURCE = 'crbuild'


class CrbuildIntegrator(object):
  """Integrates Buildbot with crbuild service.

  Two extenal systems CrbuildIntegrator integrates are represented by
  |buildbot| and |build_service| parameters of the start() method. Here
  |buildbot| is BuildbotGateway, which encapsulates Buildbot API, and
  |build_service| is a DeferredResource for crbuild API.

  CrbuildIntegrator has to be explicitly started and stopped. Normally
  CrbuildPoller does that in startService/stopService.
  """

  def __init__(self, build_namespaces):
    """Creates a CrbuildIntegrator.

    Args:
      build_namespaces (list of str): poll only builds in any of
        |build_namespaces|.
    """
    assert build_namespaces, 'Build namespaces not specified'
    self.build_namespaces = build_namespaces[:]
    self.buildbot = None
    self.build_service = None
    self._find_change_cache = None
    self.started = False

  def start(self, buildbot, build_service):
    assert not self.started, 'CrbuildIntegrator is already started'
    assert buildbot
    assert build_service
    self.buildbot = buildbot
    self.build_service = build_service
    self.build_service.start()
    self.started = True
    log('integrator started')

  def stop(self):
    if self.started is None:
      return
    self.buildbot = None
    self.build_service.stop()
    self.build_service = None
    self.started = False
    log('integrator stopped')

  @inlineCallbacks
  def _find_change_in_db(self, revision_commit_key):
    """Searches for a Change object by revision and commit_key in database.

    Args:
      revision_commit_key: a tuple of revision and commit_key.

    Every Change object has a revision attribute. Commit key is stored as
    STATE_PROPERTY/COMMIT_KEY_PROPERTY property.

    This function runs a db query to find Changes by revision and then filters
    them by commit_key. Presumably, there won't be many changes with the same
    revision, which is a git sha or svn revision number, so filtering by
    commit_key in memory is OK.

    Returns:
      buildbot.changes.change.Change object as Deferred.
    """
    revision, commit_key = revision_commit_key
    change_ids = yield self.buildbot.find_changes_by_revision(revision)
    for change_id in change_ids:
      change = yield self.buildbot.get_change_by_id(change_id)
      state = change.properties.getProperty(STATE_PROPERTY)
      if state is None:
        continue
      prop_value = state.get(COMMIT_KEY_PROPERTY)
      if str(prop_value) == str(commit_key):
        returnValue(change)
        return

  def _find_change(self, revision, commit_key):
    """Searches for a Change by revision and commit_key. Uses cache."""
    if self._find_change_cache is None:
      self._find_change_cache = self.buildbot.get_cache(
          CHANGE_CACHE_NAME,
          self._find_change_in_db
      )

    # Use (revision, commit_key) tuple as cache key.
    return self._find_change_cache.get((revision, commit_key))

  def _insert_change(self, commit):
    """Inserts a new Change object to the buildbot.

    Args:
      commit (dict): a commit returned by build.lease service method.

    Returns:
      change id as Deferred.
    """
    owner = commit.get('committer', {})
    when_timestamp = commit.get('createTime')
    if when_timestamp:
      when_timestamp = datetime.fromtimestamp(when_timestamp)

    state = {
        COMMIT_KEY_PROPERTY: commit['key'],
    }

    return self.buildbot.add_change_to_db(
        author=owner.get('email') or owner.get('name'),
        files=[f['path'] for f in commit.get('files', [])],
        comments=commit.get('message'),
        revision=commit.get('revision'),
        when_timestamp=when_timestamp,
        branch=commit.get('branch'),
        category=CHANGE_CATEGORY,
        revlink=commit.get('url'),
        properties={
            STATE_PROPERTY: (state, 'Change'),
        },
        repository=commit['repoUrl'],
        project=commit.get('project'),
    )

  @inlineCallbacks
  def _get_change(self, commit):
    """Returns an existing or new Change for a commit.

    Args:
      commit (dict): a commit returned by build.lease service method.

    Returns:
      buildbot.changes.change.Change object as Deferred.
    """
    change = yield self._find_change(commit['revision'], commit['key'])
    if change is None:
      change_id = yield self._insert_change(commit)
      change = yield self.buildbot.get_change_by_id(change_id)
    returnValue(change)

  @inlineCallbacks
  def _insert_source_stamp(self, commits):
    """Inserts a new SourceStamp for the list of commits and returns ssid."""
    assert commits
    changes = []
    for commit in commits:
      change = yield self._get_change(commit)
      changes.append(change)
    main_change = changes[0]
    ssid = yield self.buildbot.insert_source_stamp_to_db(
        branch=main_change.branch,
        revision=main_change.revision,
        repository=main_change.repository,
        project=main_change.project,
        changeids=[c.number for c in changes],
    )
    returnValue(ssid)

  @inlineCallbacks
  def _schedule(self, builder_name, build_key, ssid):
    """Schedules a build and returns (bsid, brid) tuple as Deferred."""
    state = {
        BUILD_KEY_PROPERTY: build_key,
    }

    bsid, brid = yield self.buildbot.add_buildset(
        ssid=ssid,
        reason=BUILDSET_REASON,
        builderNames=[builder_name],
        properties={
            STATE_PROPERTY: (state, STATE_PROPERTY_SOURCE),
        },
        external_idstring=build_key,
    )
    log('Scheduled a build %s for %s' % (bsid, builder_name))
    returnValue((bsid, brid))

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
  def _try_schedule_builds(self, builds, commits, scheduled_build_keys):
    """Schedule builds if builds are valid and there is capacity.

    Args:
      builds: list of build dicts from build.lease api.
      commits: list of commit dicts from build.lease api.
      scheduled_build_keys (set): a set, where kets of scheduled builds will be
        added.
    """

    commit_map = {c['key']: c for c in commits}
    ssid_cache = {}

    @inlineCallbacks
    def get_ssid(commit_keys):
      """Returns ssid for |commit_keys| or None if they are bad."""
      assert commit_keys
      commit_keys = sorted(commit_keys)  # make order deterministic.
      cache_key = tuple(commit_keys)
      ssid = ssid_cache.get(cache_key)
      if ssid is not None:
        returnValue(ssid)
        return

      commits = []
      for commit_key in commit_keys:
        commit = commit_map.get(commit_key)
        if not commit:
          log('Commit %s not found' % commit_key)
          returnValue(None)
          return
        commits.append(commit)

      ssid = yield self._insert_source_stamp(commits)
      ssid_cache[cache_key] = ssid
      returnValue(ssid)

    builders = self.buildbot.get_builders()
    for build in builds:
      builder_name = build['builderName']
      build_key = build['key']
      builder = builders.get(builder_name)
      if builder is None:
        log('Invalid builder name: %s' % builder_name)
        continue
      has_capacity = yield self._builder_can_accept_more_builds(builder)
      if not has_capacity:
        log('Cannot schedule %s: no available slaves' % builder_name)
        continue

      ssid = yield get_ssid(build['commitKeys'])
      if ssid is None:
        continue
      log('Scheduling %s...' % builder_name)
      yield self._schedule(builder_name, build_key, ssid)
      scheduled_build_keys.add(build_key)

  @inlineCallbacks
  def _unlease_non_scheduled_builds(self, all_builds, scheduled_build_keys):
    """Unleases non-scheduled builds."""
    for build in all_builds:
      build_key = build['key']
      assert build_key is not None
      if build_key in scheduled_build_keys:
        continue
      try:
        yield self.build_service.api.update(body=dict(
            buildKey=build_key,
            leaseSeconds=0
        ))
      except Exception:
        log('Error: could not update lease for %s %s: %s' %
            (build['builderName'], build_key, traceback.format_exc()))

  @inlineCallbacks
  def poll_builds(self):
    """Polls crbuild and schedules builds."""
    assert self.started
    available_slaves = self.buildbot.get_available_slaves()
    if not available_slaves:
      log('no available slaves. Not leasing.', level=logging.DEBUG)
      return

    log('Leasing builds...')
    lease = yield self.build_service.api.lease(body=dict(
        tags=self.build_namespaces,
        # Assume in the worst case 2 builds out of 3 will not be scheduled.
        maxBuilds=len(available_slaves) * 3,
        leaseSeconds=PROBE_LEASE_SECONDS,
    ))

    commits = lease.get('commits', [])
    builds = lease.get('builds', [])
    log('Got %d builds' % len(builds))

    scheduled = set()
    try:
      yield self._try_schedule_builds(builds, commits, scheduled)
    finally:
      # Update build leases in the finally statement because we want to unlease
      # builds that were not scheduled.
      yield self._unlease_non_scheduled_builds(builds, scheduled)

  @staticmethod
  def is_crbuild_build(build):
    """Returns True if |build| is scheduled by crbuild."""
    state = build.properties.getProperty(STATE_PROPERTY)
    return state is not None

  def update_build(self, build, **update_body):
    """Updates a build on crbuild.

    Args:
      build: A Buildbot build. Its properties are used to get the build key.
      update_body: body parameters for build.update API method.

    Returns:
      The API call result as Deferred, or None if build is not a crbuild build.
    """
    state = build.properties.getProperty(STATE_PROPERTY)
    if state is None:
      return None
    build_key = state[BUILD_KEY_PROPERTY]

    log('updating build %s' % build_key)
    update_body['buildKey'] = build_key
    return self.build_service.api.update(body=update_body)

  @classmethod
  def inc_lease(cls, lease_seconds):
    # Increase lease by 20% or 10 seconds, which ever is greater, to give
    # buildbot an opportunity to hang a bit.
    return max(int(lease_seconds * 1.2), lease_seconds + 10)

  def on_build_started(self, build):
    # TODO(nodir): introduce "lease_key". Check lease_key when a build starts.
    # If the lease_key is expired, abort the build.

    # TODO(nodir): add "if status=scheduled" condition. The deal is, this
    # request may face a transient error and build_finished may not. In this,
    # case the request order is undefined, so a build may transition from
    # SUCCESS to BUILDING. Add a condition parameter "ifStatusEquals".
    # Also on the server-side, do not allow transitioning a build from a final
    # state to BUILDING.
    return self.update_build(
        build,
        url=self.buildbot.get_build_url(build),
        status='BUILDING',
        leaseSeconds=self.inc_lease(BUILD_ETA_UPDATE_INTERVAL_SECONDS),
    )

  def on_build_eta_update(self, build, eta_seconds):
    lease = max(BUILD_ETA_UPDATE_INTERVAL_SECONDS, eta_seconds)
    lease = self.inc_lease(lease)
    return self.update_build(build, leaseSeconds=lease)

  def on_build_finished(self, build, status):
    return self.update_build(
        build,
        status=status,
        leaseSeconds=0,
    )
