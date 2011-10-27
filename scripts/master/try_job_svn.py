# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urllib
import urllib2

from buildbot.changes import svnpoller
from twisted.internet import defer
from twisted.python import log

try:
  # pylint: disable=E0611
  from buildbot.scheduler import BadJobfile
except ImportError:
  from buildbot.schedulers.trysched import BadJobfile

from master.try_job_base import TryJobBase


class SVNPoller(svnpoller.SVNPoller):
  @defer.deferredGenerator
  def submit_changes(self, changes):
    """Instead of submitting the changes to the master, pass them to
    TryJobSubversion. We don't want buildbot to see these changes.

    Code used in Buildbot 0.8.x.
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
      except BadJobfile:
        log.msg('%s reports a bad jobfile in %s' % (self, chdict['revision']))
        log.err()

      # 'fix' revision.
      self.parent.get_lkgr(parsed)

      wfd = defer.waitForDeferred(self.master.addChange(
        author=','.join(parsed['email']),
        #revision=chdict['revision'],
        # OMG.
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
  last_lkgr = None

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
    return self.addChangeInner(change.files, change.comments, None)

  def addChangeInner(self, files, comments, changeid):
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
        lambda output: self._OnDiffReceived(comments, output, changeid))
    return deferred

  def _OnDiffReceived(self, comments, diff_content, changeid):
    if not isinstance(comments, dict):
      options = dict(
          item.split('=', 1) for item in comments.splitlines() if '=' in item)
    else:
      options = comments
    options['patch'] = diff_content
    return self.SubmitJob(options, changeid)

  def get_lkgr(self, options):
    # TODO(maruel): This code is not at the right place!!
    options['rietveld'] = (self.code_review_sites or {}).get(options['project'])
    last_good_url = (self.last_good_urls or {}).get(options['project'])
    if not options['revision'] and last_good_url:
      # Grab last known good revision number.
      # TODO(maruel): NOT SYNC!!!
      try:
        connection = urllib2.urlopen(last_good_url)
        self.last_lkgr = options['revision'] = int(connection.read().strip())
        connection.close()
      except (ValueError, IOError):
        options['revision'] = self.last_lkgr or 'HEAD'
