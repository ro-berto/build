# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urllib

from buildbot.changes import svnpoller
from twisted.internet import defer
from twisted.python import log

from master.try_job_base import BadJobfile, TryJobBase


class SVNPoller(svnpoller.SVNPoller):
  @defer.deferredGenerator
  def submit_changes(self, changes):
    """Instead of submitting the changes to the master, pass them to
    TryJobSubversion. We don't want buildbot to see these changes.
    """
    for chdict in changes:
      # TODO(maruel): Clean up to not parse two times, trap the exception.
      parsed = {'email': None}
      good = False
      try:
        # pylint: disable=E1101
        options = dict(
            item.split('=', 1) for item in chdict['comments'].splitlines()
            if '=' in item)
        parsed = self.parent.parse_options(options)
        good = True
      except (TypeError, ValueError):
        raise BadJobfile('Failed to parse the metadata')

      # 'fix' revision.
      # pylint: disable=E1101
      wfd = defer.waitForDeferred(self.parent.get_lkgr(parsed))
      yield wfd
      wfd.getResult()

      wfd = defer.waitForDeferred(self.master.addChange(
        author=','.join(parsed['email']),
        revision=parsed['revision'],
        comments=''))
      yield wfd
      change = wfd.getResult()

      if good:
        # pylint: disable=E1101
        self.parent.addChangeInner(
            chdict['files'], parsed, change.number)


class TryJobSubversion(TryJobBase):
  """Poll a Subversion server to grab patches to try."""
  def __init__(self, name, pools, svn_url, properties=None,
               last_good_urls=None, code_review_sites=None):
    TryJobBase.__init__(self, name, pools, properties,
                        last_good_urls, code_review_sites)
    self.svn_url = svn_url
    self.watcher = SVNPoller(svnurl=svn_url, pollinterval=10)

  def setServiceParent(self, parent):
    TryJobBase.setServiceParent(self, parent)
    self.watcher.setServiceParent(self)
    self.watcher.master = self.master

  def addChange(self, change):
    """Used in Buildbot 0.7.12."""
    try:
      options = dict(
          item.split('=', 1) for item in change.comments.splitlines()
          if '=' in item)
      parsed = self.parse_options(options)
    except (TypeError, ValueError):
      raise BadJobfile('Failed to parse the metadata')
    return self.addChangeInner(change.files, parsed, None)

  def addChangeInner(self, files, options, changeid):
    """Process the received data and send the queue buildset."""
    # Implicitly skips over non-files like directories.
    diffs = [f for f in files if f.endswith(".diff")]
    if len(diffs) != 1:
      # We only accept changes with 1 diff file.
      log.msg("Svn try with too many files %s" % (','.join(files)))
      return

    command = ['cat', self.svn_url + '/' + urllib.quote(diffs[0]),
        '--non-interactive']
    deferred = self.watcher.getProcessOutput(command)
    deferred.addCallback(
        lambda output: self._OnDiffReceived(options, output, changeid))
    return deferred

  def _OnDiffReceived(self, options, diff_content, changeid):
    log.msg(options)
    options['patch'] = diff_content
    return self.SubmitJob(options, [changeid])
