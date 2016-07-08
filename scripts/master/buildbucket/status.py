# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.status import builder as build_results
from buildbot.status.base import StatusReceiverMultiService
from twisted.internet.defer import inlineCallbacks, returnValue

from . import common
from .buildbot_gateway import BuildbotGateway


BUILD_STATUS_NAMES = {
    build_results.EXCEPTION: 'EXCEPTION',
    build_results.FAILURE: 'FAILURE',
    build_results.RETRY: 'RETRY',
    build_results.SKIPPED: 'SKIPPED',
    build_results.SUCCESS: 'SUCCESS',
    build_results.WARNINGS: 'SUCCESS',  # Treat warnings as SUCCESS.
}


class BuildBucketStatus(StatusReceiverMultiService):
  """Updates build status on buildbucket."""

  def __init__(self, integrator, buildbucket_service, dry_run):
    """Creates a new BuildBucketStatus.

    Args:
      integrator (BuildBucketIntegrator): integrator to notify about status
        changes.
      buildbucket_service (DeferredResource): buildbucket API client.
      dry_run (bool): if True, do not start integrator.
    """
    StatusReceiverMultiService.__init__(self)
    self.integrator = integrator
    self.buildbucket_service = buildbucket_service
    self.dry_run = dry_run
    self.integrator_starting = None

  def startService(self):
    StatusReceiverMultiService.startService(self)
    if self.dry_run:
      return

    buildbot = BuildbotGateway(self.parent)
    self.integrator.start(buildbot, self.buildbucket_service)
    self.integrator.poll_builds()
    self.parent.getStatus().subscribe(self)

  def stopService(self):
    self.integrator.stop()
    StatusReceiverMultiService.stopService(self)

  # pylint: disable=W0613
  def builderAdded(self, name, builder):
    # Subscribe to this builder.
    return self

  def buildStarted(self, builder_name, build):
    if self.dry_run:
      return
    self.integrator.on_build_started(build)

  def buildFinished(self, builder_name, build, result):
    if self.dry_run:
      return
    assert result in BUILD_STATUS_NAMES
    status = BUILD_STATUS_NAMES[result]
    self.integrator.on_build_finished(build, status)
