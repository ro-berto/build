# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.base import PollingChangeSource
from buildbot.util import deferredLocked
from twisted.internet import defer, utils
from twisted.python import log

import os
import shutil


class GitBranchPoller(PollingChangeSource):
  """Polls multiple branches in a git repository."""

  def __init__(self, repo_url, branches, pollInterval=60, revlinktmpl='',
               workdir='git_poller', verbose=False):
    """Initializes a new instance of the GitBranchPoller class.

    Args:
      repo_url: URL of the remote repository.
      branches: List of branches in the remote repository to track.
      pollInterval: Number of seconds between polling operations.
      revlinktmpl: String template, taking a single string parameter,
        used to generate a web link to a revision.
      workdir: Working directory for the poller to use.
      verbose: Emit actual git commands and their raw results.
    """
    self.repo_url = repo_url
    assert branches, 'GitBranchPoller: at least one branch is required'
    self.branches = branches
    self.pollInterval = pollInterval
    self.revlinktmpl = revlinktmpl
    self.workdir = os.path.abspath(workdir)
    self.verbose = verbose

    if not os.path.exists(self.workdir):
      self._log('Creating working directory:', self.workdir)
      os.makedirs(self.workdir)
    else:
      self._log('Using existing working directory:', self.workdir)

    # Mapping of branch names to the latest observed revision.
    self.branch_heads = {branch: None for branch in branches}
    self.branch_heads_lock = defer.DeferredLock()

  @deferredLocked('branch_heads_lock')
  @defer.inlineCallbacks
  def startService(self):
    def stop(err):
      self._log('Failed to initialize revision history for', self.repo_url)

      # In verbose mode, stderr has already been emitted.
      if not self.verbose and err.rstrip():
        self._log('stderr:\n%s' % err.rstrip())

      return self.stopService()

    self._log('Initializing revision history of', self.repo_url)

    out, err, ret = yield self._git(
      'rev-parse', '--git-dir', '--is-bare-repository')
    out = out.splitlines()

    # Git commands are executed from inside the working directory, meaning
    # that relative to where the command was executed, --git-dir should be ".".
    if ret or len(out) != 2 or out[0] != '.' or out[1] != 'true':
      self._log('Working directory did not contain a mirrored repository')
      shutil.rmtree(self.workdir)
      os.makedirs(self.workdir)
      should_clone = True
    else:
      should_clone = False

    if should_clone:
      self._log('Cloning mirror of', self.repo_url)
      out, err, ret = yield self._git('clone', '--mirror', self.repo_url, '.')
      if ret:
        yield stop(err)
        return

    yield self._log('Fetching origin for', self.repo_url)
    out, err, ret = yield self._git('fetch', 'origin')
    if ret:
      yield stop(err)
      return

    for branch in self.branch_heads:
      out, err, ret = yield self._git('rev-parse', branch)
      if ret:
        yield stop(err)
      self._log(branch, 'at', out.rstrip())
      self.branch_heads[branch] = out.rstrip()

    yield PollingChangeSource.startService(self)

  @deferredLocked('branch_heads_lock')
  @defer.inlineCallbacks
  def poll(self):
    def log_error(err, ret):
      if ret:
        self._log('Polling', self.repo_url, 'failed, retrying in',
                  self.pollInterval, 'seconds')
        # In verbose mode, stderr has already been emitted.
        if not self.verbose and err.rstrip():
          self._log('stderr:\n%s' % err.rstrip())

      return ret

    self._log('Polling', self.repo_url)
    out, err, ret = yield self._git('fetch', 'origin')
    if log_error(err, ret):
      return

    args = []
    revision_branch_map = {}
    new_branch_heads = {}

    for branch, head in self.branch_heads.iteritems():
      args.append('%s..%s' % (head, branch))
      out, err, ret = yield self._git('rev-list', args[-1])
      if log_error(err, ret):
        return
      revisions = out.splitlines()

      if revisions:
        self._log(branch, 'at', revisions[0])
        new_branch_heads[branch] = revisions[0]

        for revision in revisions:
          revision_branch_map[revision] = branch
      else:
        self._log('No new revisions for', branch)

    if not revision_branch_map:
      return

    self._log('Determining total ordering of revisions')
    out, err, ret = yield self._git('rev-list', '--date-order', *args)
    if log_error(err, ret):
      return

    change_data = {revision: {} for revision in out.splitlines()}

    # Accumulate data to be sent to the master from earliest to latest revision.
    for revision in reversed(out.splitlines()):
      if revision not in revision_branch_map:
        self._log('Saw unexpected revision:', revision)
        continue

      self._log('Retrieving commit info for', revision, 'on',
                revision_branch_map[revision])

      out, err, ret = yield self._git(
        'show', r'--format=%ae', '--quiet', revision)
      if log_error(err, ret):
        return
      change_data[revision]['author'] = out.rstrip()

      out, err, ret = yield self._git(
        'show', r'--format=%ct', '--quiet', revision)
      if log_error(err, ret):
        return
      change_data[revision]['timestamp'] = out.rstrip()

      out, err, ret = yield self._git(
        'show', r'--format=%B', '--quiet', revision)
      if log_error(err, ret):
        return
      change_data[revision]['description'] = out.rstrip()

      out, err, ret = yield self._git(
        'diff-tree', '--name-only', '--no-commit-id', '-r', revision)
      if log_error(err, ret):
        return
      change_data[revision]['files'] = out.splitlines()

    for revision in change_data:
      try:
        yield self.master.addChange(
          author=change_data[revision]['author'],
          branch=revision_branch_map[revision],
          comments=change_data[revision]['description'],
          files=change_data[revision]['files'],
          repository=self.repo_url,
          revision=revision,
          revlink=self.revlinktmpl % revision,
          when_timestamp=change_data[revision]['timestamp'],
        )
      except Exception as e:
        log_error(str(e), 1)
        return

    # Now that all git operations have succeeded and the poll is complete,
    # update our view of the branch heads.
    self.branch_heads.update(new_branch_heads)

  @defer.inlineCallbacks
  def _git(self, *args):
    out, err, ret = yield utils.getProcessOutputAndValue(
      'git', args, path=self.workdir)

    if self.verbose:
      self._log('git', *args)
      if out.rstrip():
        self._log('stdout:\n%s' % out.rstrip())
      if err.rstrip():
        self._log('stderr:\n%s' % err.rstrip())
      if ret:
        self._log('retcode:', ret)

    defer.returnValue((out, err, ret))

  def _log(self, *args):
    log.msg('%s:' % self.__class__.__name__, *args)

  def describe(self):
    return '%s%s: polling: %s, watching branches: %s' % (
      self.__class__.__name__,
      '' if self.master else '[STOPPED (refer to log)]',
      self.repo_url,
      ', '.join(self.branches),
    )
