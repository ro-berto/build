#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Initialize the environment variables and start the buildbot slave.
"""

import os
import shutil
import subprocess
import sys

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))


def remove_all_vars_except(dictionary, keep):
  """Remove all keys from the specified dictionary except those in !keep|"""
  for key in set(dictionary.keys()) - set(keep):
    dictionary.pop(key)


def Reboot():
  print "Rebooting..."
  if sys.platform.startswith('win'):
    subprocess.call(['shutdown', '-r', '-f', '-t', '1'])
  elif sys.platform in ('darwin', 'posix', 'linux2'):
    subprocess.call(['sudo', 'shutdown', '-r', 'now'])
  else:
    raise NotImplementedError('Implement Reboot function')


def HotPatchSlaveBuilder():
  """We could override the SlaveBuilder class but it's way simpler to just
  hotpatch it."""
  # pylint: disable=E0611,F0401
  try:
    # buildbot 0.7.12
    from buildbot.slave.bot import SlaveBuilder
  except ImportError:
    # buildbot 0.8.x
    from buildslave.bot import SlaveBuilder
  old_remote_shutdown = SlaveBuilder.remote_shutdown

  def rebooting_remote_shutdown(self):
    old_remote_shutdown(self)
    Reboot()

  SlaveBuilder.remote_shutdown = rebooting_remote_shutdown


def FixSubversionConfig():
  if sys.platform == 'win32':
    dest = os.path.join(os.environ['APPDATA'], 'Subversion', 'config')
  else:
    dest = os.path.join(os.environ['HOME'], '.subversion', 'config')
  shutil.copyfile('config', dest)


def error(msg):
  print >> sys.stderr, msg
  sys.exit(1)


def main():
  # Change the current directory to the directory of the script.
  os.chdir(SCRIPT_PATH)
  build_dir = os.path.dirname(SCRIPT_PATH)
  # Directory containing build/slave/run_slave.py
  root_dir = os.path.dirname(build_dir)
  depot_tools = os.path.join(root_dir, 'depot_tools')

  # Make sure the current python path is absolute.
  old_pythonpath, os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'], ''
  for path in old_pythonpath.split(os.pathsep):
    os.environ['PYTHONPATH'] += os.path.abspath(path) + os.pathsep

  # Update the python path.
  python_path = [
    os.path.join(build_dir, 'site_config'),
    os.path.join(build_dir, 'scripts'),
    os.path.join(build_dir, 'scripts', 'release'),
    os.path.join(build_dir, 'third_party'),
    os.path.join(root_dir, 'build_internal', 'site_config'),
    os.path.join(root_dir, 'build_internal', 'symsrc'),
    SCRIPT_PATH,  # Include the current working directory by default.
  ]
  os.environ['PYTHONPATH'] += os.pathsep.join(python_path)

  # Add these in from of the PATH too.
  sys.path = python_path + sys.path

  os.environ['CHROME_HEADLESS'] = '1'
  os.environ['PAGER'] = 'cat'

  # Platform-specific initialization.

  if sys.platform.startswith('win'):
    # list of all variables that we want to keep
    env_var = [
        'APPDATA',
        'BUILDBOT_ARCHIVE_FORCE_SSH',
        'CHROME_HEADLESS',
        'CHROMIUM_BUILD',
        'COMSPEC',
        'COMPUTERNAME',
        'DXSDK_DIR',
        'HOMEDRIVE',
        'HOMEPATH',
        'LOCALAPPDATA',
        'NUMBER_OF_PROCESSORS',
        'OS',
        'PATH',
        'PATHEXT',
        'PROCESSOR_ARCHITECTURE',
        'PROCESSOR_ARCHITEW6432',
        'PROGRAMFILES',
        'PROGRAMW6432',
        'PYTHONPATH',
        'SYSTEMDRIVE',
        'SYSTEMROOT',
        'TEMP',
        'TESTING_MASTER',
        'TESTING_MASTER_HOST',
        'TESTING_SLAVENAME',
        'TMP',
        'USERNAME',
        'USERDOMAIN',
        'USERPROFILE',
        'WINDIR',
    ]

    remove_all_vars_except(os.environ, env_var)

    # Extend the env variables with the chrome-specific settings.
    slave_path = [
        depot_tools,
        # Reuse the python executable used to start this script.
        os.path.dirname(sys.executable),
        os.path.join(os.environ['SYSTEMROOT'], 'system32'),
        os.path.join(os.environ['SYSTEMROOT'], 'system32', 'WBEM'),
    ]
    # build_internal/tools contains tools we can't redistribute.
    tools = os.path.join(root_dir, 'build_internal', 'tools')
    if os.path.isdir(tools):
      slave_path.append(os.path.abspath(tools))
    os.environ['PATH'] = os.pathsep.join(slave_path)
    os.environ['LOGNAME'] = os.environ['USERNAME']

  elif sys.platform in ('darwin', 'posix', 'linux2'):
    # list of all variables that we want to keep
    env_var = [
        'CCACHE_DIR',
        'CHROME_ALLOCATOR',
        'CHROME_HEADLESS',
        'DISPLAY',
        'DISTCC_DIR',
        'HOME',
        'HOSTNAME',
        'LANG',
        'LOGNAME',
        'PAGER',
        'PATH',
        'PWD',
        'PYTHONPATH',
        'SHELL',
        'SSH_AGENT_PID',
        'SSH_AUTH_SOCK',
        'SSH_CLIENT',
        'SSH_CONNECTION',
        'SSH_TTY',
        'TESTING_MASTER',
        'TESTING_MASTER_HOST',
        'TESTING_SLAVENAME',
        'USER',
        'USERNAME',
    ]

    remove_all_vars_except(os.environ, env_var)
    slave_path = [
        depot_tools, '/usr/bin', '/bin',
        '/usr/sbin', '/sbin', '/usr/local/bin'
    ]
    os.environ['PATH'] = os.pathsep.join(slave_path)

  else:
    error('Platform %s is not implemented yet' % sys.platform)

  FixSubversionConfig()

  HotPatchSlaveBuilder()
  import twisted.scripts.twistd as twistd
  twistd.run()


if '__main__' == __name__:
  main()
