# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import shutil

from buildbot.process.properties import Properties
from buildbot.schedulers.trysched import TryBase
from twisted.internet import defer, utils
from twisted.python import log

from master.try_job_base import BadJobfile


def validate_job(parsed_job):
  # A dictionary containing required fields and their type.
  required = {'name' : basestring,
              'user' : basestring,
              'email' : list,
              'gerrit_patches' : list,
              'bot' : list}

  wrong = [
      field for field, f_type in required.iteritems()
      if not isinstance(parsed_job.get(field), f_type)
  ]

  if wrong:
    raise BadJobfile('Option(s) %s missing or of wrong type!'
                     % ','.join(wrong))


class CrOSTryJobGit(TryBase):
  """Poll a Git server to grab patches to try."""

  _PROPERTY_SOURCE = 'Try Job'

  def __init__(self, name, poller, properties=None):
    """Initialize the class.

    Arguments:
      name: See TryBase.__init__().
      poller: The git poller that is watching the job repo.
      properties: See TryBase.__init__()
    """
    TryBase.__init__(self, name, [], properties or {})
    self.watcher = poller

  def startService(self):
    TryBase.startService(self)
    self.startConsumingChanges()

  def stopService(self):
    def rm_temp_dir(result):
      if os.path.isdir(self.watcher.workdir):
        shutil.rmtree(self.watcher.workdir)

    d = TryBase.stopService(self)
    d.addCallback(rm_temp_dir)
    d.addErrback(log.err)
    return d

  def get_props(self, bot, options):
    """Overriding base class method."""
    props = Properties()
    props.setProperty('gerrit_patches', ' '.join(options['gerrit_patches']),
                      self._PROPERTY_SOURCE)
    props.setProperty('chromeos_config', bot, self._PROPERTY_SOURCE)
    return props

  def create_buildset(self, ssid, parsed_job):
    """Overriding base class method."""
    log.msg('Creating try job(s) %s' % ssid)
    result = None
    for bot in parsed_job['bot']:
      result = self.addBuildsetForSourceStamp(ssid=ssid,
          reason=parsed_job['name'],
          external_idstring=parsed_job['name'],
          builderNames=[bot],
          properties=self.get_props(bot, parsed_job))

    return result

  def get_file_contents(self, file_path):
    """Returns a Deferred to returns the file's content."""
    return utils.getProcessOutput(
        self.watcher.gitbin,
        ['show', 'FETCH_HEAD:%s' % file_path],
        path=self.watcher.workdir,
        )

  @defer.deferredGenerator
  def gotChange(self, change, important):
    """Process the received data and send the queue buildset."""
    # Implicitly skips over non-files like directories.
    if len(change.files) != 1:
      # We only accept changes with 1 diff file.
      raise BadJobfile(
          'Try job with too many files %s' % (','.join(change.files)))

    wfd = defer.waitForDeferred(self.get_file_contents(change.files[0]))
    yield wfd
    parsed = json.loads(wfd.getResult())
    validate_job(parsed)

    d = self.master.db.sourcestamps.addSourceStamp(
        branch=change.branch,
        revision=change.revision,
        project=change.project,
        repository=change.repository,
        changeids=[change.number])
    d.addCallback(self.create_buildset, parsed)
    d.addErrback(log.err, "Failed to queue a try job!")
