#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Launches a daemon to monitor android device temperaures.

This script will repeatedly poll the given devices for their
temperatures every 60 seconds via adb and uploads them for monitoring
through infra's ts_mon.
"""

import json
import logging
import os
import optparse
import re
import signal
import subprocess
import sys
import time

# Various names of sensors used to measure cpu temp
_CPU_TEMP_SENSORS = [
  # most nexus devices
  'tsens_tz_sensor0',
  # android one
  'mtktscpu',
  # nexus 9
  'CPU-therm',
]

# TODO(bpastene): change the following if infra.git becomes a checked
# out repo on slaves instead of a cipd managed package.

# Location of the infra-python package's run script.
_RUN_PY = '/opt/infra-python/run.py'


def get_device_args(adb_path, slave_name, device):
  bat_temp = None
  cpu_temp = None
  # Search for the file that the _CPU_TEMP_SENSOR dumps to and cat it.
  cmd = [adb_path, '-s', device, 'shell',
         'grep -lE "%s" /sys/class/thermal/thermal_zone*/type'
           % ('|'.join(_CPU_TEMP_SENSORS))]
  try:
    cpu_temp_files = subprocess.check_output(cmd)
    if (len(cpu_temp_files.splitlines()) == 1):
        cpu_temp_file = re.sub('type$', 'temp', cpu_temp_files.strip())
        cmd = [adb_path, '-s', device, 'shell',
               'cat %s' % (cpu_temp_file)]
        file_contents = subprocess.check_output(cmd).strip()
        # Most devices report cpu temp in degrees (C), but a few
        # can report it in thousandths of a degree. If this is in thousandths,
        # chop off the trailing three digits to convert to degrees
        if (len(file_contents) == 5):
          file_contents = file_contents[:2]
        cpu_temp = int(file_contents)
  except (subprocess.CalledProcessError, TypeError, ValueError):
    cpu_temp = None

  # Dump system battery info and grab the temp.
  cmd = [adb_path, '-s', device, 'shell', 'dumpsys battery']
  try:
    battery_info = subprocess.check_output(cmd)
    for line in battery_info.splitlines():
      m = re.match('^\s*temperature: ([0-9]+)\s*$', line)
      if m:
        bat_temp = int(m.group(1))
  except (subprocess.CalledProcessError, TypeError, ValueError):
    bat_temp = None

  cpu_dict = {'name': "dev/cpu/temperature",
              'value': cpu_temp,
              'device_id': device,
              'slave': slave_name}
  cpu_temp_args = ['--float', json.dumps(cpu_dict)] if cpu_temp else []
  battery_dict = {'name': 'dev/battery/temperature',
                  'value': bat_temp,
                  'device_id': device,
                  'slave': slave_name}
  bat_temp_args = ['--float', 
                   json.dumps(battery_dict)] if bat_temp else []
  return cpu_temp_args + bat_temp_args


def main(adb_path,
         devices_json,
         slave_name):
  """Launches the device temperature monitor.

  Polls the devices for their battery and cpu temperatures
  every 60 seconds and uploads them for monitoring through infra's
  ts_mon. Fully qualified, the metric names would be
  /chrome/infra/dev/(cpu|battery)/temperature

  Args:
    adb_path: Path to adb binary.
    devices_json: Json list of device serials to poll.
    slave_name: Name of the buildbot slave.
  """

  devices = json.loads(devices_json)
  while True:
    for device in devices:
      upload_cmd_args = get_device_args(adb_path, slave_name, device)

      cmd = [_RUN_PY, 'infra.tools.send_ts_mon_values'] + upload_cmd_args
      try:
        subprocess.Popen(cmd)
      except OSError:
        logging.exception('Unable to call %s', _RUN_PY)

    time.sleep(60)


if __name__ == '__main__':
  sys.exit(main(*sys.argv[1:]))
