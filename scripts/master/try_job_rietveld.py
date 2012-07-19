# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import json
import time
import urllib
import urlparse

from buildbot.changes import base
from buildbot.schedulers.trysched import BadJobfile
from twisted.application import internet
from twisted.internet import defer
from twisted.python import log
from twisted.web import client

from master.try_job_base import TryJobBase


class _ValidUserPoller(internet.TimerService):
  """Check chromium-access for users allowed to send jobs from Rietveld.
  """
  # The name of the file that contains the password for authenticating
  # requests to chromium-access.
  _PWD_FILE = '.try_job_rietveld_password'

  def __init__(self, interval):
    """
    Args:
      interval: Interval used to poll chromium-access, in seconds.
    """
    internet.TimerService.__init__(self, interval, _ValidUserPoller._poll, self)
    self._users = frozenset()

  def contains(self, email):
    """Checks if the given email address is a valid user.

    Args:
      email: The email address to check against the internal list.

    Returns:
      True if the email address is allowed to send try jobs from rietveld.
    """
    return email in self._users

  # base.PollingChangeSource overrides:
  def _poll(self):
    """Polls for valid user names.

    Returns:
      A deferred objects to be called once the operation completes.
    """
    log.msg('ValidUserPoller._poll')
    d = defer.succeed(None)
    d.addCallback(self._GetUsers)
    d.addCallback(self._MakeSet)
    d.addErrback(log.err, 'error in ValidUserPoller')
    return d

  def _GetUsers(self, _):
    """Downloads list of valid users.

    Returns:
      A frozenset of string containing the email addresses of users allowed to
      send jobs from Rietveld.
    """
    try:
      pwd = open(self._PWD_FILE).readline().strip()
    except IOError:
      return frozenset([])

    now_string = str(int(time.time()))
    params = {
      'md5': hashlib.md5(pwd + now_string).hexdigest(),
      'time': now_string
    }
    return client.getPage('https://chromium-access.appspot.com/auto/users',
                          agent='buildbot',
                          method='POST',
                          postdata=urllib.urlencode(params))

  def _MakeSet(self, data):
    """Converts the input data string into a set of email addresses.
    """
    emails = (email.strip() for email in data.splitlines())
    self._users = frozenset(email for email in emails if email)


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
    self._valid_users = _ValidUserPoller(interval=12 * 60 * 60)
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
      if not self._valid_users.contains(job['user']):
        continue
      # Add the 'project' property to each job based on the project of this
      # instance.
      job['project'] = self._project
      # Add a 'bot' property which is a map of builder name to ?.
      job['bot'] = {job['builder']: None}
      # Set some default values for properties not needed for this job.
      job['patch'] = ''
      job['patchlevel'] = -1  # Ignored, but must be an integer
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
    self._valid_users.setServiceParent(self)
