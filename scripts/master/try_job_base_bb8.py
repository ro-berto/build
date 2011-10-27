# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from twisted.python import log

# TODO(maruel): Remove me once we're switched to 0.8.x
# pylint: disable=E0611,F0401
from buildbot.process.properties import Properties
from buildbot.schedulers.trysched import TryBase  # pylint: disable=W0611
from buildbot.schedulers.trysched import BadJobfile
from twisted.internet import defer


class TryJobBaseMixIn:
  def __init__(self):
    pass

  def SubmitJob(self, parsed_job, changeid):
    #try:
    #  parsed_job = self.parse_options(parsed_job)
    #except BadJobfile:
    #  log.msg(
    #    '%s reports a bad jobfile in %s' % (self, parsed_job.get('name')))
    #  log.err()
    #  return defer.succeed(None)
    # Only to be used if only a subset of builders are allowed to run try jobs.
    #parsed_job['bot'] = self.filterBuilderList(parsed_job['bot'])

    # Validate/fixup the builder names.
    if not parsed_job['bot']:
      log.msg('incoming Try job did not specify any allowed builder names')
      return defer.succeed(None)

    d = self.master.db.sourcestamps.addSourceStamp(
        branch=parsed_job['branch'],
        revision=parsed_job['revision'],
        patch_body=parsed_job['patch'],
        patch_level=parsed_job['patchlevel'],
        patch_subdir=parsed_job['root'],
        project=parsed_job['project'],
        repository=parsed_job['repository'] or '',
        changeids=[changeid])

    requested_props = Properties()
    properties = {
        'clobber': parsed_job['clobber'],
        'testfilters': parsed_job['testfilter'],
        'issue': parsed_job['issue'],
        'patchset': parsed_job['patchset'],
        'rietveld': parsed_job['rietveld'],
    }
    requested_props.update(properties, "try build")
    def create_buildset(ssid):
      log.msg('Creating try job %s' % ssid)
      return self.addBuildsetForSourceStamp(ssid=ssid,
          reason=parsed_job['name'],
          external_idstring=parsed_job['name'],
          builderNames=parsed_job['bot'],
          properties=requested_props)
    d.addCallback(create_buildset)
    d.addErrback(log.err, "Failed to queue a try job!")
