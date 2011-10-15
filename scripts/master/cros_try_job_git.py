# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import tempfile

import buildbot
from twisted.python import log

from master import tryjob_git_poller
from master.try_job_base import TryJobBase

buildbot_0_8 = int(buildbot.version.split('.')[1]) >= 8
if buildbot_0_8:
  from master.try_job_base_bb8 import BadJobfile
else:
  from master.try_job_base_bb7 import BadJobfile

class CrOSTryJobGit(TryJobBase):
  """Poll a Git server to grab patches to try."""
  def __init__(self, name, pools, repo_url, properties=None):
    TryJobBase.__init__(self, name, pools, properties, None, None)
    self.repo_url = repo_url
    self.watcher = tryjob_git_poller.GitPoller(
        repourl=repo_url,
        workdir=tempfile.mkdtemp(prefix='gitpoller'),
        pollinterval=10)
    self.watcher.setServiceParent(self)

  def ParseJob(self, stuff_tuple):
    _, contents = stuff_tuple
    # TODO: item.partition if python > 2.5.
    options = dict(item.split('=') for item in contents.splitlines())
    log.msg('Tryjob dict:\n%s' % str(options))

    if not options.get('gerrit_patches', None):
      raise BadJobfile('No patches specified!')

    if not options.get('bot'):
      raise BadJobfile('No configs specified!')

    return TryJobBase.ParseJob(self, options)

  def get_props(self, options):
    base_props = TryJobBase.get_props(self, options)
    base_props.setProperty('gerrit_patches', options.get('gerrit_patches'),
                      'Scheduler')
    log.msg('props[clobber]=%s' % base_props.getProperty('clobber'))
    return base_props

  def addChange(self, change):
    """Process the received data and send the queue buildset."""
    # Implicitly skips over non-files like directories.
    if len(change.files) != 1:
      # We only accept changes with 1 diff file.
      log.msg("Tryjob with too many files %s" % (','.join(change.files)))
      return

    output = self.watcher.get_file_contents(change.files[0])
    log.msg('Tryjob contents:\n%s'  % output)
    self.SubmitJob((change.comments, output))
