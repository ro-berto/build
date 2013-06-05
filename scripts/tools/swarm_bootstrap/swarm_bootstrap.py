#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Manages the initial bootstrapping.

Automatically generates the dimensions for the current machine and stores them
in the given file.
"""

import cStringIO
import json
import logging
import optparse
import os
import socket
import subprocess
import sys
import urllib2
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# A mapping between sys.platform values and the corresponding swarm name
# for that platform.
PLATFORM_MAPPING = {
    'darwin': 'Mac',
    'cygwin': 'Windows',
    'linux2': 'Linux',
    'win32': 'Windows'
}


def WriteJsonToFile(filepath, data):
  return WriteToFile(filepath, json.dumps(data, sort_keys=True, indent=2))


def WriteToFile(filepath, content):
  """Writes out a json file.

  Returns True on success.
  """
  try:
    with open(filepath, mode='w') as f:
      f.write(content)
    return True
  except IOError as e:
    logging.error('Cannot write file %s: %s', filepath, e)
    return False


def GetDimensions():
  """Returns a dictionary of attributes representing this machine.

  Returns:
    A dictionary of the attributes of the machine.
  """
  if sys.platform not in PLATFORM_MAPPING:
    logging.error('Running on an unknown platform, %s, unable to '
                  'generate dimensions', sys.platform)
    return {}

  hostname = socket.gethostname().lower().split('.', 1)[0]
  return {
    'dimensions': {
      'os': PLATFORM_MAPPING[sys.platform],
    },
    'tag': hostname,
  }


def GetChromiumDimensions():
  """Returns chromium infrastructure specific dimensions."""
  dimensions = GetDimensions()
  if not dimensions:
    return dimensions

  hostname = dimensions['tag']
  # Get the vlan of this machine from the hostname when it's in the form
  # '<host>-<vlan>'.
  if '-' in hostname:
    dimensions['dimensions']['vlan'] = hostname.split('-')[1]
  return dimensions


def DownloadSwarmBot(swarm_server):
  """Downloads the latest version of swarm_bot code directly from the Swarm
  server.

  It is assumed that this will download a file named slave_machine.py.

  Returns True on success.
  """
  swarm_get_code_url = swarm_server.rstrip('/') + '/get_slave_code'
  try:
    response = urllib2.urlopen(swarm_get_code_url)
  except urllib2.URLError as e:
    logging.error('Unable to download swarm slave code from %s.\n%s',
                  swarm_get_code_url, e)
    return False

  # 'response' doesn't act exactly like a file so we can't pass it directly
  # to the zipfile reader.
  z = zipfile.ZipFile(cStringIO.StringIO(response.read()), 'r')
  try:
    z.extractall()
  finally:
    z.close()
  return True


def CreateStartSlave(filepath):
  """Creates the python scripts that is called to restart the swarm bot slave.

  See src/swarm_bot/slave_machine.py in the swarm server code about why this is
  needed.
  """
  content = (
    'import slave_machine\n'
    'slave_machine.Restart()\n')
  return WriteToFile(filepath, content)


def SetupAutoStartupWin(command):
  """Uses Startup folder in the Start Menu."""
  # TODO(maruel): Not always true. Read from registry if needed.
  filepath = os.path.expanduser(
      '~\\AppData\\Roaming\\Microsoft\\Windows\\'
      'Start Menu\\Programs\\Startup\\run_swarm_bot.bat')
  content = '@cd /d ' + BASE_DIR + ' && ' + ' '.join(command)
  return WriteToFile(filepath, content)


def SetupAutoStartupPosix(command):
  """Uses crontab."""
  # The \n is very important.
  content = '@reboot cd %s && %s\n' % (BASE_DIR, ' '.join(command))
  if not WriteToFile('mycron', content):
    return False

  try:
    # It returns 1 if there was no cron job set.
    subprocess.call(['crontab', '-r'])
    subprocess.check_call(['crontab', 'mycron'])
  finally:
    os.remove('mycron')
  return True


def main():
  # Simplify the code by setting the current directory as the directory
  # containing this file.
  os.chdir(BASE_DIR)

  parser = optparse.OptionParser(description=sys.modules[__name__].__doc__)
  parser.add_option('-d', '--dimensionfile', default='dimension.in')
  parser.add_option('-s', '--swarm-server')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Set logging level to DEBUG. Optional. Defaults to '
                    'ERROR level.')
  (options, args) = parser.parse_args()

  if args:
    parser.error('Unexpected argument, %s' % args)
  if not options.swarm_server:
    parser.error('Swarm server is required.')

  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.ERROR)

  options.dimensionfile = os.path.abspath(options.dimensionfile)

  print('Generating the machine dimensions...')
  if not WriteJsonToFile(options.dimensionfile, GetChromiumDimensions()):
    return 1

  print('Downloading newest swarm_bot code...')
  if not DownloadSwarmBot(options.swarm_server):
    return 1

  slave_machine = os.path.join(BASE_DIR, 'slave_machine.py')
  if not os.path.isfile(slave_machine):
    print('Failed to find %s' % slave_machine)
    return 1

  print('Create start_slave.py script...')
  if not CreateStartSlave(os.path.join(BASE_DIR, 'start_slave.py')):
    return 1

  print('Setup up swarm script to run on startup...')
  command = [
    sys.executable,
    slave_machine,
    '-a', options.swarm_server,
    '-p', '443',
    '-r', '400',
    '-v',
    options.dimensionfile,
  ]
  if sys.platform == 'win32':
    if not SetupAutoStartupWin(command):
      return 1
  else:
    if not SetupAutoStartupPosix(command):
      return 1

  print('Rebooting...')
  if sys.platform == 'win32':
    result = subprocess.call(['shutdown', '-r', '-f', '-t', '1'])
  else:
    result = subprocess.call(['sudo', 'shutdown', '-r', 'now'])
  if result:
    print('Please reboot the slave manually.')

  return result


if __name__ == '__main__':
  sys.exit(main())
