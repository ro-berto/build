# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes import gitpoller
from buildbot.util import deferredLocked
from twisted.python import log
from twisted.internet import defer, utils

import os

class ChromiumGitPoller(gitpoller.GitPoller):
  """A git poller which keeps track of commit tag order.
  This class has the same outward behavior as GitPoller, but it also keeps
  track of the commit order of git tags.  The tagcmp method can be used as a
  comparator function when comparing git tags."""

  def __init__(self, *args, **kwargs):
    gitpoller.GitPoller.__init__(self, *args, **kwargs)
    self.tag_order = []
    self.tag_lookup = {}

  def _parse_history(self, res):
    """Populate two data structures from the repo log:
         self.tag_order is an in-order list of all commit tags in the repo.
         self.tag_lookup maps tags to their index in self.tag_order."""
    new_history = [line[0:40] for line in res[0].splitlines()]
    log.msg("Parsing %d new git tags" % len(new_history))
    new_history.reverse()  # We want earliest -> latest
    old_len = len(self.tag_order)
    self.tag_order.extend(new_history)
    for i, value in enumerate(new_history):
      self.tag_lookup[value] = old_len + i

  @deferredLocked('initLock')
  def _init_history(self, _):
    """Initialize tag order data from an existing git checkout.
    This is invoked once, when the git poller is started."""
    log.msg('ChromiumGitPoller: initializing revision history')
    d = utils.getProcessOutputAndValue(
        self.gitbin,
        ['log', 'origin/%s' % self.branch, r'--format=%H'],
        path=self.workdir, env=dict(PATH=os.environ['PATH']))
    d.addCallback(self._convert_nonzero_to_failure)
    d.addErrback(self._stop_on_failure)
    d.addCallback(self._parse_history)
    return d

  def _process_history(self, res):
    """Add new git commits to the tag order data.
    This is called every time the poller detects new changes."""
    d = utils.getProcessOutputAndValue(
      self.gitbin,
      ['log', '%s..origin/%s' % (self.branch, self.branch), r'--format=%H'],
      path=self.workdir, env=dict(PATH=os.environ['PATH']))
    d.addCallback(self._convert_nonzero_to_failure)
    d.addErrback(self._stop_on_failure)
    d.addCallback(self._parse_history)
    return d

  @staticmethod
  def _process_history_failure(res):
    log.msg('ChromiumGitPoller: repo log failed')
    log.err(res)
    return None

  def tagcmp(self, x, y):
    """A general-purpose sorting comparator for git tags
    based on commit order."""
    try:
      return cmp(self.tag_lookup[x], self.tag_lookup[y])
    except KeyError, e:
      msg = 'ChromiumGitPoller doesn\'t know anything about git tag %s' % str(e)
      raise RuntimeError(msg)

  def startService(self):
    gitpoller.GitPoller.startService(self)
    d = defer.succeed(None)
    d.addCallback(self._init_history)

  @deferredLocked('initLock')
  def poll(self):
    d = self._get_changes()
    d.addCallback(self._process_history)
    d.addErrback(ChromiumGitPoller._process_history_failure)
    d.addCallback(self._process_changes)
    d.addErrback(self._process_changes_failure)
    d.addCallback(self._catch_up)
    d.addErrback(self._catch_up_failure)
    return d
