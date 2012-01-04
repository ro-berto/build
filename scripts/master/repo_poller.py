# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import tempfile
import urllib

from twisted.internet import defer, utils
from twisted.python import log
from buildbot.changes.base import PollingChangeSource
from buildbot.util import deferredLocked, epoch2datetime

from master.chromium_git_poller_bb8 import GitTagComparator

def ConvertNonZeroToFailure(res):
  """Callback for twisted.internet.utils.getProcessOutputAndValue"""
  (stdout, stderr, code) = res
  if code != 0:
    raise RuntimeError('command failed with exit code %d: %s' % (code, stderr))
  return (stdout, stderr, code)


class RepoTagComparator(GitTagComparator):
  """Maintains a canonical ordering of commits across multiple git repos."""

  def addRevision(self, revision):
    """Unlike GitTagComparator, don't assert(revision not in self.tag_lookup);
    that can legitimately happen if two repos share common history."""
    self.tag_lookup[revision] = len(self.tag_order)
    self.tag_order.append(revision)


class RepoPoller(PollingChangeSource):
  """Polls a repo meta-repository and submits buildbot changes.

  repo is a layer over git that provides support for projects that span multiple
  git repositories.  This poller discovers changes in all of the underlying git
  repositories, and turns them into buildbot master changes.

  Buildbot doesn't provide very good support out of the box for displaying
  changes from multiple git repositories on a single console.  The biggest
  obstacle is that there is no inherent canonical ordering of commits across
  multiple independent repositories.

  This class addresses that by applying and enforcing an arbitrary (but
  generally useful) canonical ordering.  Changes in the git repositories are
  ordered by timestamp first (with one-second granularity).  In the event of
  collisions, ordering falls back to alphabetical ordering by repository name.
  """

  def __init__(self, repo_url, repo_branch=None, workdir=None,
               pollInterval=5*60, repo_bin='repo', git_bin='git',
               category='', project='', revlinktmpl=None,
               encoding='utf-8'):
    if not workdir:
      workdir = tempfile.mkdtemp(prefix='repo_poller')
      log.msg('RepoPoller: using new working dir %s' % workdir)

    self.repo_url = repo_url
    self.repo_branch = repo_branch
    self.workdir = workdir
    self.pollInterval = pollInterval
    self.repo_bin = repo_bin
    self.git_bin = git_bin
    self.category = category
    self.project = project
    self.revlinktmpl = revlinktmpl
    self.encoding = encoding
    self.initLock = defer.DeferredLock()
    self.comparator = RepoTagComparator()
    self.changeCount = 0

  def startService(self):
    if not os.path.isabs(self.workdir):
      self.workdir = os.path.join(self.master.basedir, self.workdir)
      log.msg('RepoPoller: using workdir "%s"' % self.workdir)

    if not os.path.exists(os.path.join(self.workdir, '.repo')):
      d = self.initRepository()
      d.addErrback(log.err, 'while initializing RepoPoller repository')
    else:
      d = defer.succeed(None)
      log.msg('RepoPoller: using pre-existing repo checkout.')

    d.addCallback(self.initHistory)
    def _comparator_initialized(*unused_args):
      self.comparator.initialized = True
    d.addCallback(_comparator_initialized)
    PollingChangeSource.startService(self)

  def StopOnFailure(self, f):
    if self.running:
      d = defer.maybeDeferred(self.stopService)
      d.addErrback(log.err, 'while stopping broken RepoPoller service')
    return f

  def RunRepoCmd(self, args):
    log.msg('RepoPoller: running "%s %s"' % (self.repo_bin, ' '.join(args)))
    d = utils.getProcessOutputAndValue(self.repo_bin, args,
                                       env=dict(PATH=os.environ['PATH']),
                                       path=self.workdir)
    d.addCallback(ConvertNonZeroToFailure)
    d.addErrback(self.StopOnFailure)
    return d

  def DoLog(self, *args):
    return self.RunRepoCmd(['forall', '-p', '-c', self.git_bin, 'log',
                            '--format=%H %ct', 'repo_poller..'])

  def DoSync(self, *args):
    # TODO(szager): I pulled the number 4 out of thin air.  Better heuristic?
    return self.RunRepoCmd(['sync', '-j', '4'])

  def DoTag(self, *args):
    if self.changeCount == 0:
      return defer.succeed(0)
    self.changeCount = 0
    return self.RunRepoCmd(['forall', '-c', self.git_bin, 'tag', '-a', '-f',
                            'repo_poller', '-m', '"repo poller sync"'])

  @deferredLocked('initLock')
  def initRepository(self):
    if not os.path.exists(self.workdir):
      os.makedirs(self.workdir)
    repo_args = ['init', '-u', '/'.join([self.repo_url, 'manifest'])]
    if self.repo_branch:
      repo_args.extend(['-b', self.repo_branch])
    d = self.RunRepoCmd(repo_args)
    def _success(*args):
      log.msg('RepoPoller: finished initializing.')
    d.addCallback(_success)
    return d

  @deferredLocked('initLock')
  def initHistory(self, *args):
    log.msg('RepoPoller: initializing revision history')
    d = self.DoSync()
    def _getBranches(*args):
      return self.RunRepoCmd(['forall', '-p', '-c',
                              self.git_bin, 'branch'])
    d.addCallback(_getBranches)
    def _logBranches(args):
      (stdout, stderr, code) = args
      for line in stdout.splitlines():
        log.msg(line)
      return (stdout, stderr, code)
    d.addCallback(_logBranches)
    def _log(*args):
      return self.RunRepoCmd(['forall', '-p', '-c',
                              self.git_bin, 'log', '--format=%H %ct'])
    d.addCallback(_log)
    d.addCallback(self.ProcessInitialHistory)
    def _setChangeCount(*args):
      self.changeCount = 1  # To force DoTag.
    d.addCallback(_setChangeCount)
    d.addCallback(self.DoTag)
    return d

  @deferredLocked('initLock')
  def poll(self):
    log.msg('RepoPoller: polling...')
    d = self.DoSync()
    d.addCallback(self.DoLog)
    d.addCallback(self.ProcessChanges)
    d.addCallback(self.DoTag)
    def _success(*args):
      log.msg('RepoPoller: finished polling.')
    d.addCallback(_success)
    return d

  def GetCommitComments(self, project, rev):
    args = ['log', rev, '--no-walk', '--format=%s%n%b']
    d = utils.getProcessOutput(self.git_bin, args,
                               path=os.path.join(self.workdir, project),
                               env=dict(PATH=os.environ['PATH']),
                               errortoo=False)
    def process(git_output):
      stripped_output = git_output.strip().decode(self.encoding)
      if len(stripped_output) == 0:
        raise RuntimeError('could not get commit comment for rev')
      return stripped_output
    d.addCallback(process)
    return d

  def GetCommitFiles(self, project, rev):
    args = ['log', rev, '--name-only', '--no-walk', '--format=%n']
    d = utils.getProcessOutput(self.git_bin, args,
                               path=os.path.join(self.workdir, project),
                               env=dict(PATH=os.environ['PATH']),
                               errortoo=False)
    d.addCallback(lambda git_output: [x for x in git_output.splitlines() if x])
    return d

  def GetCommitName(self, project, rev):
    args = ['log', rev, '--no-walk', '--format=%aE']
    d = utils.getProcessOutput(self.git_bin, args,
                               path=os.path.join(self.workdir, project),
                               env=dict(PATH=os.environ['PATH']),
                               errortoo=False)
    def process(git_output):
      stripped_output = git_output.strip().decode(self.encoding)
      if len(stripped_output) == 0:
        raise RuntimeError('RepoPoller: could not get commit name for rev')
      return stripped_output
    d.addCallback(process)
    return d

  def ParseRepoGitLogs(self, stdout):
    project = None
    allchanges = []
    for line in stdout.splitlines():
      if not line:
        continue
      if line[:8] == 'project ':
        project = line[8:].rstrip('/')
        continue
      assert(project)
      (revision, timestamp) = line.split()
      allchanges.append((int(timestamp), project, revision))
    allchanges.sort()  # Sorts by timestamp
    for item in allchanges:
      self.comparator.addRevision(item[2])
    return allchanges

  def ProcessInitialHistory(self, args):
    """Initialize comparator with existing commits."""
    (stdout, stderr, status) = args
    if status:
      log.msg('RepoPoller: could not initialize repo history '
              'from git logs: %s.' % stderr)
      return
    self.ParseRepoGitLogs(stdout)

  @defer.deferredGenerator
  def ProcessChanges(self, args):
    (stdout, stderr, status) = args
    if status:
      log.msg('RepoPoller: running `git log` '
              'across repo projects failed: %s' % stderr)
      return

    for timestamp, project, rev in self.ParseRepoGitLogs(stdout):
      dl = defer.DeferredList([
          self.GetCommitName(project, rev),
          self.GetCommitFiles(project, rev),
          self.GetCommitComments(project, rev),
          ], consumeErrors=True)

      wfd = defer.waitForDeferred(dl)
      yield wfd
      results = wfd.getResult()

      # check for failures
      failures = [r[1] for r in results if not r[0]]
      if failures:
        # just fail on the first error; they're probably all related!
        raise failures[0]

      revlink = ''
      if self.revlinktmpl and rev:
        revlink = self.revlinktmpl % (
            urllib.quote_plus(project), urllib.quote_plus(rev))

      name, files, comments = [r[1] for r in results]
      d = self.master.addChange(
          author=name,
          revision=rev,
          files=files,
          comments=comments,
          when_timestamp=epoch2datetime(timestamp),
          branch=None,
          category=self.category,
          project=self.project,
          repository='/'.join([self.repo_url, project]),
          revlink=revlink)
      wfd = defer.waitForDeferred(d)
      yield wfd
      results = wfd.getResult()
      self.changeCount += 1
