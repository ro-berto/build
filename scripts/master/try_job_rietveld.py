# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import urlparse

from buildbot.changes import base
from buildbot.schedulers.trysched import BadJobfile
from twisted.internet import defer
from twisted.python import log
from twisted.web import client

from master.try_job_base import TryJobBase


class _RietveldPoller(base.PollingChangeSource):
  """Polls Rietveld for any pending patch sets to build.

  Periodically polls Rietveld to see if any patch sets have been marked by
  users to be tried.  If so, send them to the trybots.
  """

  def __init__(self, get_pending_endpoint, interval):
    """
    Args:
      get_pending_endpoint: Rietveld URL string used to retrieve jobs to try.
      interval: Interval used to poll Rietveld, in seconds.
    """
    # Set interval time in base class.
    self.pollInterval = interval

    # A string URL for the Rietveld endpoint to query for pending try jobs.
    self._get_pending_endpoint = get_pending_endpoint

    # Cursor used to keep track of next patchset(s) to try.  If the cursor
    # is None, then try from the beginning.
    self._cursor = None

    # Try job parent of this poller.
    self._try_job_rietveld = None

  # base.PollingChangeSource overrides:
  def poll(self):
    """Polls Rietveld for any pending try jobs and submit them.

    Returns:
      A deferred objects to be called once the operation completes.
    """
    log.msg('RietveldPoller.poll')
    d = defer.succeed(None)
    d.addCallback(self._OpenUrl)
    d.addCallback(self._ParseJson)
    d.addErrback(log.err, 'error in RietveldPoller')  # eat errors
    return d

  def setServiceParent(self, parent):
    base.PollingChangeSource.setServiceParent(self, parent)
    self._try_job_rietveld = parent

  def _OpenUrl(self, _):
    """Downloads pending patch sets from Rietveld.

    Returns: A string containing the pending patchsets from Rietveld
        encoded as JSON.
    """
    endpoint = self._get_pending_endpoint
    if self._cursor:
      sep = '&' if '?' in endpoint else '?'
      endpoint = endpoint + '%scursor=%s' % (sep, self._cursor)

    log.msg('RietveldPoller._OpenUrl: %s' % endpoint)
    return client.getPage(endpoint, agent='buildbot')

  def _ParseJson(self, json_string):
    """Parses the JSON pending patch set information.

    Args:
      json_string: A string containing the serialized JSON jobs.

    Returns: A list of pending try jobs.  This is the list of all jobs returned
        by Rietveld, not simply the ones we tried this time.
    """
    data = json.loads(json_string)
    self._cursor = str(data['cursor'])
    self._try_job_rietveld.SubmitJobs(data['jobs'])


class TryJobRietveld(TryJobBase):
  """A try job source that gets jobs from pending Rietveld patch sets."""

  def __init__(self, name, pools, properties=None, last_good_urls=None,
               code_review_sites=None, project=None):
    """Creates a try job source for Rietveld patch sets.

    Args:
      name: Name of this scheduler.
      pools: No idea.
      properties: Extra build properties specific to this scheduler.
      last_good_urls: Dictionary of project to last known good build URL.
      code_review_sites: Dictionary of project to code review site.  This
          class care only about the 'chrome' project.
      project: The name of the project whose review site URL to extract.
          If the project is not found in the dictionary, an exception is raised.
    """
    TryJobBase.__init__(self, name, pools, properties,
                        last_good_urls, code_review_sites)
    endpoint = self._GetRietveldEndPointForProject(code_review_sites, project)
    self._poller = _RietveldPoller(endpoint, interval=10)
    self._project = project
    log.msg('TryJobRietveld created, get_pending_endpoint=%s '
            'project=%s' % (endpoint, project))

  @staticmethod
  def _GetRietveldEndPointForProject(code_review_sites, project):
    """Determines the correct endpoint for the chrome review site URL.

    Args:
      code_review_sites: Dictionary of project name to review site URL.
      project: The name of the project whose review site URL to extract.
          If the project is not found in the dictionary, an exception is raised.

    Returns: A string with the endpoint extracted from the chrome
        review site URL, which is the URL to poll for new patch
        sets to try.
    """
    if project not in code_review_sites:
      raise Exception('No review site for "%s"' % project)

    return urlparse.urljoin(code_review_sites[project],
                            'get_pending_try_patchsets?limit=100')

  def SubmitJobs(self, jobs):
    """Submit pending try jobs to slaves for building.

    Args:
      jobs: a list of jobs.  Each job is a dictionary of properties describing
          what to build.
    """
    log.msg('TryJobRietveld.SubmitJobs: %s' % json.dumps(jobs, indent=2))

    exceptions = []
    for job in jobs:
      if not job['user'].endswith('@chromium.org'):
        continue
      # Add the 'project' property to each job based on the project of this
      # instance.
      job['project'] = self._project
      # Add a 'bot' property which is a map of builder name to ?.
      job['bot'] = {job['builder']: None}
      # Set some default values for properties not needed for this job.
      job['patch'] = ''
      job['patchlevel'] = ''
      job['branch'] = None
      job['repository'] = None
      job['try_job_key'] = job['key']

      try:
        self.SubmitJob(job, None)
      except BadJobfile, ex:
        exceptions.append(ex)

    for ex in exceptions:
      log.msg(ex)

  # TryJobBase overrides:
  def setServiceParent(self, parent):
    TryJobBase.setServiceParent(self, parent)
    self._poller.setServiceParent(self)
    self._poller.master = self.master
