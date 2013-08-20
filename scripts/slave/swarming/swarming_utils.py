#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Code to find swarming_client."""

import os


def find_client(base_dir):
  """Returns the path to swarming_client if found."""
  src_swarming_client = os.path.join(
      base_dir, 'src', 'tools', 'swarming_client')
  if os.path.isdir(src_swarming_client):
    return src_swarming_client

  # This is the previous path. This can be removed around 2013-12-01.
  src_swarm_client = os.path.join(base_dir, 'src', 'tools', 'swarm_client')
  if os.path.isdir(src_swarm_client):
    return src_swarm_client
