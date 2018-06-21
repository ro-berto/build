# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


def distribute_subdir_slaves(master, builders, hostnames, slaves):
  """Distributes a list of builders to a list of hostnames with subdirs.

  Each builder will be assigned to one (subdir) slave. The different hosts will
  have an equal number (+/- 1) of subdir slaves.

  Example: Distributing builders [A, B, C, D, E] to slaves [X, Y] will result
  in [AX0, BY0, CX1, DY1, EX2], where e.g. CX1 is builder C on host X with
  subdir 1.
  """
  # Assuming lists are used to ensure determinism.
  assert isinstance(builders, list)
  assert isinstance(hostnames, list)

  # Assuming there are more or equal builders than hostnames.
  assert len(builders) >= len(hostnames)

  subdir_index = 0
  hostname_index = 0
  for builder in builders:
    if hostname_index >= len(hostnames):
      # All hostnames were used, rotate and advance the subdir index.
      hostname_index = 0
      subdir_index += 1
    slaves.append({
      'master': master,
      'builder': builder,
      'hostname': hostnames[hostname_index],
      'os': 'linux',
      'version': 'trusty',
      'bits': '64',
      'subdir': str(subdir_index),
    })
    hostname_index += 1


def verify_subdir_slaves(c):
  """Checks that subdir slaves are not auto-rebooted."""
  for s in c['slaves']:
    # Note, we can't import the class AutoRebootBuildSlave
    if '#' in s.slavename and s.__class__.__name__ == 'AutoRebootBuildSlave':
      raise Exception(
          'Subdir slaves must not auto-reboot. But found %s' % s.slavename)
