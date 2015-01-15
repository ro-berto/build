# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This file encapsulates most of buildbot API for BuildBucketIntegrator."""

from buildbot.changes.changes import Change
from buildbot.interfaces import IControl
from buildbot.master import Control
from buildbot.status import builder as build_results
from twisted.internet.defer import inlineCallbacks, returnValue
import sqlalchemy as sa


class BuildbotGateway(object):
  """All buildbot APIs needed by BuildBucketIntegrator to function.

  Handy to mock.
  """

  def __init__(self, master):
    """Creates a BuildbotGateway.

    Args:
      master (buildbot.master.BuildMaster): the buildbot master.
    """
    assert master, 'master not specified'
    self.master = master

  def find_changes_by_revision(self, revision):
    """Searches for Changes in database by |revision| and returns change ids."""
    def find(conn):
      table = self.master.db.model.changes
      q = sa.select([table.c.changeid]).where(table.c.revision == revision)
      return [row.changeid for row in conn.execute(q)]
    return self.master.db.pool.do(find)

  @inlineCallbacks
  def get_change_by_id(self, change_id):
    """Returns buildot.changes.changes.Change as Deferred for |change_id|."""
    chdict = yield self.master.db.changes.getChange(change_id)
    change = yield Change.fromChdict(self.master, chdict)
    returnValue(change)

  def get_cache(self, name, miss_fn):
    """Returns a buildbot.util.lru.AsyncLRUCache by |name|.

    Args:
      name (str): cache name. If called twice with the same name, returns the
        same object.
      miss_fn (func): function cache_key -> value. Used on cache miss.
    """
    return self.master.caches.get_cache(name, miss_fn)

  def add_change_to_db(self, **kwargs):
    """Adds a change to buildbot database.

    See buildbot.db.changes.ChangesConnectorComponent.addChange for arguments.
    """
    return self.master.db.changes.addChange(**kwargs)

  def insert_source_stamp_to_db(self, **kwargs):
    """Inserts a SourceStamp to buildbot database.

    See buildbot.db.sourcestamps.SourceStampsConnectorComponent.addSourceStamp
    for arguments.
    """
    return self.master.db.sourcestamps.addSourceStamp(**kwargs)

  def add_buildset(self, **kwargs):
    """Adds a Buildset to buildbot database.

    See buildbot.master.BuildMaster.addBuildset for arguments.
    """
    return self.master.addBuildset(**kwargs)

  def get_builders(self):
    """Returns a map of builderName -> buildbot.status.builder.BuilderStatus."""
    status = self.master.getStatus()
    names = status.getBuilderNames()
    return {name:status.getBuilder(name) for name in names}

  @staticmethod
  def is_slave_available(slave):
    """Returns True is slave is available to start a build. Otherwise False."""
    return slave.isConnected() and not slave.getRunningBuilds()

  def get_slaves(self):
    """Returns a list of all slaves.

    Returns:
      A list of buildbot.status.slave.SlaveStatus.
    """
    status = self.master.getStatus()
    return map(status.getSlave, status.getSlaveNames())

  def get_available_slaves(self):
    """Returns a list of all available slaves.

    Returns:
      A list of buildbot.status.slave.SlaveStatus.
    """
    return filter(self.is_slave_available, self.get_slaves())

  def get_build_url(self, build):
    """Returns a URL for the |build|."""
    return self.master.getStatus().getURLForThing(build)

  def stop_build(self, build, reason):
    """Stops the |build|."""
    control = Control(self.master)
    builder_control = control.getBuilder(build.getBuilder().getName())
    assert builder_control
    build_control = builder_control.getBuild(build.getNumber())
    assert build_control
    build_control.stopBuild(reason)
