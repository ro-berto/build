#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Starts all masters and verify they can server /json/project fine.
"""

import collections
import contextlib
import glob
import logging
import optparse
import os
import subprocess
import sys
import threading
import time

import masters_util

port_master_lock = threading.Lock()
port_lock_map = collections.defaultdict(threading.Lock)

def do_master_imports():
  # Import scripts/slave/bootstrap.py to get access to the ImportMasterConfigs
  # function that will pull in every site_config for us. The master config
  # classes are saved as attributes of config_bootstrap.Master. The import
  # takes care of knowing which set of site_configs to use.
  import slave.bootstrap
  slave.bootstrap.ImportMasterConfigs()
  return getattr(sys.modules['config_bootstrap'], 'Master')

class pathstack:
  def __init__(self):
    self.saved_paths = []


  def backup_if_present(self, original_path):
    real_paths = glob.glob(original_path)
    for real_path in real_paths:
      bkup_path = real_path + '_'
      if os.path.exists(real_path) and not os.path.exists(bkup_path):
        if subprocess.call(['mv', real_path, bkup_path]) != 0:
          print >> sys.stderr, 'ERROR: Failed to rename %s to %s' % (
              real_path, bkup_path)
        else:
          self.saved_paths.insert(0, (real_path, bkup_path))


  def restore_backup(self):
    restores = self.saved_paths
    self.saved_paths = []
    restores.reverse()
    for (path, bkup) in restores:
      if subprocess.call(['rm', '-rf', path]) != 0:
        print >> sys.stderr, 'ERROR: Failed to remove %s' % path
      if subprocess.call(['mv', bkup, path]) != 0:
        print >> sys.stderr, 'ERROR: Failed to rename %s to %s' % (bkup, path)


def test_master(master, master_class, path):
  context = pathstack()
  if not masters_util.stop_master(master, path):
    return False
  try:
    all_ports = [master_class.master_port, master_class.master_port_alt,
                 master_class.slave_port]
    with port_master_lock:
      port_locks = [port_lock_map[p] for p in sorted(all_ports) if p]

    with contextlib.nested(*port_locks):
      start = time.time()
      # Try to backup paths we may not want to overwite.
      context.backup_if_present(os.path.join(path, 'twistd.log'))
      context.backup_if_present(os.path.join(path, 'git_poller_*.git'))
      try:
        if not masters_util.start_master(master, path, dry_run=True):
          return False
        name = master_class.project_name
        # We pass both the read/write and read-only ports, even though querying
        # either one alone would be sufficient sign of success.
        ports = [p for p in all_ports[:2] if p]
        res = masters_util.wait_for_start(master, name, path, ports)
        if not res:
          logging.info('%s Success in %1.1fs', master, (time.time() - start))
        return res
      finally:
        masters_util.stop_master(master, path)
  finally:
    context.restore_backup()


class MasterTestThread(threading.Thread):
  def __init__(self, master, master_class, master_path):
    self.master = master
    self.master_class = master_class
    self.master_path = master_path
    self.result = None
    super(MasterTestThread, self).__init__()

  def run(self):
    logging.info('Starting %s', self.master)
    with masters_util.temporary_password(
        os.path.join(self.master_path, '.apply_issue_password')):
      self.result = test_master(
          self.master, self.master_class, self.master_path)


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
  master_classes = do_master_imports()
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
  with masters_util.temporary_password(bot_pwd_path):
    master_threads = []
    for master in masters[:]:
      if not master in expected:
        continue
      masters.remove(master)
      classname = expected.pop(master)
      if not classname:
        skipped += 1
        continue
      cur_thread = MasterTestThread(
          master=master,
          master_class=getattr(master_classes, classname),
          master_path=os.path.join(base, master))
      cur_thread.start()
      master_threads.append(cur_thread)
    for cur_thread in master_threads:
      cur_thread.join(20)
      if cur_thread.result:
        print '\n=== Error running %s === ' % cur_thread.master
        print cur_thread.result
        failed.add(cur_thread.master)
      else:
        success += 1

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
  # Remove site_config's we don't add ourselves. Can cause issues when running
  # this test under a buildbot-spawned process.
  sys.path = [x for x in sys.path if not x.endswith('site_config')]
  base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  sys.path.extend(os.path.normpath(os.path.join(base_dir, d)) for d in (
      'site_config',
      os.path.join('..', 'build_internal', 'site_config'),
  ))
  expected = {
      'master.chromium': 'Chromium',
      'master.chromium.chrome': 'ChromiumChrome',
      'master.chromium.chromebot': 'ChromiumChromebot',
      'master.chromium.chromiumos': 'ChromiumChromiumOS',
      'master.chromium.endure': 'ChromiumEndure',
      'master.chromium.flaky': 'ChromiumFlaky',
      'master.chromium.fyi': 'ChromiumFYI',
      'master.chromium.gatekeeper': 'Gatekeeper',
      'master.chromium.git': 'ChromiumGIT',
      'master.chromium.gpu': 'ChromiumGPU',
      'master.chromium.gpu.fyi': 'ChromiumGPUFYI',
      'master.chromium.linux': 'ChromiumLinux',
      'master.chromium.lkgr': 'ChromiumLKGR',
      'master.chromium.mac': 'ChromiumMac',
      'master.chromium.memory': 'ChromiumMemory',
      'master.chromium.memory.fyi': 'ChromiumMemoryFYI',
      'master.chromium.perf': 'ChromiumPerf',
      'master.chromium.perf_av': 'ChromiumPerfAv',
      'master.chromium.pyauto': 'ChromiumPyauto',
      'master.chromium.swarm': 'ChromiumSwarm',
      'master.chromium.unused': None,
      'master.chromium.webkit': 'ChromiumWebkit',
      'master.chromium.webrtc': 'ChromiumWebRTC',
      'master.chromium.webrtc.fyi': 'ChromiumWebRTCFYI',
      'master.chromium.win': 'ChromiumWin',
      'master.chromiumos': 'ChromiumOS',
      'master.chromiumos.tryserver': None,
      'master.chromiumos.unused': None,
      'master.client.drmemory': 'DrMemory',
      'master.client.dynamorio': 'DynamoRIO',
      'master.client.dart': 'Dart',
      'master.client.dart.fyi': 'DartFYI',
      'master.client.libjingle': 'Libjingle',
      'master.client.libyuv': 'Libyuv',
      'master.client.nacl': 'NativeClient',
      'master.client.nacl.chrome': 'NativeClientChrome',
      'master.client.nacl.llvm': 'NativeClientLLVM',
      'master.client.nacl.ports': 'NativeClientPorts',
      'master.client.nacl.ragel': 'NativeClientRagel',
      'master.client.nacl.sdk': 'NativeClientSDK',
      'master.client.nacl.sdk.addin': 'NativeClientSDKAddIn',
      'master.client.nacl.sdk.mono': 'NativeClientSDKMono',
      'master.client.nacl.toolchain': 'NativeClientToolchain',
      'master.client.omaha': 'Omaha',
      'master.client.pagespeed': 'PageSpeed',
      'master.client.sfntly': None,
      'master.client.skia': None,
      'master.client.syzygy': None,
      'master.client.toolkit': None,
      'master.client.tsan': None,  # make start fails
      'master.client.unused': None,
      'master.client.v8': 'V8',
      'master.client.webrtc': 'WebRTC',
      'master.experimental': None,
      'master.reserved': None,  # make start fails
      'master.tryserver.chromium': 'TryServer',
      'master.tryserver.chromium.linux': 'TryServerLinux',
      'master.tryserver.nacl': 'NativeClientTryServer',
      'master.tryserver.unused': None,
      'master.tryserver.webrtc': 'WebRTCTryServer',
      'master.devtools': 'DevTools',
  }
  return real_main(base_dir, expected)


if __name__ == '__main__':
  sys.exit(main())
