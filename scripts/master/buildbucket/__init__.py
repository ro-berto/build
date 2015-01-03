# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""buildbucket module implements buildbucket-buildbot integration.

The main entry point is buildbucket.setup() that accepts master configuration
dict with other buildbucket parameters and configures master to run builds
scheduled on buildbucket service.

Example:
  buildbucket.setup(
      c,  # Configuration object.
      build_namespaces=['qo'],
      service_json_key_filename=ActiveMaster.buildbucket_json_key_filename,
  )

"""

import functools
import os

from .integration import BuildBucketIntegrator
from .poller import BuildBucketPoller
from .status import BuildBucketStatus
from . import client


def setup(config, build_namespaces, service_json_key_filename,
          poll_interval=10, buildbucket_hostname=None, dry_run=None):
  """Configures a master to lease, schedule and update builds on buildbucket.

  Args:
    config (dict): master configuration dict.
    build_namespaces (list of str): a list of build namespaces to poll.
      Namespaces are specified at build submission time.
    service_json_key_filename (str): JSON key for buildbucket authentication.
      Can be received from a buildbucket maintainer.
    poll_interval (int): frequency of polling, in seconds. Defaults to 10.
    buildbucket_hostname (str): if not None, override the default buildbucket
      service url.
    dry_run (bool): whether to run buildbucket in a dry-run mode.
  """
  assert isinstance(config, dict), 'config must be a dict'
  assert build_namespaces, 'build namespaces are not specified'
  assert isinstance(build_namespaces, list), 'build_namespaces must be a list'
  assert all(isinstance(n, basestring) for n in build_namespaces), (
        'all build namespaces must be strings')
  assert service_json_key_filename, 'service_json_key_filename not specified'

  if dry_run is None:
    dry_run = 'POLLER_DRY_RUN' in os.environ

  integrator = BuildBucketIntegrator(build_namespaces)

  create_http = functools.partial(
      client.create_authorized_http, service_json_key_filename)
  buildbucket_service_factory = functools.partial(
      client.create_buildbucket_service, create_http, buildbucket_hostname)

  poller = BuildBucketPoller(
      integrator=integrator,
      buildbucket_service_factory=buildbucket_service_factory,
      poll_interval=poll_interval,
      dry_run=dry_run,
  )
  status = BuildBucketStatus(integrator)
  config.setdefault('change_source', []).append(poller)
  config.setdefault('status', []).append(status)
