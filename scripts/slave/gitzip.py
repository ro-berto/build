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

  # One of the following:
  $ ./.git/hooks/first-checkout.sh   # posix
  > .\.git\hooks\first-checkout.bat  # windows
"""

import optparse
import os
try:
  # pylint: disable=F0401
  from queue import Queue
except ImportError:
  from Queue import Queue
import stat
import subprocess
import sys
import tempfile
import threading

from slave.slave_utils import GSUtilSetup

FIRST_CHECKOUT_SH = """#!/bin/bash

if -z "$1"; then
  case `uname -s` in
    "Linux")
      os=unix
      ;;
    "Darwin")
      os=mac
      ;;
    *)
      echo "You didn't specify an OS (mac, win, unix, or android), \
and I can't figure it out from 'uname -s'" 1>&2
      exit 1
      ;;
  esac
else
  os=$1
fi

git config target.os $os
git checkout --force HEAD
git config -f .gitmodules --get-regexp '.os$' "(all|$os)" |
sed 's/^submodule\.\(.*\)\.os .*$/\1/' |
while read submodule; do
  git config submodule.$submodule.update checkout
  (cd $submodule && git checkout --force HEAD)
done
git submodule update
"""

FIRST_CHECKOUT_BAT = """@echo off
setlocal

if "%1" == "" (
  SET os=win
) ELSE (
  SET os=%1
)

call git config target.os %os%
call git checkout --force HEAD

FOR /F "delims=. tokens=2" %%x in ^
    ('git config -f .gitmodules --get-regexp .os$ "(all|%os%)"') DO (
  call git config submodule.%%x.update checkout
  CMD /C "cd %%x & git checkout --force HEAD"
)

call git submodule update
"""


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
      submod_path = submod_dict['path']
      submod_clonedir = os.path.join(clonedir, submod_path)
      submod_url = submod_dict['url']
      self._run_cmd(['git', 'checkout', 'HEAD', submod_path], clonedir)
      thr = threading.Thread(
          target=self.DoFetch, args=(submod_clonedir, submod_url))
      thr.start()
      threads.append(thr)
    for thr in threads:
      thr.join()
    for thr in threads:
      if thr.err:
        raise thr.err
    self._run_cmd(['git', 'submodule', 'init'], clonedir)
    self._run_cmd(['git', 'config', 'diff.ignoreSubmodules', 'all'], clonedir)
    self._run_cmd(['git', 'submodule', 'foreach', 'git', 'config', '-f',
                   '$toplevel/.git/config', 'submodule.$name.ignore', 'all'],
                   clonedir)
    self._run_cmd(['git', 'submodule', 'foreach', 'git', 'config', '-f',
                   '$toplevel/.git/config', 'submodule.$name.update', 'none'],
                  clonedir)

  def PostFetch(self, clonedir):
    try:
      # Set up git config
      self._run_cmd(['git', 'config', 'core.autocrlf', 'false'], clonedir)
      self._run_cmd(['git', 'config', 'core.filemode', 'false'], clonedir)

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
        cmd = ['git', 'clone', '-n', url, clonedir]
        workdir = self.workdir
      else:
        raise RuntimeError('No existing checkout, and no url provided')
      self._run_cmd(cmd, workdir)
      self._run_cmd(['git', 'update-ref', 'refs/heads/master', 'origin/master'],
                    clonedir)
      self.PostFetch(clonedir)
    except Exception, e:
      threading.current_thread().err = e
      raise
    else:
      threading.current_thread().err = None

  @staticmethod
  def CreateFirstCheckoutHook(clonedir):
    permissions = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                   stat.S_IRGRP | stat.S_IXGRP|
                   stat.S_IROTH | stat.S_IXOTH)
    hook_path = os.path.join(clonedir, '.git', 'hooks', 'first-checkout.sh')
    fh = open(hook_path, 'w')
    fh.write(FIRST_CHECKOUT_SH)
    fh.close()
    os.chmod(hook_path, permissions)
    hook_path = os.path.join(clonedir, '.git', 'hooks', 'first-checkout.bat')
    fh = open(hook_path, 'w')
    fh.write(FIRST_CHECKOUT_BAT)
    fh.close()
    os.chmod(hook_path, permissions)

  def CreateZipFile(self, zippath, zipfile, sha1_file):
    self._run_cmd(['rm', '-f', zipfile])
    cmd = ['7z', 'a', '-tzip', '-mx=0', zipfile, zippath]
    self._run_cmd(cmd)
    cmd = ['sha1sum', os.path.basename(zipfile)]
    (_, stdout, _) = self._run_cmd(cmd, workdir=os.path.dirname(zipfile))
    fh = open(sha1_file, 'w')
    fh.write('%s' % stdout)
    fh.close()

  def UploadFiles(self, *f, **kwargs):
    try:
      threading.current_thread().err = None
      if not self.gs_bucket:
        return
      gsutil_exe = GSUtilSetup()
      gs_url = self.gs_bucket
      if not gs_url.startswith('gs://'):
        gs_url = 'gs://%s' % gs_url
      cmd = ([gsutil_exe] + kwargs.get('gsutil_args', []) +
             ['cp', '-a', self.gs_acl] + list(f) + [gs_url])
      self._run_cmd(cmd)
    except Exception, e:
      threading.current_thread().err = e
      raise

  def ZipAndUpload(self):
    gs_threads = []

    # Create a zip file of everything
    full_zippath = self.base
    full_zipfile = os.path.join(self.workdir, '%s-full.zip' % self.base)
    full_sha1_file = '%s.sha1' % full_zipfile
    self.CreateZipFile(full_zippath, full_zipfile, full_sha1_file)

    thr = threading.Thread(
        target=self.UploadFiles,
        args=(full_zipfile,))
    thr.start()
    gs_threads.append(thr)

    thr = threading.Thread(
        target=self.UploadFiles,
        args=(full_sha1_file,),
        kwargs={'gsutil_args': ['-h', 'Content-Type:text/html']})
    thr.start()
    gs_threads.append(thr)

    # Create a zip file of just the top-level source without submodules
    bare_zippath = os.path.join(self.base, '.git')
    bare_zipfile = os.path.join(self.workdir, '%s-bare.zip' % self.base)
    bare_sha1_file = '%s.sha1' % bare_zipfile
    self.CreateZipFile(bare_zippath, bare_zipfile, bare_sha1_file)

    thr = threading.Thread(
        target=self.UploadFiles,
        args=(bare_zipfile,))
    thr.start()
    gs_threads.append(thr)

    thr = threading.Thread(
        target=self.UploadFiles,
        args=(bare_sha1_file,),
        kwargs={'gsutil_args': ['-h', 'Content-Type:text/html']})
    thr.start()
    gs_threads.append(thr)

    map(threading.Thread.join, gs_threads)
    for thr in gs_threads:
      if thr.err:
        raise thr.err

  def Run(self):
    message_thread = threading.Thread(target=self._pump_messages)
    message_thread.start()
    try:
      self.DoFetch(self.base, self.url)
      self.CreateFirstCheckoutHook(self.base)
      self.ZipAndUpload()
    finally:
      self.messages.put(TerminateMessageThread)
      message_thread.join()


if __name__ == '__main__':
  parser = optparse.OptionParser()
  parser.add_option('-d', '--workdir', action='store', dest='workdir',
                    metavar='DIR', help='Working directory in which to clone '
                    'the git repository')
  parser.add_option('-b', '--base', action='store', dest='base',
                    metavar='DIR', help='The directory under WORKDIR '
                    'containing the pre-existing top-level source checkout')
  parser.add_option('-u', '--url', action='store', dest='url', metavar='URL',
                    help='URL of top-level git repository')
  parser.add_option('-g', '--gs_bucket', action='store', dest='gs_bucket',
                    help='URL of Google Storage bucket to upload result')
  parser.add_option('-a', '--gs_acl', action='store', dest='gs_acl',
                    metavar='URL', default='public-read', help='Canned ACL for '
                    'objects uploaded to Google Storage')
  parser.add_option('-t', '--timeout', action='store', type=int, dest='timeout',
                    help='Timeout for individual commands', default=3600)
  parser.add_option('-s', '--stayalive', action='store', type=int,
                    dest='stayalive', help='Make sure this script produces '
                    'terminal output at least every STAYALIVE seconds, to '
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
