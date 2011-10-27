# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urllib

from buildbot.changes import svnpoller
from twisted.python import log

from master.try_job_base import TryJobBase


class TryJobSubversion(TryJobBase):
  """Poll a Subversion server to grab patches to try."""
  def __init__(self, name, pools, svn_url, properties=None,
               last_good_urls=None, code_review_sites=None):
    TryJobBase.__init__(self, name, pools, properties,
                        last_good_urls, code_review_sites)
    self.svn_url = svn_url
    self.watcher = svnpoller.SVNPoller(svnurl=svn_url, pollinterval=10)
    self.watcher.setServiceParent(self)

  def ParseJob(self, stuff_tuple):
    comment, diff = stuff_tuple
    # TODO: item.partition if python > 2.5.
    options = dict(item.split('=') for item in comment.splitlines())
    options['patch'] = diff
    return TryJobBase.ParseJob(self, options)

  def addChange(self, change):
    """Process the received data and send the queue buildset."""
    # Implicitly skips over non-files like directories.
    files = [f for f in change.files if f.endswith(".diff")]
    if len(files) != 1:
      # We only accept changes with 1 diff file.
      log.msg("Svn try with too many files %s" % (','.join(change.files)))
      return

    command = ['cat', self.svn_url + '/' + urllib.quote(files[0]),
        '--non-interactive']
    deferred = self.watcher.getProcessOutput(command)
    deferred.addCallback(lambda output: self._OnDiffReceived(change, output))

  def _OnDiffReceived(self, change, diff_content):
    # Send it as a tuple.
    self.SubmitJob((change.comments, diff_content))
