# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from datetime import timedelta

from buildbot.changes.base import PollingChangeSource
from twisted.internet.defer import inlineCallbacks, returnValue

from .buildbot_gateway import BuildbotGateway


class BuildBucketPoller(PollingChangeSource):
  """Polls builds scheduled by buildbucket service.

  Besides polling, BuildBucketPoller is responsible for starting/stopping
  BuildBucketIntegrator.
  """
  # Is it polling right now?
  _polling = False

  def __init__(self, integrator, buildbucket_service_factory,
               poll_interval=None, dry_run=None):
    """Creates a new BuildBucketPoller.

    Args:
      integrator (BuildBucketIntegrator): integrator to use for build
        scheduling.
      buildbucket_service_factory (function): returns a DeferredResource as
        Deferred that will be used to access buildbucket service API.
      poll_interval (int): frequency of polling, in seconds.
      dry_run (bool): if True, do not poll.
    """
    assert integrator
    if isinstance(poll_interval, timedelta):
      poll_interval = poll_interval.total_seconds()

    self.integrator = integrator
    self.buildbucket_service_factory = buildbucket_service_factory
    if poll_interval:
      self.pollInterval = poll_interval
    self.dry_run = dry_run

  @inlineCallbacks
  def _start_integrator(self):
    buildbucket_service = yield self.buildbucket_service_factory()
    buildbot = BuildbotGateway(self.master)
    self.integrator.start(buildbot, buildbucket_service)

  def startService(self):
    PollingChangeSource.startService(self)
    if not self.dry_run:
      d = self._start_integrator()
      # Once started, poll.
      d.addCallback(lambda _: self.poll())

  def stopService(self):
    self.integrator.stop()
    PollingChangeSource.stopService(self)

  @inlineCallbacks
  def poll(self):
    # Defend from running multiple polling processes
    # and running at all in dry_run mode.
    if not self._polling and self.integrator.started and not self.dry_run:
      self._polling = True
      try:
        yield self.integrator.poll_builds()
      finally:
        self._polling = False
