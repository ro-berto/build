# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re

from twisted.internet import defer
from twisted.python import log

from buildbot.schedulers.base import BaseScheduler

from master.gerrit_poller import GerritPoller


class JobDefinition(object):
  """Describes a try job posted on Gerrit."""
  def __init__(self, builder_names=None):
    # Force str type and remove empty builder names.
    self.builder_names = [str(b) for b in (builder_names or []) if b]

  def __repr__(self):
    return repr(self.__dict__)

  @staticmethod
  def parse(text):
    """Parses a try job definition."""
    text = text and text.strip()
    if not text:
      # Return an empty definition.
      return JobDefinition()

    # Parse as json.
    try:
      job = json.loads(text)
    except:
      raise ValueError('Couldn\'t parse job definition: %s' % text)

    # Convert to canonical form.
    if isinstance(job, list):
      # Treat a list as builder name list.
      job = {'builderNames': job}
    elif not isinstance(job, dict):
      raise ValueError('Job definition must be a JSON object or array.')

    return JobDefinition(job.get('builderNames'))


class _TryJobGerritPoller(GerritPoller):
  """Polls issues, creates changes and calls scheduler.submitJob.

  This class is a part of TryJobGerritScheduler implementation and not designed
  to be used otherwise.
  """

  change_category = 'tryjob'

  MESSAGE_REGEX_TRYJOB = re.compile('!tryjob(.*)$', re.I)

  def __init__(self, scheduler, gerrit_host, gerrit_projects=None,
               pollInterval=None):
    assert scheduler
    GerritPoller.__init__(self, gerrit_host, gerrit_projects, pollInterval)
    self.scheduler = scheduler

  def _is_interesting_message(self, message):
    return self.MESSAGE_REGEX_TRYJOB.search(message['message'])

  def getChangeQuery(self):
    query = GerritPoller.getChangeQuery(self)
    # Request only issues with TryJob=+1 label.
    query += '+label:TryJob=%2B1'
    return query

  def parseJob(self, message):
    """Parses a JobDefinition from a Gerrit message."""
    tryjob_match = self.MESSAGE_REGEX_TRYJOB.search(message['message'])
    assert tryjob_match
    return JobDefinition.parse(tryjob_match.group(1))

  @defer.inlineCallbacks
  def addChange(self, change, message):
    """Parses a job, adds a change and calls self.scheduler.submitJob."""
    try:
      job = self.parseJob(message)
      buildbotChange = yield self.addBuildbotChange(change, message)
      yield self.scheduler.submitJob(buildbotChange, job)
      defer.returnValue(buildbotChange)
    except Exception as e:
      log.err('TryJobGerritPoller failed: %s' % e)
      raise


class TryJobGerritScheduler(BaseScheduler):
  """Polls try jobs on Gerrit and creates buildsets."""
  def __init__(self, name, default_builder_names, gerrit_host,
               gerrit_projects=None, pollInterval=None):
    """Creates a new TryJobGerritScheduler.

    Args:
        name: name of the scheduler.
        default_builder_names: a list of builder names used in case a job didn't
            specify any.
        gerrit_host: URL to the Gerrit instance
        gerrit_projects: Gerrit projects to filter issues.
        pollInterval: frequency of polling.
    """
    BaseScheduler.__init__(self, name,
                           builderNames=default_builder_names,
                           properties={})
    self.poller = _TryJobGerritPoller(self, gerrit_host, gerrit_projects,
                                      pollInterval)

  def setServiceParent(self, parent):
    BaseScheduler.setServiceParent(self, parent)
    self.poller.master = self.master
    self.poller.setServiceParent(self)

  def gotChange(self, *args, **kwargs):
    """Do nothing because changes are processed by submitJob."""

  @defer.inlineCallbacks
  def submitJob(self, change, job):
    bsid = yield self.addBuildsetForChanges(
        reason='tryjob',
        changeids=[change.number],
        builderNames=job.builder_names,
        properties=change.properties)
    log.msg('Successfully submitted a Gerrit try job for %s: %s.' %
            (change.who, job))
    defer.returnValue(bsid)
