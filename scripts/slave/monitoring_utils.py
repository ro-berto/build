# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import socket
import subprocess
import sys

# Install Infra build environment.
BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BUILD_ROOT, 'scripts'))

from slave import infra_platform


LOGGER = logging.getLogger('monitoring_utils')


PLATFORM_CONFIG = {
  'linux': {
    'run_cmd': ['/opt/infra-python/run.py'],
  },
  'mac': {
    'run_cmd': ['/opt/infra-python/run.py'],
  },
  'win': {
    'run_cmd': ['C:\\infra-python\\ENV\\Scripts\\python.exe',
                'C:\\infra-python\\run.py'],
  },
}


def _check_call(cmd, **kwargs):
  LOGGER.info('Executing command: %s', cmd)
  subprocess.check_call(cmd, **kwargs)


def write_build_monitoring_event(datadir, build_properties):
  # Ensure that all command components of "run_cmd" are available.
  config = PLATFORM_CONFIG.get(infra_platform.get()[0])
  if not config or 'run_cmd' not in config:
    LOGGER.warning('No run.py is defined for this platform.')
    return
  run_cmd_missing = [p for p in config['run_cmd'] if not os.path.exists(p)]
  if run_cmd_missing:
    LOGGER.warning('Unable to find run.py. Some components are missing: %s',
                   run_cmd_missing)
    return

  hostname = socket.getfqdn()
  if hostname:  # just in case getfqdn() returns None.
    hostname = hostname.split('.')[0]
  else:
    hostname = None

  try:
    cmd = config['run_cmd'] + [
       'infra.tools.send_monitoring_event',
       '--event-mon-output-file', os.path.join(datadir, 'log_request_proto'),
       '--event-mon-run-type', 'file',
       '--event-mon-service-name',
           'buildbot/master/master.%s'
           % build_properties.get('mastername', 'UNKNOWN'),
       '--build-event-build-name',
           build_properties.get('buildername', 'UNKNOWN'),
       '--build-event-build-number',
           str(build_properties.get('buildnumber', 0)),
       '--build-event-build-scheduling-time',
           str(1000*int(build_properties.get('requestedAt', 0))),
       '--build-event-type', 'BUILD',
       '--event-mon-timestamp-kind', 'POINT',
       # And use only defaults for credentials.
     ]
    # Add this conditionally so that we get an error in
    # send_monitoring_event log files in case it isn't present.
    if hostname:
      cmd += ['--build-event-hostname', hostname]
    _check_call(cmd)
  except Exception:
    LOGGER.warning("Failed to send monitoring event.", exc_info=True)
