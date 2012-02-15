# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil

from twisted.internet import defer, utils
from twisted.python import log

import master.cros_builder_mapping as builder_mapping
from master.try_job_base import BadJobfile, TryJobBase, text_to_dict


def validate_job(parsed_job):
  if not parsed_job.get('gerrit_patches'):
    if not parsed_job['issue']:
      raise BadJobfile('No patches specified!')
  elif parsed_job['issue']:
    raise BadJobfile('Both issue and gerrit_patches specified!')

  if not parsed_job.get('bot'):
    raise BadJobfile('No configs specified!')
  else:
    for bot in parsed_job['bot']:
      if not builder_mapping.CONFIG_NAME_DICT.get(bot):
        raise BadJobfile('Invalid config %s specified' % bot)


class CrOSTryJobGit(TryJobBase):
  """Poll a Git server to grab patches to try."""
  def __init__(self, name, pools, poller, properties=None):
    TryJobBase.__init__(self, name, pools, properties, None, None)
    self.watcher = poller

  def startService(self):
    TryJobBase.startService(self)
    self.startConsumingChanges()

  def stopService(self):
    def rm_temp_dir(result):
      if os.path.isdir(self.watcher.workdir):
        shutil.rmtree(self.watcher.workdir)

    d = TryJobBase.stopService(self)
    d.addCallback(rm_temp_dir)
    d.addErrback(log.err)
    return d

  def get_props(self, bot, options):
    """Overriding base class method."""
    props = TryJobBase.get_props(self, bot, options)
    props.setProperty('gerrit_patches', ','.join(options['gerrit_patches']),
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
          builderNames=[builder_mapping.CONFIG_NAME_DICT[bot]],
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
    parsed = self.parse_options(text_to_dict(wfd.getResult()))
    # ChromeOS trybots pull the patch directly from Gerrit.
    parsed['patch'] = ''
    validate_job(parsed)
    self.SubmitJob(parsed, [change.number])
