#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Code to find swarming_client."""

import os
import sys

from common import find_depot_tools  # pylint: disable=W0611

# From depot_tools/
import subprocess2


def find_client(base_dir):
  """Returns the path to swarming_client if found.

  |base_dir| will be in general os.getcwd(), so the script is very dependent on
  CWD. CWD should be the base directory of the checkout. It has always been the
  case.
  """
  src_swarming_client = os.path.join(
      base_dir, 'src', 'tools', 'swarming_client')
  if os.path.isdir(src_swarming_client):
    return src_swarming_client

  # This is the previous path. This can be removed around 2013-12-01.
  src_swarm_client = os.path.join(base_dir, 'src', 'tools', 'swarm_client')
  if os.path.isdir(src_swarm_client):
    return src_swarm_client


def get_version(client):
  """Returns the version of swarming.py client tool as a tuple, if available."""
  try:
    version = subprocess2.check_output(
        [
          sys.executable,
          os.path.join(client, 'swarming.py'),
          '--version',
        ])
  except (subprocess2.CalledProcessError, OSError):
    return None
  version = tuple(map(int, version.split('.')))
  print('Detected swarming.py version %s' % '.'.join(map(str, version)))
  return version
