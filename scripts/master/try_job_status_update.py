# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Listens to try jobs and update the code review site."""

import urllib

from buildbot.status.builder import FAILURE, SKIPPED, SUCCESS, WARNINGS
from buildbot.status import base
from twisted.python import log
from twisted.web import client

from master import get_password
from master.try_job_stamp import TryJobStamp


class TryJobStatusUpdate(base.StatusReceiverMultiService):
  """Status notifier which updates the code review status."""
  def __init__(self, important_steps):
    # The status object we must subscribe to.
    base.StatusReceiverMultiService.__init__(self)
    self.status = None
    # The steps we care about. Note that this shouldn't be more than what lkgr
    # (goodrevision.py) is using as the signal reference.
    self.important_steps = important_steps
    self.password = get_password.Password('.code_review_password'
        ).GetPassword()

  def setServiceParent(self, parent):
    base.StatusReceiverMultiService.setServiceParent(self, parent)
    self.setup()

  def setup(self):
    # pylint: disable=E1101
    self.status = self.parent.getStatus()
    self.status.subscribe(self)

  def disownServiceParent(self):
    self.status.unsubscribe(self)
    # pylint: disable=E1101
    for w in self.watched:
      w.unsubscribe(self)
    return base.StatusReceiverMultiService.disownServiceParent(self)

  def builderAdded(self, name, builder):
    """A builder has connected, registers to it."""
    return self

  def buildStarted(self, name, build):
    """A build has started allowing us to register for stepFinished."""
    self.UpdateCodeView(build, None, [SUCCESS, []])
    return self

  def stepFinished(self, build, step, results):
    self.UpdateCodeView(build, step, results)

  def buildFinished(self, name, build, results):
    # A single failure in the run marks the whole run as failed. That's not
    # what we want.
    self.UpdateCodeView(build, None, [SUCCESS, []])

  def UpdateCodeView(self, build, step, results):
    """Look if something interesting happened. Is it worth to update the code
    review site?

    build is of type BuildStatus."""
    job_stamp = build.getSourceStamp()
    if isinstance(job_stamp, TryJobStamp):
      # buildbot 0.7.12
      review_status_update_url = job_stamp.getCodeReviewStatusUrl()
    else:
      # buildbot 0.8.x
      try:
        review_status_update_url = build.getProperty('rietveld')
      except KeyError:
        review_status_update_url = None

    # We only care about it if it contains a patchset.
    if not review_status_update_url:
      return
    review_status_update_url = str(review_status_update_url)

    builder_name = build.getBuilder().getName()
    if not hasattr(job_stamp, 'results'):
      job_stamp.results = {}
    previous_result = job_stamp.results.get(builder_name)
    job_stamp.results.setdefault(builder_name, 'pending')

    # No need to update.
    if job_stamp.results[builder_name] == 'failure':
      return

    # Is None for a starting or a ending job.
    if step and self.important_steps:
      # Example of step.getText() value: ['unit_tests', '16 disabled']
      step_text = step.getText()[0]
      if not step_text in self.important_steps:
        # Non-important step.
        return

    # results[1] is an array of the steps that generated the status results[0].
    result = results[0]
    if result == FAILURE:
      job_stamp.results[builder_name] = 'failure'
    elif (result in (SUCCESS, WARNINGS, SKIPPED) and build.isFinished()):
      job_stamp.results[builder_name] = 'success'
    # else, it's already 'pending'.

    # The status didn't change. No need to update again.
    if previous_result == job_stamp.results[builder_name]:
      return

    details_url = (self.status.getBuildbotURL() +
                   "buildstatus?builder=%s&number=%d" % (builder_name,
                                                         build.getNumber()))
    self.PostData(builder_name,
                  job_stamp.results[builder_name],
                  review_status_update_url,
                  details_url)

  def PostData(self, builder_name, status, update_url, details_url):
    """Post the revision data to the server store."""
    params = {
      'platform_id': builder_name,
      'status': status,
      'details_url': details_url,
      'password': self.password,
    }
    # Trigger the HTTP POST request to update the tree status.
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    connection = client.getPage(update_url, method='POST',
                                postdata=urllib.urlencode(params),
                                headers=headers,
                                agent='buildbot')

    def Failure(result):
      log.msg('Failed to close the tree')

    connection.addErrback(Failure)
    return connection
