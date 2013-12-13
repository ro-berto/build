#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This file is needed by Google Cloud Compute Engine slaves."""

import json
import logging
import platform
import socket
import sys

import slave_machine  # pylint: disable-msg=F0401


# A mapping between sys.platform values and the corresponding swarm name
# for that platform.
PLATFORM_MAPPING = {
  'cygwin': 'Windows',
  'darwin': 'Mac',
  'linux2': 'Linux',
  'win32': 'Windows',
}


def WriteJsonToFile(filepath, data):
  """Writes out a json file.

  Returns True on success.
  """
  try:
    with open(filepath, mode='w') as f:
      f.write(json.dumps(data, sort_keys=True, indent=2))
    return True
  except IOError as e:
    logging.error('Cannot write file %s: %s\n%s', filepath, data, e)
    return False


def ConvertMacVersion(version):
  """Returns the major OSX version, like 10.7, 10.8, etc."""
  version_parts = version.split('.')

  assert len(version_parts) >= 2, 'Unable to determine Mac version'
  return '.'.join(version_parts[:2])


def ConvertWindowsVersion(version):
  """Returns the major Windows version, like 5.0, 5.1, 6.2, etc."""
  if '-' in version:
    version = version.split('-')[1]

  version_parts = version.split('.')
  assert len(version_parts) >= 2,  'Unable to determine Windows version'

  return '.'.join(version_parts[:2])


def GetPlatformVersion():
  if sys.platform == 'cygwin':
    return ConvertWindowsVersion(platform.system())

  elif sys.platform == 'win32':
    return ConvertWindowsVersion(platform.version())

  elif sys.platform == 'darwin':
    return ConvertMacVersion(platform.mac_ver()[0])

  elif sys.platform == 'linux2':
    # No need to convert the linux value since it already returns what we
    # want (like '12.04' or '10.04' for ubuntu slaves).
    return platform.linux_distribution()[1]

  raise Exception('Unable to determine platform version')


def GetArchitectureSize():
  """Returns the number of bits in the systems architecture.

  Currently this only works on 32-bit or 64-bit systems.
  """
  # TODO(maruel): Returns the python build bitness, not the OS bitness.
  return '64' if sys.maxsize > 2**32 else '32'


def GetDimensions(hostname, platform_id, platform_version):
  """Returns a dictionary of attributes representing this machine.

  Returns:
    A dictionary of the attributes of the machine.
  """
  if platform_id not in PLATFORM_MAPPING:
    logging.error('Running on an unknown platform, %s, unable to '
                  'generate dimensions', platform_id)
    return {}

  platform_name = PLATFORM_MAPPING[platform_id]

  return {
    'dimensions': {
      'bits': GetArchitectureSize(),
      'machine': platform.machine(),
      'os': [
          platform_name,
          platform_name + '-' + platform_version,
      ],
    },
    'tag': hostname,
  }


def GetChromiumDimensions(hostname, platform_id, platform_version):
  """Returns chromium infrastructure specific dimensions."""
  dimensions = GetDimensions(hostname, platform_id, platform_version)
  if not dimensions:
    return dimensions

  hostname = dimensions['tag']
  # Get the vlan of this machine from the hostname when it's in the form
  # '<host>-<vlan>'.
  if '-' in hostname:
    dimensions['dimensions']['vlan'] = hostname.split('-')[-1]
    # Replace vlan starting with 'c' to 'm'.
    if dimensions['dimensions']['vlan'][0] == 'c':
      dimensions['dimensions']['vlan'] = (
          'm' + dimensions['dimensions']['vlan'][1:])
  return dimensions


def GenerateAndWriteDimensions(dimensions_file):
  """Generates and stores the dimensions for this machine.

  Args:
    dimensions_file: The location to write the dimension file to.

  Returns:
    0 if the dimension file is successfully generated, 1 otherwise.
  """
  hostname = socket.gethostname().lower().split('.', 1)[0]
  dimensions = GetChromiumDimensions(hostname, sys.platform,
                                     GetPlatformVersion())

  if not WriteJsonToFile(dimensions_file, dimensions):
    return 1

  return 0


def main():
  # TODO(csharp): Write the logs to a local file.

  # TODO(csharp): Update the auto start code to ensure the dimensions that are
  # written out are the ones the machine will read.
  GenerateAndWriteDimensions('dimensions.in')

  slave_machine.Restart()


if __name__ == '__main__':
  sys.exit(main())
