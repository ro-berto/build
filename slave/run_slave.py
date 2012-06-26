#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Initialize the environment variables and start the buildbot slave.
"""

import os
import shutil
import subprocess
import sys
import time

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
needs_reboot = False


def remove_all_vars_except(dictionary, keep):
  """Remove all keys from the specified dictionary except those in !keep|"""
  for key in set(dictionary.keys()) - set(keep):
    dictionary.pop(key)


def Reboot():
  """Reboot system according to platform type.

  On some platforms, like Mac, run_slave.py is launched by a system launcher
  agent.  In those cases, any children of this process will get killed by the
  agent if they're still running after we exit.  Our strategy to ensure our
  system reboot command is issued without getting killed before sudo runs
  shutdown for us is:

  1. Only call Reboot() from run_slave.py, and not from within the
     remote_shutdown method.  This allows us to avoid the possibility of
     the sudo being executed and being interrupted by the Twisted service
     as it shuts down due to a separate reactor.stop() call.  (This was just
     the only theory available for why some bots would not reboot at times.)

  2. Use subprocess.call() instead of Popen() to ensure that run_slave.py
     doesn't exit at all when it calls Reboot().  This ensures that run_slave.py
     won't exit and trigger any cleanup routines by whatever launched
     run_slave.py.

  Since our strategy depends on Reboot() never returning, raise an exception
  if that should occur to make it clear in logs that an error condition is
  occurring somewhere.
  """
  print "Rebooting..."
  if sys.platform.startswith('win'):
    subprocess.call(['shutdown', '-r', '-f', '-t', '1'])
  elif sys.platform in ('darwin', 'posix', 'linux2'):
    subprocess.call(['sudo', 'shutdown', '-r', 'now'])
  else:
    raise NotImplementedError('Implement Reboot function')
  print 'reboot requested, going to sleep...'
  while True:
    time.sleep(60)
  raise Exception('run_slave.Reboot() should not return but would have')


def HotPatchSlaveBuilder():
  """We could override the SlaveBuilder class but it's way simpler to just
  hotpatch it."""
  # pylint: disable=E0611,F0401
  try:
    # buildbot 0.7.12
    from buildbot.slave.bot import log, Bot, SlaveBuilder
  except ImportError:
    # buildbot 0.8.x
    from buildslave.bot import log, Bot, SlaveBuilder
  old_remote_shutdown = SlaveBuilder.remote_shutdown

  def rebooting_remote_shutdown(self):
    """Set a reboot flag and stop the reactor so when the slave exits we reboot.

    Note that Buildbot masters >= 0.8.3 try to stop the slave in 2 ways.  First
    they try the new way which works for slaves running based on Buildbot 0.8.3
    or later.  If the slave is running something earlier than Buildbot 0.8.3,
    the master will then try the old way which will be what actually restarts
    those older slaves.

    For older slaves, the new way is always run first, and this causes the
    "No such method 'remote_shutdown'" message that is seen in the old slaves'
    twistd.log files.  This error is safe to ignore since the master will have
    immediately tried the old way and correctly restarted those slaves after
    that error is caught.
    """
    global needs_reboot
    needs_reboot = True
    old_remote_shutdown(self)

  SlaveBuilder.remote_shutdown = rebooting_remote_shutdown

  Bot.old_remote_setBuilderList = Bot.remote_setBuilderList
  def cleanup(self, wanted):
    retval = self.old_remote_setBuilderList(wanted)
    wanted_dirs = ['info', 'cert', '.svn'] + [r[1] for r in wanted]
    for d in os.listdir(self.basedir):
      # Delete build.dead directories.
      possible_build_dead = os.path.join(self.basedir, d, 'build.dead')
      if os.path.isdir(possible_build_dead):
        from common import chromium_utils
        log.msg("Deleting unwanted directory %s" % possible_build_dead)
        chromium_utils.RemoveDirectory(possible_build_dead)

      # Delete old slave directories.
      if d not in wanted_dirs and os.path.isdir(os.path.join(self.basedir, d)):
        log.msg("Deleting unwanted directory %s" % d)
        from common import chromium_utils
        chromium_utils.RemoveDirectory(os.path.join(self.basedir, d))
    return retval
  Bot.new_remote_setBuilderList = cleanup
  Bot.remote_setBuilderList = Bot.new_remote_setBuilderList


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
  # Use adhoc argument parsing because of twisted's twisted argument parsing.
  use_buildbot_8 = False
  if '--use_buildbot_8' in sys.argv:
    sys.argv.remove('--use_buildbot_8')
    use_buildbot_8 = True

  # Change the current directory to the directory of the script.
  os.chdir(SCRIPT_PATH)
  build_dir = os.path.dirname(SCRIPT_PATH)
  # Directory containing build/slave/run_slave.py
  root_dir = os.path.dirname(build_dir)
  depot_tools = os.path.join(root_dir, 'depot_tools')

  if not os.path.isdir(depot_tools):
    error('You must put a copy of depot_tools in %s' % depot_tools)
  bot_password_file = os.path.normpath(
      os.path.join(build_dir, 'site_config', '.bot_password'))
  if not os.path.isfile(bot_password_file):
    error('You forgot to put the password at %s' % bot_password_file)

  # Make sure the current python path is absolute.
  old_pythonpath = os.environ.get('PYTHONPATH', '')
  os.environ['PYTHONPATH']  = ''
  for path in old_pythonpath.split(os.pathsep):
    if path:
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

  if use_buildbot_8:
    python_path.append(
        os.path.join(build_dir, 'third_party', 'buildbot_slave_8_4'))
    python_path.append(os.path.join(build_dir, 'third_party', 'twisted_10_2'))
  else:
    python_path.append(os.path.join(build_dir, 'third_party', 'buildbot_7_12'))
    python_path.append(os.path.join(build_dir, 'third_party', 'twisted_8_1'))

  os.environ['PYTHONPATH'] = (
      os.pathsep.join(python_path) + os.pathsep + os.environ['PYTHONPATH'])

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
        'VS100COMNTOOLS',
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
        'CHROME_VALGRIND_NUMCPUS',
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
        depot_tools,
        # Reuse the python executable used to start this script.
        os.path.dirname(sys.executable),
        '/usr/bin', '/bin', '/usr/sbin', '/sbin', '/usr/local/bin'
    ]
    os.environ['PATH'] = os.pathsep.join(slave_path)

  else:
    error('Platform %s is not implemented yet' % sys.platform)

  # This envrionment is defined only when testing the slave on a dev machine.
  if 'TESTING_MASTER' not in os.environ:
    # Don't overwrite the ~/.subversion/config file when TESTING_MASTER is set.
    FixSubversionConfig()
    # Do not reboot the workstation or delete unknown directories in the current
    # directory.
    HotPatchSlaveBuilder()

  import twisted.scripts.twistd as twistd
  twistd.run()
  if needs_reboot:
    # Send the appropriate system shutdown command.
    Reboot()
    # This line should not be reached.


def UpdateScripts():
  if os.environ.get('RUN_SLAVE_UPDATED_SCRIPTS', None):
    os.environ.pop('RUN_SLAVE_UPDATED_SCRIPTS')
    return False
  gclient_path = os.path.join(SCRIPT_PATH, '..', '..', 'depot_tools', 'gclient')
  if sys.platform.startswith('win'):
    gclient_path += '.bat'
  if subprocess.call([gclient_path, 'sync']) != 0:
    msg = '(%s) `gclient sync` failed; proceeding anyway...' % sys.argv[0]
    print >> sys.stderr, msg
  os.environ['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'
  return True


if '__main__' == __name__:
  if UpdateScripts():
    os.execv(sys.executable, [sys.executable] + sys.argv)
  main()
