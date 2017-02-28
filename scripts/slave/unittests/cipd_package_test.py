#!/usr/bin/env python
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import logging
import os
import string
import subprocess
import sys

from multiprocessing.pool import ThreadPool

import test_env  # pylint: disable=W0403,W0611

import slave.infra_platform
import slave.robust_tempdir


# Instance-wide logger.
LOGGER = logging.getLogger('cipd_presubmit')


def resolve_package(pkg):
  LOGGER.info('Resolving CIPD package: %s %s', pkg.name, pkg.version)

  cmd = ['cipd', 'resolve', pkg.name, '-version', pkg.version]
  LOGGER.debug('Running command: %s', cmd)
  proc = subprocess.Popen(cmd,
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  stdout, _ = proc.communicate()
  LOGGER.debug('STDOUT:\n%s', stdout)

  if proc.returncode != 0:
    LOGGER.error('Failed to resolve CIPD package: %s %s',
        pkg.name, pkg.version)
    return False
  return True


def run_presubmit(basedir):
  """Validates that all of the referenced CIPD packages exist at their specified
  versions for all supported slave platforms.

  Any slave-side software that has CIPD package expectations should add their
  packages to this validation in order to assert their existence via PRESUBMIT.

  Returns (int): 0 if all packages exist, 1 if some are missing.
  """
  # Ensure that CIPD exists on this platform.
  #
  # We want to run this here so we can use the CIPD version that the slave
  # system uses. However, if this fails, we will fall back to the local system's
  # CIPD binary (in PATH) for the remainder of the tests.
  cipd_bootstrap_succeeded = False
  try:
    from slave import cipd_bootstrap_v2
    cipd_bootstrap_v2.high_level_ensure_cipd_client(basedir, None)
    cipd_bootstrap_succeeded = True
  except Exception:
    LOGGER.exception('Failed to ensure CIPD bootstrap.')

  # Collect our expected packages.
  from slave import logdog_bootstrap, remote_run
  packages = set()
  def _add_packages(src_fn):
    src_packages = set(src_fn())
    assert src_packages, (
        'Source %s yielded no CIPD packages.' % (src_fn.__module__,))
    packages.update(src_packages)

  _add_packages(cipd_bootstrap_v2.all_cipd_packages)
  _add_packages(logdog_bootstrap.all_cipd_packages)
  _add_packages(remote_run.all_cipd_packages)

  # Validate the set of packages.
  all_packages = set()
  for base_pkg in packages:
    for os_name, arch in slave.infra_platform.cipd_all_targets():
      pkg = base_pkg._replace(name=string.Template(base_pkg.name).substitute(
          os=os_name, arch=arch, platform='%s-%s' % (os_name, arch)))
      all_packages.add(pkg)

  # Fire up a thread pool to execute our resolutions in parallel.
  tp = ThreadPool(processes=10)
  try:
    result = tp.map(resolve_package, sorted(all_packages))
  finally:
    tp.close()
    tp.join()

  resolved = sum(result)
  LOGGER.info('Resolved %d package(s).', resolved)

  missing = len(result) - resolved
  if missing:
    LOGGER.error('%d CIPD package(s) could not be resolved.', missing)
    return 1

  if not cipd_bootstrap_succeeded:
    LOGGER.error('CIPD bootstrap did not successfully install.')
    return 1

  return 0


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--verbose', action='count', default=0,
                      help='Increase logging. Can be specified multiple times.')
  opts = parser.parse_args(argv[1:])

  # Verbosity.
  if opts.verbose == 0:
    level = logging.WARNING
  elif opts.verbose == 1:
    level = logging.INFO
  else:
    level = logging.DEBUG
  logging.getLogger().setLevel(level)

  basedir = os.path.join(test_env.BASE_DIR, 'cipd_presubmit')
  with slave.robust_tempdir.RobustTempdir(basedir) as rt:
    return run_presubmit(rt.tempdir())


if __name__ == '__main__':
  logging.basicConfig(level=logging.WARNING)
  sys.exit(main(sys.argv))
