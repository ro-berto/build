#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Starts all masters and verify they can server /json/project fine.
"""

from __future__ import with_statement
import logging
import optparse
import os
import subprocess
import sys
import time

import masters_util


def test_master(master, name, path):
  print('Trying %s' % master)
  start = time.time()
  if not masters_util.stop_master(master, path):
    return False
  # Try to backup twistd.log
  twistd_log = os.path.join(path, 'twistd.log')
  had_twistd_log = os.path.isfile(twistd_log)
  # Try to backup a Git workdir.
  git_workdir = os.path.join(path, 'git_poller_src.git')
  had_git_workdir = os.path.isdir(git_workdir)
  try:
    if had_twistd_log:
      os.rename(twistd_log, twistd_log + '_')
    if had_git_workdir:
      if subprocess.call(['mv', git_workdir, git_workdir + '_']) != 0:
        print >> sys.stderr, 'ERROR: Failed to rename %s' % git_workdir
    try:
      if not masters_util.start_master(master, path):
        return False

      res = masters_util.wait_for_start(master, name, path)
      if res:
        logging.info('Success in %1.1fs' % (time.time() - start))
      return res
    finally:
      masters_util.stop_master(master, path)
  finally:
    if had_twistd_log:
      os.rename(twistd_log + '_', twistd_log)
    if (os.path.isdir(git_workdir) and
        subprocess.call(['rm', '-rf', git_workdir]) != 0):
      print >> sys.stderr, 'ERROR: Failed to remove %s' % git_workdir
    if had_git_workdir:
      if subprocess.call(['mv', git_workdir + '_', git_workdir]) != 0:
        print >> sys.stderr, 'ERROR: Failed to rename %s' % (git_workdir + '_')


def real_main(base_dir, expected):
  expected = expected.copy()
  parser = optparse.OptionParser()
  parser.add_option('-v', '--verbose', action='count', default=0)
  options, args = parser.parse_args()
  if args:
    parser.error('Unsupported args %s' % ' '.join(args))
  levels = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)
  logging.basicConfig(level=levels[min(options.verbose, len(levels)-1)])

  start = time.time()
  base = os.path.join(base_dir, 'masters')
  # Here we look for a slaves.cfg file in the directory to ensure that
  # the directory actually contains a master, as opposed to having existed
  # at one time but later having been removed.  In the latter case, it's
  # no longer an actual master that should be 'discovered' by this test.
  masters = sorted(
      p for p in os.listdir(base)
      if (os.path.isfile(os.path.join(base, p, 'slaves.cfg')) and
          not p.startswith('.'))
  )

  failed = set()
  skipped = 0
  success = 0

  # First make sure no master is started. Otherwise it could interfere with
  # conflicting port binding.
  if not masters_util.check_for_no_masters():
    return 1
  for master in masters:
    pid_path = os.path.join(base, master, 'twistd.pid')
    if os.path.isfile(pid_path):
      pid_value = int(open(pid_path).read().strip())
      if masters_util.pid_exists(pid_value):
        print >> sys.stderr, ('%s is still running as pid %d.' %
            (master, pid_value))
        print >> sys.stderr, 'Please stop it before running the test.'
        return 1

  bot_pwd_path = os.path.join(
      base_dir, '..', 'build', 'site_config', '.bot_password')
  need_bot_pwd = not os.path.isfile(bot_pwd_path)
  try:
    if need_bot_pwd:
      with open(bot_pwd_path, 'w') as f:
        f.write('foo\n')
    for master in masters[:]:
      if not master in expected:
        continue
      masters.remove(master)
      name = expected.pop(master)
      if not name:
        skipped += 1
        continue
      if not test_master(master, name, os.path.join(base, master)):
        failed.add(master)
      else:
        success += 1
  finally:
    if need_bot_pwd:
      os.remove(bot_pwd_path)

  if failed:
    print >> sys.stderr, (
        '%d masters failed:\n%s' % (len(failed), '\n'.join(sorted(failed))))
  if masters:
    print >> sys.stderr, (
        '%d masters were not expected:\n%s' %
        (len(masters), '\n'.join(sorted(masters))))
  if expected:
    print >> sys.stderr, (
        '%d masters were expected but not found:\n%s' %
        (len(expected), '\n'.join(sorted(expected))))
  print >> sys.stderr, (
      '%s masters succeeded, %d failed, %d skipped in %1.1fs.' % (
        success, len(failed), skipped, time.time() - start))
  return int(bool(masters or expected or failed))


def main():
  base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  expected = {
      'master.chromium': 'Chromium',
      'master.chromium.chrome': 'Chromium Chrome',
      'master.chromium.chromebot': 'Chromium Chromebot',
      'master.chromium.chromiumos': 'Chromium ChromiumOS',
      'master.chromium.flaky': 'Chromium Flaky',
      'master.chromium.fyi': 'Chromium FYI',
      'master.chromium.git': 'Chromium Git',
      'master.chromium.gpu': 'Chromium GPU',
      'master.chromium.gpu.fyi': 'Chromium GPU FYI',
      'master.chromium.linux': 'Chromium Linux',
      'master.chromium.lkgr': 'Chromium LKGR',
      'master.chromium.mac': 'Chromium Mac',
      'master.chromium.memory': None,
      'master.chromium.memory.fyi': 'Chromium Memory FYI',
      'master.chromium.perf': 'Chromium Perf',
      'master.chromium.perf_av': 'Chromium Perf Av',
      'master.chromium.pyauto': 'Chromium PyAuto',
      'master.chromium.swarm': 'Chromium Swarm',
      'master.chromium.webkit': 'Chromium Webkit',
      'master.chromium.win': 'Chromium Win',
      'master.chromiumos': 'ChromiumOS',
      'master.client.drmemory': None,  # make start fails
      'master.client.dart': 'Dart',  # make start fails
      'master.client.dart.fyi': 'Dart FYI',  # make start fails
      'master.client.nacl': 'NativeClient',
      'master.client.nacl.chrome': 'NativeClientChrome',
      'master.client.nacl.llvm': 'NativeClientLLVM',
      'master.client.nacl.ports': 'NativeClientPorts',
      'master.client.nacl.ppapi': 'NativeClientPPAPI',
      'master.client.nacl.sdk': 'NativeClientSDK',
      'master.client.nacl.sdk.mono': 'NativeClientSDKMono',
      'master.client.nacl.toolchain': 'NativeClientToolchain',
      'master.client.omaha': 'Omaha',
      'master.client.pagespeed': 'PageSpeed',
      'master.client.sfntly': None,
      'master.client.skia': None,
      'master.client.syzygy': None,
      'master.client.tsan': None,  # make start fails
      'master.client.v8': 'V8',
      'master.experimental': None,
      'master.reserved': None,  # make start fails
      'master.tryserver.chromium': 'Chromium Try Server',
      'master.tryserver.nacl': 'NativeClient-Try',
      'master.chromiumos.tryserver': None,
      'master.devtools': 'Chromium DevTools',
  }
  return real_main(base_dir, expected)


if __name__ == '__main__':
  sys.exit(main())
