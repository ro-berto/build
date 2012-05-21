#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Commands for zipping a git clone and uploading it to Google Storage.

The git clone contains a .git directory, but none of the actual source
files from the repository.  That's accomplished by using the -n flag to
`git clone`.  The advantages of this approach are:

  - Keeps the size of the zip file down.
  - Unlike a git bundle, there's no index to rebuild.  That greatly speeds
    up the unpacking process and avoids a common source of errors (corrupt
    index file).

This class supports git submodules, i.e., it will discover and clone all
submodules that are registered in a .gitmodules file.  Multiple levels
of submodules are supported.

The output of this script consists of four files:

  <workdir>/<repobase>-bare.zip
  <workdir>/<repobase>-bare.zip.sha1
  <workdir>/<repobase>-full.zip
  <workdir>/<repobase>-full.zip.sha1

... where <repobase> is the human-ish part of the top-level git repo.
<repobase>-bare.zip contains just the top-level git repository, no submodules.
<repobase>-full.zip contains the top-level plus all submodules.
The .sha1 files are the result of running sha1sum on the zip files.
If a gs_bucket is provided to the constructor, these four files will be
uploaded to Google Storage.

To bootstrap a source checkout from the uploaded zip file:

  $ wget http://commondatastorage.googleapis.com/<bucket>/<repobase>-full.zip
  $ unzip <repobase>-full.zip
  $ cd <repobase>
  $ git checkout HEAD
  # If there are submodules:
  $ git submodule update --init --recursive
  $ git submodule foreach --recursive git checkout HEAD
"""

import optparse
import os
try:
  # pylint: disable=F0401
  from queue import Queue
except ImportError:
  from Queue import Queue
import subprocess
import sys
import tempfile
import threading

from slave.slave_utils import GSUtilSetup

# pylint: disable=W0232
class TerminateMessageThread:
  pass


class GitZip(object):
  # pylint: disable=W0621
  def __init__(self, workdir, base=None, url=None, gs_bucket=None,
               gs_acl='public-read', timeout=900, stayalive=None,
               verbose=False):
    self.workdir = workdir
    if url and not base:
      base = os.path.basename(url)
      if base.endswith('.git'):
        base = base[:-4]
    self.base = base
    self.url = url
    self.gs_bucket = gs_bucket
    self.gs_acl = gs_acl
    self.timeout = timeout
    self.stayalive = stayalive
    self.stayalive_timer = None
    self.verbose = verbose
    self.messages = Queue()

  def _run_cmd(self, cmd, workdir=None, raiseOnFailure=True):
    if workdir is None:
      workdir = self.workdir
    def _thread_main():
      thr = threading.current_thread()
      try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
        (stdout, stderr) = proc.communicate()
      except Exception, e:
        thr.status = -1
        thr.stdout = ''
        thr.stderr = repr(e)
      else:
        thr.status = proc.returncode
        thr.stdout = stdout
        thr.stderr = stderr
    thr = threading.Thread(target=_thread_main)
    if self.verbose:
      self.messages.put('Running "%s" in %s' % (' '.join(cmd), workdir))
    thr.start()
    thr.join(self.timeout)
    if thr.isAlive():
      raise RuntimeError('command "%s" in dir "%s" timed out' % (
          ' '.join(cmd), workdir))
    # pylint: disable=E1101
    if raiseOnFailure and thr.status != 0:
      raise RuntimeError('command "%s" in dir "%s" exited with status %d:\n%s' %
                         (' '.join(cmd), workdir, thr.status, thr.stderr))
    return (thr.status, thr.stdout, thr.stderr)

  def _pump_messages(self):
    def _stayalive():
      print "Still working..."
      self.stayalive_timer = threading.Timer(self.stayalive, _stayalive)
      self.stayalive_timer.start()

    while True:
      if self.stayalive:
        self.stayalive_timer = threading.Timer(self.stayalive, _stayalive)
        self.stayalive_timer.start()
      msg = self.messages.get()
      if self.stayalive_timer:
        self.stayalive_timer.cancel()
        self.stayalive_timer = None
      if msg is TerminateMessageThread:
        return
      print msg

  def FetchSubmodules(self, clonedir):
    # Get path/url information for submodules
    config_cmd = ['git', 'config', '-f', '.gitmodules', '-l']
    (_, stdout, _) = self._run_cmd(config_cmd, clonedir)

    submods = {}
    for line in stdout.splitlines():
      try:
        (key, val) = line.split('=')
        (header, mod_name, subkey) = key.split('.')
        if header != 'submodule':
          continue
        submod_dict = submods.setdefault(mod_name, {})
        submod_dict[subkey] = val
      except ValueError:
        pass

    threads = []
    for submod_dict in submods.itervalues():
      if 'path' not in submod_dict or 'url' not in submod_dict:
        continue
      submod_clonedir = os.path.join(clonedir, submod_dict['path'])
      submod_url = submod_dict['url']
      thr = threading.Thread(
          target=self.DoFetch, args=(submod_clonedir, submod_url))
      thr.start()
      threads.append(thr)
    for thr in threads:
      thr.join()
    for thr in threads:
      if thr.err:
        raise thr.err

  def PostFetch(self, clonedir):
    try:
      # If there's a .gitmodules file, fetch submodules
      cmd = ['git', 'checkout', 'HEAD', '.gitmodules']
      (status, _, _) = self._run_cmd(cmd, clonedir, raiseOnFailure=False)
      if status != 0:
        return
      self.FetchSubmodules(clonedir)
    except:
      raise
    finally:
      # Make sure git index is clean
      cmd = ['rm', '-rf', '.gitmodules', os.path.join('.git', 'index')]
      self._run_cmd(cmd, clonedir)

  def DoFetch(self, clonedir, url=None):
    try:
      if os.path.isdir(os.path.join(clonedir, '.git')):
        cmd = ['git', 'fetch', 'origin']
        workdir = clonedir
      elif url is not None:
        clonedir_parent = os.path.dirname(clonedir)
        if clonedir_parent and not os.path.isdir(clonedir_parent):
          self._run_cmd(['mkdir', '-p', clonedir_parent])
        cmd = ['git', 'clone', '-n', url, clonedir]
        workdir = self.workdir
      else:
        raise RuntimeError('No existing checkout, and no url provided')
      self._run_cmd(cmd, workdir)
      self.PostFetch(clonedir)
    except Exception, e:
      threading.current_thread().err = e
      raise
    else:
      threading.current_thread().err = None

  def CreateZipFile(self, zippath, zipfile, sha1_file):
    cmd = ['zip', '-0', '-r', '-o', zipfile, zippath]
    self._run_cmd(cmd)
    cmd = ['sha1sum', os.path.basename(zipfile)]
    (_, stdout, _) = self._run_cmd(cmd, workdir=os.path.dirname(zipfile))
    fh = open(sha1_file, 'w')
    fh.write('%s' % stdout)
    fh.close()

  def UploadFiles(self, *f):
    try:
      if not self.gs_bucket:
        return
      gsutil_exe = GSUtilSetup()
      gs_url = self.gs_bucket
      if not gs_url.startswith('gs://'):
        gs_url = 'gs://%s' % gs_url
      cmd = [gsutil_exe, 'cp', '-a', self.gs_acl] + list(f) + [gs_url]
      self._run_cmd(cmd)
    except Exception, e:
      threading.current_thread().err = e
      raise
    else:
      threading.current_thread().err = None

  def ZipAndUpload(self):
    # Create a zip file of everything
    full_zippath = self.base
    full_zipfile = os.path.join(self.workdir, '%s-full.zip' % self.base)
    full_sha1_file = '%s.sha1' % full_zipfile
    self.CreateZipFile(full_zippath, full_zipfile, full_sha1_file)

    full_thr = threading.Thread(
        target=self.UploadFiles, args=(full_zipfile, full_sha1_file))
    full_thr.start()

    # Create a zip file of just the top-level source without submodules
    bare_zippath = os.path.join(self.base, '.git')
    bare_zipfile = os.path.join(self.workdir, '%s-bare.zip' % self.base)
    bare_sha1_file = '%s.sha1' % bare_zipfile
    self.CreateZipFile(bare_zippath, bare_zipfile, bare_sha1_file)

    bare_thr = threading.Thread(
        target=self.UploadFiles, args=(bare_zipfile, bare_sha1_file))
    bare_thr.start()

    full_thr.join()
    bare_thr.join()
    # pylint: disable=E1101
    if full_thr.err:
      # pylint: disable=E1101
      raise full_thr.err
    # pylint: disable=E1101
    if bare_thr.err:
      # pylint: disable=E1101
      raise bare_thr.err

  def Run(self):
    message_thread = threading.Thread(target=self._pump_messages)
    message_thread.start()
    try:
      self.DoFetch(self.base, self.url)
      self.ZipAndUpload()
    finally:
      self.messages.put(TerminateMessageThread)
      message_thread.join()


if __name__ == '__main__':
  parser = optparse.OptionParser()
  parser.add_option('-d', '--workdir', action='store', dest='workdir',
                    help='Working directory in which to clone git repository')
  parser.add_option('-b', '--base', action='store', dest='base',
                    help='The directory under <workdir> containing the '
                    'pre-existing top-level source checkout')
  parser.add_option('-u', '--url', action='store', dest='url', metavar='<url>',
                    help='URL of top-level git repository')
  parser.add_option('-g', '--gs_bucket', action='store', dest='gs_bucket',
                    help='URL of Google Storage bucket to upload result')
  parser.add_option('-a', '--gs_acl', action='store', dest='gs_acl',
                    default='public-read', help='Canned ACL for objects '
                    'uploaded to Google Storage')
  parser.add_option('-t', '--timeout', action='store', type=int, dest='timeout',
                    help='Timeout for individual commands', default=3600)
  parser.add_option('-s', '--stayalive', action='store', type=int,
                    dest='stayalive', help='Make sure this script produces '
                    'terminal output at least every <stayalive> seconds, to '
                    'prevent its parent process from timing out.', default=200)
  parser.add_option('-v', '--verbose', action='store_true', dest='verbose')
  options, args = parser.parse_args()

  if not options.workdir:
    if not options.url:
      parser.print_help()
      sys.exit(1)
    options.workdir = tempfile.mkdtemp(prefix='gitzip_workdir')
    print 'Creating working directory in %s' % options.workdir

  if not options.base:
    if not options.url:
      parser.print_help()
      sys.exit(1)
    base = os.path.basename(options.url)
    if base.endswith('.git'):
      base = base[:-4]
    options.base = base

  kwargs = {}
  for kw in ['workdir', 'base', 'url', 'gs_bucket', 'gs_acl', 'timeout',
             'stayalive', 'verbose']:
    kwargs[kw] = getattr(options, kw)
  gitzip = GitZip(**kwargs)
  gitzip.Run()
  sys.exit(0)
