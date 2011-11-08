# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import tempfile

from twisted.internet import defer, utils

from master.try_job_base import buildbot_0_8, BadJobfile, TryJobBase

if buildbot_0_8:
  from buildbot.changes.gitpoller import GitPoller
else:
  from master.tryjob_git_poller import GitPoller


class CrOSTryJobGit(TryJobBase):
  """Poll a Git server to grab patches to try."""
  def __init__(self, name, pools, repo_url, properties=None):
    TryJobBase.__init__(self, name, pools, properties, None, None)
    self.repo_url = repo_url
    self.watcher = GitPoller(
        repourl=repo_url,
        workdir=tempfile.mkdtemp(prefix='gitpoller'),
        pollinterval=10)
    self.watcher.setServiceParent(self)

  def ParseJob(self, stuff_tuple):
    _, contents = stuff_tuple
    options = dict(item.split('=') for item in contents.splitlines())
    return TryJobBase.ParseJob(self, options)

  def get_file_contents(self, file_path):
    """Returns a Deferred to returns the file's content."""
    return utils.getProcessOutput(
        self.watcher.gitbin,
        ['show', 'FETCH_HEAD:%s' % file_path],
        path=self.watcher.workdir)

  @defer.deferredGenerator
  def addChange(self, change):
    """Process the received data and send the queue buildset."""
    # Implicitly skips over non-files like directories.
    if len(change.files) != 1:
      # We only accept changes with 1 diff file.
      raise BadJobfile(
          'Try job with too many files %s' % (','.join(change.files)))

    wfd = defer.waitForDeferred(self.get_file_contents(change.files[0]))
    yield wfd
    # This is technically wrong, will be fixed in next change.
    self.SubmitJob((change.comments, wfd.getResult()))
