# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.status import builder as build_results
from buildbot.status.base import StatusReceiverMultiService
from master.crbuild.integration import BUILD_ETA_UPDATE_INTERVAL_SECONDS
from twisted.internet.defer import inlineCallbacks, returnValue

# Map (Buildbot-specific build result -> crbuild-specific build status)
BUILD_STATUS_NAMES = {
    build_results.SUCCESS: 'SUCCESS',
    build_results.EXCEPTION: 'EXCEPTION',
    build_results.FAILURE: 'FAILURE',
}


class CrbuildStatus(StatusReceiverMultiService):
  """Updates build status on crbuild."""

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
    if not self.integrator.is_crbuild_build(build):
      return None

    self.integrator.on_build_started(build)
    # Tell Buildbot to call self.buildETAUpdate every 10 seconds.
    return (self, BUILD_ETA_UPDATE_INTERVAL_SECONDS)

  def buildETAUpdate(self, build, eta_seconds):
    self.integrator.on_build_eta_update(build, eta_seconds)

  def buildFinished(self, builder_name, build, result):
    status = BUILD_STATUS_NAMES.get(result, 'EXCEPTION')
    self.integrator.on_build_finished(build, status)
