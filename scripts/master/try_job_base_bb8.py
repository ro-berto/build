# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from twisted.python import log

from buildbot.schedulers.trysched import TryBase  # pylint: disable=W0611
from buildbot.schedulers.trysched import BadJobfile
from twisted.internet import defer


class TryJobBaseMixIn:
  def __init__(self):
    pass

  def SubmitJob(self, parsed_job):
    try:
      parsed_job = self.parse_options(parsed_job)
    except BadJobfile:
      log.msg(
        '%s reports a bad jobfile in %s' % (self, parsed_job.get('name')))
      log.err()
      return defer.succeed(None)
    parsed_job['bot'] = self.filterBuilderList(parsed_job['bot'])

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
        repository=parsed_job['repository'] or '')
    def create_buildset(ssid):
      log.msg('Creating try job %s' % ssid)
      return self.addBuildsetForSourceStamp(ssid=ssid,
          reason=parsed_job['name'],
          external_idstring=parsed_job['name'],
          builderNames=parsed_job['bot'],
          properties=self.get_props(parsed_job))
    d.addCallback(create_buildset)
    d.addErrback(log.err, "Failed to queue a try job!")
