#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A small maintenance tool to do mass execution on the slaves."""

import os
import optparse
import re
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common import chromium_utils
from master import slaves_list


def SubRun(enabled, names, cmd, options):
  if enabled:
    if options.max:
      max_index = options.max
    else:
      max_index = len(names)
    if options.min:
      min_index = options.min
    else:
      min_index = 1
    for index in range(min_index, max_index + 1):
      host = names[index - 1]
      command = [item % {'index': index, 'host': host} for item in cmd]
      print "> %s" % " ".join(command)
      if not options.print_only:
        retcode = subprocess.call(command)
        if retcode:
          print 'Stopped at index %d' % index
          print 'Returned %d' % retcode
          if not options.ignore_failure:
            return retcode
  return 0


def RunSSH(options, args):
  retcode = SubRun(options.win, options.win_names,
                   ['ssh', '-o ConnectTimeout=5', 'chrome-bot@%(host)s',
                    options.win_cmd] + args,
                   options)
  if not retcode:
    retcode = SubRun(options.linux, options.linux_names,
                     ['ssh', '-o ConnectTimeout=5', '-t', 'chrome-bot@%(host)s',
                      options.linux_cmd] + args,
                     options)
  if not retcode:
    retcode = SubRun(options.mac, options.mac_names,
                     ['ssh', '-o ConnectTimeout=5', '-t', 'chrome-bot@%(host)s',
                      options.mac_cmd] + args,
                     options)
  return retcode


def RunSCP(options, args):
  retcode = SubRun(options.win, options.win_names,
                   ['scp', args[0], 'chrome-bot@%(host)s:' + args[1]],
                   options)
  if not retcode:
    retcode = SubRun(options.linux, options.linux_names,
                     ['scp', args[0], 'chrome-bot@%(host)s:' + args[1]],
                     options)
  if not retcode:
    retcode = SubRun(options.mac, options.mac_names,
                     ['scp', args[0], 'chrome-bot@%(host)s:' + args[1]],
                     options)
  return retcode


def Clobber(options, args):
  # TODO(maruel): Find a way to find the builder's directory or use the same way
  # as Revert() (quite hackish) Should use python instead since it's guaranteed
  # to be avail and works cross-platforms.
  path_base = r'C:\b\build\slave\win\build\src\build'
  path_rel = path_base + r'\release'
  path_dbg = path_base + r'\debug'
  options.win_cmd = 'cmd /c rd /q /s %s %s' % (path_dbg, path_rel)
  # options.win_cmd = (
  #    r"cmd /c dir c:\b\build\slave\* /ad /b | findstr /v /i cert | "
  #    r"findstr /v /i info | findstr /v /i .svn > c:\b\build\slave\subdir")
  # options.win_cmd = (
  #    r"cmd /c for /F %a in (c:\b\build\slave\subdir) do "
  #    r"rd /q /s c:\b\build\slave\%a\build\src\chrome")
  # options.win_cmd = (
  #    r"cmd /c for /F %a in (c:\b\build\slave\subdir) do "
  #    r"echo c:\b\build\slave\%a\build\src\chrome")
  # options.win_cmd = (
  #    r"cmd /c for /F %a in (c:\b\build\slave\subdir) do "
  #    r"rd /q /s c:\b\build\slave\%a\build\src\third_party\WebKit\WebKit")
  path_scons = '/b/build/slave/*/build/src/sconsbuild'
  path_make = '/b/build/slave/*/build/src/out'
  options.linux_cmd = 'rm -rf %s %s' % (path_scons, path_make)
  path = '/b/build/slave/*/build/src/xcodebuild'
  options.mac_cmd = 'rm -rf %s' % path
  # We don't want to stop if one slave failed.
  options.ignore_failure = True
  return RunSSH(options, args)


def Revert(options, args):
  # path_base = r'C:\b\build\slave\win\build\src\chrome'
  options.win_cmd = (
      r"cmd /c for /F %a in (c:\\b\\build\\slave\\subdir) do "
      r"cd c:\\b\\build\\slave\%a\\build\\src && gclient revert")
  path = '/b/build/slave/*/build/src'
  options.linux_cmd = 'cd %s && gclient revert' % path
  path = '/b/build/slave/*/build/src'
  options.mac_cmd = 'cd %s && gclient revert' % path
  options.ignore_failure = True
  return RunSSH(options, args)


def Restart(options, args):
  options.win_cmd = 'shutdown -r -f -t 1'
  options.linux_cmd = 'sudo shutdown -r now'
  options.mac_cmd = 'sudo shutdown -r now'
  # We don't want to stop if one slave failed.
  options.ignore_failure = True
  return RunSSH(options, args)


def SyncScripts(options, args):
  options.win_cmd = 'cmd /c cd c:\\b && depot_tools\\gclient sync'
  options.linux_cmd = 'cd /b && ./depot_tools/gclient sync'
  options.mac_cmd = 'cd /b && ./depot_tools/gclient sync'
  return RunSSH(options, args)


def TaskKill(options, args):
  options.win_cmd = 'taskkill /im crash_service.exe'
  options.ignore_failure = True
  options.win = True
  options.linux = False
  options.mac = False
  return RunSSH(options, args)


def InstallMsi(options, args):
  """Example."""
  options.win_cmd = 'msiexec /quiet /i \\\\hostname\\sharename\\appverif.msi'
  options.linux = False
  options.mac = False
  return RunSSH(options, args)


def SCP(options, args):
  if len(args) != 2:
    print 'Need 2 args'
    return 1
  return RunSCP(options, args)


def Main(argv):
  usage = """%prog [options]

Sample usage:
  %prog -x t.c --index 5 -i -W "cmd rd /q /s c:\\b\\build\\slave\\win\\build"
  %prog -x chromium -l -c

Note: t is replaced with 'tryserver', 'c' with chromium' and
      co with 'chromiumos'."""

  # Generate the list of available masters.
  masters_path = chromium_utils.ListMasters()
  masters = [os.path.basename(f) for f in masters_path]
  # Strip off 'master.'
  masters = [re.match(r'(master\.|)(.*)', m).group(2) for m in masters]
  parser = optparse.OptionParser(usage=usage)
  group = optparse.OptionGroup(parser, 'Slaves to process')
  group.add_option('-x', '--master',
      help='Master to use to load the slaves list. Choices are: %s' %
              ', '.join(masters))
  group.add_option('-w', '--win', action='store_true')
  group.add_option('-l', '--linux', action='store_true')
  group.add_option('-m', '--mac', action='store_true')
  group.add_option('-b', '--bits', help='Slave os bitness')
  group.add_option('--version', help='Slave os version')
  group.add_option('--builder',
                   help='Only slaves attached to a specfic builder')
  group.add_option('--min', type='int')
  group.add_option('--max', type='int', help='Inclusive')
  group.add_option('--index', type='int', help='execute on only one slave')
  group.add_option('-s', '--slave', action='append')
  group.add_option('--raw', help='Line separated list of slaves to use. Must '
                                 'still use -l, -m or -w to let the script '
                                 'know what command to run')
  parser.add_option_group(group)
  parser.add_option('-i', '--ignore_failure', action='store_true',
                    help='Continue even if ssh returned an error')
  group = optparse.OptionGroup(parser, 'Premade commands')
  group.add_option('-c', '--clobber', action='store_true')
  group.add_option('-r', '--restart', action='store_true')
  group.add_option('--revert', action='store_true',
                   help='Execute gclient revert')
  group.add_option('--sync_scripts', action='store_true')
  group.add_option('--taskkill', action='store_true')
  group.add_option('--scp', action='store_true',
                   help='with the source and dest files')
  group.add_option('-p', '--print_only', action='store_true',
                   help='Print which slaves would have been processed but do '
                        'nothing. With no command, just print the list of '
                        'slaves for the given platform(s).')
  parser.add_option_group(group)
  group = optparse.OptionGroup(parser, 'Custom commands')
  group.add_option('-W', '--win_cmd', help='Run a custom command instead')
  group.add_option('-L', '--linux_cmd')
  group.add_option('-M', '--mac_cmd')
  parser.add_option_group(group)
  options, args = parser.parse_args(argv)

  # If a command is specified, the corresponding platform is automatically
  # enabled.
  if options.linux_cmd:
    options.linux = True
  if options.mac_cmd:
    options.mac = True
  if options.win_cmd:
    options.win = True

  if options.raw:
    # Remove extra spaces and empty lines.
    options.slave = filter(None, (s.strip() for s in open(options.raw, 'r')))

  if not options.slave:
    if not options.master:
      parser.error('Need to pass either --slave or --master')
      return 0
    if not options.master in masters:
      # Try subsititions
      options.master = re.sub(r'\bt\b', 'tryserver', options.master)
      options.master = re.sub(r'\bc\b', 'chromium', options.master)
      options.master = re.sub(r'\bco\b', 'chromiumos', options.master)
      if not options.master in masters:
        parser.error('Unknown master \'%s\'.\nChoices are: %s' % (
          options.master, ', '.join(masters)))
    master_path = masters_path[masters.index(options.master)]
    slaves = slaves_list.SlavesList(os.path.join(master_path, 'slaves.cfg'))
    def F(os_type):
      out = slaves.GetSlaves(os=os_type, bits=options.bits,
          version=options.version, builder=options.builder)
      # Skips slave without a hostname.
      return [s.get('hostname') for s in out if s.get('hostname')]
    options.win_names = F('win')
    options.linux_names = F('linux')
    options.mac_names = F('mac')
  else:
    slaves = options.slave
    options.win_names = slaves
    options.linux_names = slaves
    options.mac_names = slaves

  if not options.linux and not options.mac and not options.win:
    parser.print_help()
    return 0

  if options.index:
    options.min = options.index
    options.max = options.index

  if options.restart:
    return Restart(options, args)
  elif options.clobber:
    return Clobber(options, args)
  elif options.sync_scripts:
    return SyncScripts(options, args)
  elif options.taskkill:
    return TaskKill(options, args)
  elif options.revert:
    return Revert(options, args)
  elif options.scp:
    return SCP(options, args)
  elif options.print_only and not (options.win_cmd or options.linux_cmd or
                                   options.mac_cmd):
    names_list = []
    if not options.min:
      options.min = 1
    if options.win:
      max_i = len(options.win_names)
      if options.max:
        max_i = options.max
      names_list += options.win_names[options.min - 1:max_i]
    if options.linux:
      max_i = len(options.linux_names)
      if options.max:
        max_i = options.max
      names_list += options.linux_names[options.min - 1:max_i]
    if options.mac:
      max_i = len(options.mac_names)
      if options.max:
        max_i = options.max
      names_list += options.mac_names[options.min - 1:max_i]
    print '\n'.join(names_list)
  else:
    if ((options.win and not options.win_cmd) or
        (options.linux and not options.linux_cmd) or
        (options.mac and not options.mac_cmd)):
      parser.error('Need to specify a command')
    return RunSSH(options, args)


if __name__ == '__main__':
  sys.exit(Main(None))
