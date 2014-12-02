# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""crbuild module implements crbuild-buildbot integration.

The main entry point is crbuild.setup() that accepts master configuration dict
with other crbuild parameters and configures master to run builds scheduled on
crbuild service.

Example:
  crbuild.setup(
      c,  # Configuration object.
      build_namespaces=['qo'],
      service_json_key_filename=ActiveMaster.crbuild_service_json_key_filename,
  )

"""

import os

from .integration import CrbuildIntegrator
from .poller import CrbuildPoller
from .status import CrbuildStatus
from . import client


def setup(config, build_namespaces, service_json_key_filename,
          poll_interval=10, dry_run=None):
  """Configures a master to lease, schedule and update builds on crbuild.

  Args:
    config (dict): master configuration dict.
    build_namespaces (list of str): a list of build namespaces to poll.
      Namespaces are specified at build submission time.
    service_json_key_filename (str): JSON key for crbuild authentication. Can be
      received from a crbuild maintainer.
    poll_interval (int): frequency of polling, in seconds. Defaults to 10.
    dry_run (bool): whether to run crbuild in a dry-run mode.
  """
  assert isinstance(config, dict), 'config must be a dict'
  assert build_namespaces, 'build namespaces are not specified'
  assert isinstance(build_namespaces, list), 'build_namespaces must be a list'
  assert all(isinstance(n, basestring) for n in build_namespaces), (
        'all build namespaces must be strings')
  assert service_json_key_filename, 'service_json_key_filename not specified'

  if dry_run is None:
    dry_run = 'POLLER_DRY_RUN' in os.environ

  integrator = CrbuildIntegrator(build_namespaces)

  create_http = lambda: client.create_authorized_http(service_json_key_filename)
  build_service_factory = lambda: client.create_build_service(create_http)

  poller = CrbuildPoller(
      integrator=integrator,
      build_service_factory=build_service_factory,
      poll_interval=poll_interval,
      dry_run=dry_run,
  )
  status = CrbuildStatus(integrator)
  config.setdefault('change_source', []).append(poller)
  config.setdefault('status', []).append(status)
