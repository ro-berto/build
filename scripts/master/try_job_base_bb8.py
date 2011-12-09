# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from twisted.python import log
from twisted.web import client

from buildbot.schedulers.trysched import TryBase  # pylint: disable=W0611
from buildbot.schedulers.trysched import BadJobfile  # pylint: disable=W0611
from twisted.internet import defer


class TryJobBaseMixIn:
  _last_lkgr = None

  def __init__(self):
    pass

  def SubmitJob(self, parsed_job, changeids):
    if not parsed_job['bot']:
      raise BadJobfile(
          'incoming Try job did not specify any allowed builder names')

    d = self.master.db.sourcestamps.addSourceStamp(
        branch=parsed_job['branch'],
        revision=parsed_job['revision'],
        patch_body=parsed_job['patch'],
        patch_level=parsed_job['patchlevel'],
        patch_subdir=parsed_job['root'],
        project=parsed_job['project'],
        repository=parsed_job['repository'] or '',
        changeids=changeids)
    def create_buildset(ssid):
      log.msg('Creating try job %s' % ssid)
      return self.addBuildsetForSourceStamp(ssid=ssid,
          reason=parsed_job['name'],
          external_idstring=parsed_job['name'],
          builderNames=parsed_job['bot'],
          properties=self.get_props(parsed_job))
    d.addCallback(create_buildset)
    d.addErrback(log.err, "Failed to queue a try job!")
    return d

  def get_lkgr(self, options):
    """Grabs last known good revision number if necessary."""
    options['rietveld'] = (self.code_review_sites or {}).get(options['project'])
    last_good_url = (self.last_good_urls or {}).get(options['project'])
    if options['revision'] or not last_good_url:
      return defer.succeed(0)

    def Success(result):
      try:
        new_value = int(result.strip())
      except (TypeError, ValueError):
        new_value = None
      if new_value and (not self._last_lkgr or new_value > self._last_lkgr):
        self._last_lkgr = new_value
      options['revision'] = self._last_lkgr or 'HEAD'

    def Failure(result):
      options['revision'] = self._last_lkgr or 'HEAD'

    connection = client.getPage(last_good_url, agent='buildbot')
    connection.addCallbacks(Success, Failure)
    return connection
