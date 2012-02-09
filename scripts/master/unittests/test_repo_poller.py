#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil
import subprocess
import tempfile

import twisted
from twisted.application import service
from twisted.internet import defer, task, reactor
from twisted.mail import smtp
from twisted.trial import unittest
import buildbot.changes.base

class MasterProxy(object):
  def __init__(self):
    self.changes = []
  def addChange(self, *args, **kwargs):
    self.changes.append((args, kwargs))
    return defer.succeed(0)

class PollingChangeSourceProxy(service.Service):
  def __init__(self):
    self.master = None
  def startService(self):
    self.master = MasterProxy()
    service.Service.startService(self)
  def stopService(self):
    return service.Service.stopService(self)

SENT_MAILS = []

def sendmail_proxy(smtphost, from_addr, to_addrs, msg,
                   senderDomainName=None, port=25):
  SENT_MAILS.append((smtphost, from_addr, to_addrs, msg,
                     senderDomainName, port))
  return defer.succeed(0)

buildbot.changes.base.PollingChangeSource = PollingChangeSourceProxy
smtp.sendmail = sendmail_proxy

from master.repo_poller import RepoPoller

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'repo'))
REPO_BIN = os.path.join(REPO_DIR, 'repo')
REPO_URL = os.path.join(REPO_DIR, 'clone.bundle')

REPO_MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <remote  name="default" fetch="." />
  <default revision="master" remote="default" sync-j="1" />
  <project name="git0" />
  <project name="git1" />
  <project name="git2" />
</manifest>
"""

class TestRepoPoller(unittest.TestCase):

  def setUp(self):
    self.workdir = tempfile.mkdtemp(prefix='repo_poller_simple_test')
    self.repo_src = os.path.join(self.workdir, 'repo-src')
    self.repo_work = os.path.join(self.workdir, 'repo-work')

    manifest_dir = os.path.join(self.repo_src, 'manifest')
    git_dir_base = os.path.join(self.repo_src, 'git')
    git_dirs = ['%s%d' % (git_dir_base, x) for x in range(3)]

    for d in git_dirs + [manifest_dir, self.repo_work]:
      if not os.path.exists(d):
        os.makedirs(d)

    for d in git_dirs + [manifest_dir]:
      self.assertFalse(subprocess.call(['git', 'init', '--quiet'], cwd=d))

    fh = open(os.path.join(manifest_dir, 'default.xml'), 'w')
    fh.write(REPO_MANIFEST)
    fh.close()
    self.assertFalse(subprocess.call(['git', 'add', 'default.xml'],
                                     cwd=manifest_dir))
    self.assertFalse(subprocess.call(['git', 'commit', '-q', '-m', 'empty'],
                                     cwd=manifest_dir))

    for x in range(3):
      git_dir = git_dirs[x]
      fh = open(os.path.join(git_dir, 'file%d.txt' % x), 'w')
      fh.write('Contents of file%d.txt\n' % x)
      fh.close()
      self.assertFalse(subprocess.call(['git', 'add', 'file%d.txt' % x],
                                       cwd=git_dir))
      self.assertFalse(subprocess.call(['git', 'commit', '-q', '-m', 'empty'],
                                       cwd=git_dir))

    cmd = [REPO_BIN, 'init', '--no-repo-verify',
           '--repo-url', REPO_URL, '-u', manifest_dir]
    devnull = open(os.devnull, 'w')
    self.assertFalse(subprocess.call(cmd, cwd=self.repo_work,
                                     stdout=devnull, stderr=devnull))
    devnull.close()

    self.poller = RepoPoller(self.repo_src, repo_branch='master',
                             workdir=self.repo_work, pollInterval=999999,
                             repo_bin=REPO_BIN, from_addr='sender@example.com',
                             to_addrs='recipient@example.com',
                             smtp_host='nohost')
    self.poller.startService()

  def tearDown(self):
    self.poller.stopService()
    shutil.rmtree(self.workdir)

  def _modifySrcFile(self, gitname, filename, comment='comment'):
    src_dir = os.path.join(self.repo_src, gitname)
    src_file = os.path.join(src_dir, filename)
    fh = open(src_file, 'a')
    fh.write('A change to %s.' % filename)
    fh.close()
    self.assertFalse(subprocess.call(['git', 'add', filename],
                                     cwd=src_dir))
    self.assertFalse(subprocess.call(['git', 'commit', '-q', '-m', comment],
                                     cwd=src_dir))

  @defer.deferredGenerator
  def test1_simple(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()
    self.assertEqual(len(self.poller.comparator.tag_order), 3,
                     "Three initial revisions in repo checkout.")

  @defer.deferredGenerator
  def test2_single_change(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    self._modifySrcFile('git2', 'file2.txt', 'comment2')

    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()
    self.assertEqual(len(self.poller.comparator.tag_order), 4,
                     "Four total revisions after a single commit.")
    self.assertEqual(len(self.poller.master.changes), 1,
                     "One change in master")
    change = self.poller.master.changes[0][1]
    self.assertEqual(change['files'], ['file2.txt'],
                     'File(s) in change.')
    self.assertEqual(change['repository'], os.path.join(self.repo_src, 'git2'),
                     'Repository for change.')
    self.assertEqual(change['comments'], 'comment2',
                     'Change comments')

  @defer.deferredGenerator
  def test3_multiple_changes(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    self._modifySrcFile('git1', 'file1.txt')

    d = task.deferLater(reactor, 2, self._modifySrcFile, 'git2', 'file2.txt')
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    d = task.deferLater(reactor, 2, self._modifySrcFile, 'git0', 'file0.txt')
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    self.assertEqual(len(self.poller.comparator.tag_order), 6,
                     "Six total revisions after three commits.")
    self.assertEqual(len(self.poller.master.changes), 3,
                     "Three changes in master")
    self.assertEqual(self.poller.master.changes[0][1]['repository'],
                     os.path.join(self.repo_src, 'git0'),
                     'Commit ordering by timestamp')
    self.assertEqual(self.poller.master.changes[1][1]['repository'],
                     os.path.join(self.repo_src, 'git1'),
                     'Commit ordering by timestamp')
    self.assertEqual(self.poller.master.changes[2][1]['repository'],
                     os.path.join(self.repo_src, 'git2'),
                     'Commit ordering by timestamp')

  @defer.deferredGenerator
  def test4_stable_sort(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    # Create enough commits to make sure their are timestamp collisions
    for i in range(5):
      self._modifySrcFile('git1', 'file1.txt', 'c%d' % i)

    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    comments = [change[1]['comments'] for change in self.poller.master.changes]
    self.assertEqual(comments, ['c%d' % i for i in range(5)],
                     'Stable sort')

  @defer.deferredGenerator
  def test5_err_notification(self):
    # Poll once to make sure working dir is initialized
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    # Trigger errors in polling by messing up working dir
    shutil.rmtree(os.path.join(self.repo_work, '.repo'))

    for i in range(3):
      d = self.poller.poll()
      d.addErrback(lambda failure: True)
      wfd = defer.waitForDeferred(d)
      yield wfd
      wfd.getResult()
      self.assertEqual(self.poller.errCount, i+1,
                       'Error count')

    self.assertEqual(len(SENT_MAILS), 1)
    self.assertEqual(SENT_MAILS[0][0:3],
                     ('nohost', 'sender@example.com', 'recipient@example.com'))

if __name__ == '__main__':
  exe = os.path.join(os.path.dirname(twisted.__path__[0]), 'bin', 'trial')
  os.execv(exe, [exe, 'test_repo_poller'])
