# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ChangeStore maps buildbucket changes to Buildbot changes."""

from master.buildbucket import common
from twisted.internet import defer


class ChangeStore(object):
  """Maps buildbucket changes to Buildbot changes."""

  def __init__(self, buildbot_gateway, unique_urls=False):
    """Initializes a ChangeStore.

    If unique_urls is True, treats change's non-empty url as change identifier.
    It should be False on Rietveld-based tryservers because url may mean base
    revision where a Rietveld patchset must be applied to.
    """
    assert buildbot_gateway
    self.buildbot = buildbot_gateway
    self.unique_urls = unique_urls
    self._find_change_cache_by_id = self.buildbot.get_cache(
        'buildbucket_changes',
        self._find_change_in_db_by_id,
    )
    self._find_change_cache_by_revlink = self.buildbot.get_cache(
        'buildbucket_changes_revlink',
        self._find_change_in_db_by_revlink,
    )

  def _insert_change(self, buildbucket_change):
    """Inserts a new Change object to the buildbot.

    Args:
      buildbucket_change (dict): a change described in build parameters.

    Returns:
      Buildbot change id as Deferred.
    """
    author_email = buildbucket_change['author']['email']
    when_timestamp = buildbucket_change.get('create_ts')
    if when_timestamp:
      when_timestamp = common.timestamp_to_datetime(when_timestamp)

    info = {
        common.BUILDBUCKET_CHANGE_ID_PROPERTY: buildbucket_change.get('id'),
    }

    return self.buildbot.add_change_to_db(
        author=author_email,
        files=[f['path'] for f in buildbucket_change.get('files', [])],
        comments=buildbucket_change.get('message') or '',
        revision=buildbucket_change.get('revision') or '',
        when_timestamp=when_timestamp,
        branch=buildbucket_change.get('branch'),
        category=common.CHANGE_CATEGORY,
        revlink=buildbucket_change.get('url') or '',
        properties={
            common.INFO_PROPERTY: (info, 'Change'),
        },
        repository=buildbucket_change.get('repo_url') or '',
        project=buildbucket_change.get('project') or '',
    )

  @defer.inlineCallbacks
  def _find_change_in_db_by_id(self, revision_and_id):
    """Searches for an existing Change object in the database.

    Args:
      revision_and_id: a tuple of change revision and buildbucket-level change
        id.

    Every Change object has a revision attribute. The buildbucket-level change
    id is stored as common.INFO_PROPERTY/common.BUILDBUCKET_CHANGE_ID_PROPERTY
    property.

    This function runs a db query to find Changes by revision and then filters
    them by buildbucket-level change id. Presumably, there won't be many changes
    with the same revision, which is a git sha or svn revision number,
    so filtering by id in memory is OK.

    Returns:
      buildbot.changes.change.Change object as Deferred.
    """
    revision, buildbucket_change_id = revision_and_id
    buildbot_change_ids = yield self.buildbot.find_changes_by_revision(revision)
    for buildbot_change_id in buildbot_change_ids:
      change = yield self.buildbot.get_change_by_id(buildbot_change_id)
      info = change.properties.getProperty(common.INFO_PROPERTY)
      if info is None:
        continue
      prop_value = info.get(common.BUILDBUCKET_CHANGE_ID_PROPERTY)
      if str(prop_value) == str(buildbucket_change_id):
        defer.returnValue(change)
        return

  @defer.inlineCallbacks
  def _find_change_in_db_by_revlink(self, revlink):
    """Searches for one Change object by revlink in the database.

    Returns:
      buildbot.changes.change.Change object as Deferred.
    """
    buildbot_change_ids = yield self.buildbot.find_changes_by_revlink(revlink)
    if buildbot_change_ids:
      change = yield self.buildbot.get_change_by_id(buildbot_change_ids[0])
      defer.returnValue(change)

  @defer.inlineCallbacks
  def get_change(self, buildbucket_change):
    """Returns an existing or new Buildbot Change for a buildbucket change.

    Args:
      buildbucket_change (dict): a change found in build parameters.

    Returns:
      buildbot.changes.change.Change object as Deferred.
    """
    buildbot_change = None

    if self.unique_urls and buildbucket_change.get('url'):
      buildbot_change = yield self._find_change_cache_by_revlink.get(
          buildbucket_change.get('url'))
    elif buildbucket_change.get('revision') and buildbucket_change.get('id'):
      buildbot_change = yield self._find_change_cache_by_id.get(
          (buildbucket_change['revision'], buildbucket_change['id']))

    if buildbot_change is None:
      change_id = yield self._insert_change(buildbucket_change)
      buildbot_change = yield self.buildbot.get_change_by_id(change_id)
    defer.returnValue(buildbot_change)

  @defer.inlineCallbacks
  def _insert_source_stamp(self, buildbucket_changes):
    """Inserts a new SourceStamp for the list of changes and returns ssid."""
    assert isinstance(buildbucket_changes, list)
    buildbot_changes = []
    for buildbucket_change in buildbucket_changes:
      buildbot_change = yield self.get_change(buildbucket_change)
      buildbot_changes.append(buildbot_change)

    ss_params = {
        'changeids': [c.number for c in buildbot_changes],
        'branch': '',
        'revision': '',
        'repository': '',
        'project': '',
    }
    if buildbot_changes:
      main_change = buildbot_changes[0]
      ss_params.update({
          'branch': main_change.branch,
          'revision': main_change.revision,
          'repository': main_change.repository,
          'project': main_change.project,
      })

    ssid = yield self.buildbot.insert_source_stamp_to_db(**ss_params)
    defer.returnValue(ssid)

  @defer.inlineCallbacks
  def get_source_stamp(self, buildbucket_changes, cache=None):
    """Returns a new or existing SourceStamp for the list of changes.

    Returns:
      SourceStamp ID as Deferred.
    """
    assert isinstance(buildbucket_changes, list)
    if cache is not None and all('id' in c for c in buildbucket_changes):
      cache_key = tuple(sorted([c['id'] for c in buildbucket_changes]))
      ssid = cache.get(cache_key)
      if ssid:
        defer.returnValue(ssid)
        return
    ssid = yield self._insert_source_stamp(buildbucket_changes)
    if cache is not None:
      cache[cache_key] = ssid
    defer.returnValue(ssid)
