#!/usr/bin/env vpython
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import subprocess
import sys

import test_env  # pylint: disable=relative-import

import slave.infra_platform
import slave.robust_tempdir


CIPD_CLIENT = 'cipd'
if sys.platform == 'win32':
  CIPD_CLIENT += '.bat'


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
  from slave import cipd_bootstrap_v2
  cipd_bootstrap_v2.high_level_ensure_cipd_client(
      basedir, None, track=cipd_bootstrap_v2.STAGING)

  from slave import logdog_bootstrap, remote_run

  manifests = []
  manifests.extend(cipd_bootstrap_v2.all_cipd_manifests())
  manifests.extend(logdog_bootstrap.all_cipd_manifests())
  manifests.extend(remote_run.all_cipd_manifests())

  fail = False

  for manifest in manifests:
    assert manifest

    lines = []
    for os_name, arch in slave.infra_platform.cipd_all_targets():
      lines.append('$VerifiedPlatform %s-%s' % (os_name, arch))
    for pkg in manifest:
      lines.append('%s %s' % (pkg.name, pkg.version))
    ensure_file = '\n'.join(lines)

    logging.debug('Verifying ensure file:\n%s', ensure_file)
    proc = subprocess.Popen(
        [CIPD_CLIENT, 'ensure-file-verify', '-ensure-file=-'],
        stdin=subprocess.PIPE)
    proc.communicate(input=ensure_file)

    if proc.returncode:
      logging.error('Failed, see logs')
      fail = True

  return 1 if fail else 0


def main(_argv):
  basedir = os.path.join(test_env.BASE_DIR, 'cipd_presubmit')
  with slave.robust_tempdir.RobustTempdir(basedir) as rt:
    return run_presubmit(rt.tempdir())


if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  sys.exit(main(sys.argv))
