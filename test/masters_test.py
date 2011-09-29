#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Starts all masters and verify they can server /json/project fine.
"""

from __future__ import with_statement
import logging
import optparse
import os
import sys
import time
import urllib

import find_depot_tools  # pylint: disable=W0611
import subprocess2
from rietveld import json


def stop_master(master, path):
  if not os.path.isfile(os.path.join(path, 'twistd.pid')):
    return True
  try:
    subprocess2.check_output(
        ['make', 'stop'], timeout=60, cwd=path,
        stderr=subprocess2.STDOUT)
    for _ in range(100):
      if not os.path.isfile(os.path.join(path, 'twistd.pid')):
        return True
      time.sleep(0.1)
    return False
  except subprocess2.CalledProcessError, e:
    if 'No such process' in e.stdout:
      logging.warning('Flushed ghost twistd.pid for %s' % master)
      os.remove(os.path.join(path, 'twistd.pid'))
      return True
    return False


def test_master(master, name, path):
  print('Trying %s' % master)
  start = time.time()
  if not stop_master(master, path):
    return False
  # Try to backup twistd.log
  twistd_log = os.path.join(path, 'twistd.log')
  had_twistd_log = os.path.isfile(twistd_log)
  try:
    if had_twistd_log:
      os.rename(twistd_log, twistd_log + '_')
    ports = range(8000, 8080) + range(8200, 8240) + range(9000, 9080)
    try:
      try:
        subprocess2.check_call(
            ['make', 'start'], timeout=60, cwd=path,
            stderr=subprocess2.STDOUT)
      except subprocess2.CalledProcessError:
        return False

      # It has ~10 seconds to boot.
      for _ in range(100):
        for p in ports:
          try:
            data = json.load(
                urllib.urlopen('http://localhost:%d/json/project' % p))
            if not data or not 'projectName' in data:
              logging.warning('Didn\'t get valid data from %s' % master)
              continue
            if data['projectName'] != name:
              logging.error(
                  'Wrong %s name, expected %s, got %s' %
                  (master, name, data['projectName']))
              return False
            logging.info('Success in %1.1fs' % (time.time() - start))
            return True
          except ValueError:
            logging.warning('Didn\'t get valid data from %s' % master)
          except IOError:
            logging.warning('Didn\'t get data from %s' % master)
        # Look in twistd.log for an exception:

        # TODO(maruel): Search for 'exception' in twistd.log.
        with open(twistd_log) as f:
          lines = f.readlines()
          stripped_lines = [l.strip() for l in lines]
          try:
            i = stripped_lines.index('--- <exception caught here> ---')
            # Found an exception!
            print ''.join(lines[max(i-15, 0):i+10])
            return False
          except ValueError:
            pass

        time.sleep(0.1)
      logging.error('Didn\'t find open port for %s' % master)
      return False
    finally:
      stop_master(master, path)
  finally:
    if had_twistd_log:
      os.rename(twistd_log + '_', twistd_log)


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
  masters = sorted(
      p for p in os.listdir(base)
      if os.path.isdir(os.path.join(base, p)) and not p.startswith('.')
  )

  failed = set()
  skipped = 0
  success = 0

  # First make sure no master is started. Otherwise it could interfere with
  # conflicting port binding.
  for master in masters:
    pid_path = os.path.join(base, master, 'twistd.pid')
    if os.path.isfile(pid_path):
      print >> sys.stderr, (
          '%s is still running as pid %s.' %
          (master, open(pid_path).read().strip()))
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
  # TODO(maruel): Add support for buildbot 0.8.x masters.
  expected = {
      'master.chromium': 'Chromium',
      'master.chromium.chrome': 'Chromium Chrome',
      'master.chromium.chromiumos': 'Chromium ChromiumOS',
      'master.chromium.flaky': None,
      'master.chromium.fyi': 'Chromium FYI',
      'master.chromium.git': None,
      'master.chromium.gpu': 'Chromium GPU',
      'master.chromium.lkgr': 'Chromium LKGR',
      'master.chromium.memory': None,
      'master.chromium.memory.fyi': 'Chromium Memory FYI',
      'master.chromium.perf': 'Chromium Perf',
      'master.chromium.perf_av': 'Chromium Perf Av',
      'master.chromium.pyauto': 'Chromium PyAuto',
      'master.chromium.swarm': None,
      'master.chromium.webkit': 'Chromium Webkit',
      'master.chromiumos': 'ChromiumOS',
      'master.client.drmemory': None,  # make start fails
      'master.client.nacl': 'NativeClient',
      'master.client.nacl.branch.irt': 'NativeClientBranchIRT',
      'master.client.nacl.chrome': 'NativeClientChrome',
      'master.client.nacl.llvm': 'NativeClientLLVM',
      'master.client.nacl.ports': 'NativeClientPorts',
      'master.client.nacl.ppapi': 'NativeClientPPAPI',
      'master.client.nacl.sdk': 'NativeClientSDK',
      'master.client.nacl.toolchain': 'NativeClientToolchain',
      'master.client.pagespeed': 'PageSpeed',
      'master.client.sfntly': None,
      'master.client.skia': None,
      'master.client.syzygy': None,
      'master.client.tsan': None,  # make start fails
      'master.client.v8': 'V8',
      'master.client.webm': 'WebM',
      'master.experimental': None,
      'master.reserved': None,  # make start fails
      'master.tryserver.chromium': 'Chromium Try Server',
      'master.tryserver.nacl': 'NativeClient-Try',
  }
  return real_main(base_dir, expected)


if __name__ == '__main__':
  sys.exit(main())
