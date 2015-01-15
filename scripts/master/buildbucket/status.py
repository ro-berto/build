# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.status import builder as build_results
from buildbot.status.base import StatusReceiverMultiService
from master.buildbucket.integration import BUILD_ETA_UPDATE_INTERVAL
from twisted.internet.defer import inlineCallbacks, returnValue


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

  def __init__(self, integrator):
    StatusReceiverMultiService.__init__(self)
    self.integrator = integrator

  def startService(self):
    StatusReceiverMultiService.startService(self)
    self.parent.getStatus().subscribe(self)

  # pylint: disable=W0613
  def builderAdded(self, name, builder):
    # Subscribe to this builder.
    return self

  def buildStarted(self, builder_name, build):
    if not self.integrator.is_buildbucket_build(build):
      return None

    self.integrator.on_build_started(build)
    # Tell Buildbot to call self.buildETAUpdate every 10 seconds.
    return (self, BUILD_ETA_UPDATE_INTERVAL.total_seconds())

  def buildETAUpdate(self, build, eta_seconds):
    self.integrator.on_build_eta_update(build, eta_seconds)

  def buildFinished(self, builder_name, build, result):
    assert result in BUILD_STATUS_NAMES
    status = BUILD_STATUS_NAMES[result]
    self.integrator.on_build_finished(build, status)
