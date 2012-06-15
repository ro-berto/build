#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Setup a given bot to become a swarm bot by installing the
required files and setting up any required scripts. The bot's OS must be
specified. We assume the bot already has python installed and a ssh server
enabled."""

import optparse
import os
import subprocess
import sys

SWARM_DIRECTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'swarm_bootstrap')


def CopySwarmDirectory(user, host):
  return ['sftp', '-obatchmode=no',
          '-b', os.path.join(SWARM_DIRECTORY_PATH, 'swarm_sftp'),
          '%s@%s' % (user, host)]


def BuildSSHCommand(user, host, platform):
  ssh = ['ssh', '-o ConnectTimeout=5']
  identity = [user + '@' + host]

  bot_setup_commands = []

  if platform == 'win':
    bot_setup_commands.extend([
        'cd c:\\swarm\\'
        '&&',
        'call swarm_bot_setup.bat'])
  else:
    bot_setup_commands.extend([
        'cd $HOME/swarm',
        '&&',
        './swarm_bot_setup.sh'])

  # On windows the command must be executed by cmd.exe
  if platform == 'win':
    bot_setup_commands = ['cmd.exe /c',
                          '"' + ' '.join(bot_setup_commands) + '"']

  return ssh + identity + bot_setup_commands


def BuildSetupCommands(user, host, platform):
  assert platform in ('linux', 'mac', 'win')

  return [
      CopySwarmDirectory(user, host),
      BuildSSHCommand(user, host, platform)
      ]


def main():
  parser = optparse.OptionParser(usage='%prog [options]',
                                 description=sys.modules[__name__].__doc__)
  parser.add_option('-b', '--bot', help='The bot to setup as a swarm bot')
  parser.add_option('-u', '--user', default='chrome-bot',
                    help='The user to use when setting up the machine. '
                    'Defaults to %default')
  parser.add_option('-p', '--print_only', action='store_true',
                    help='Print what command would be executed to setup the '
                    'swarm bot.')
  parser.add_option('-w', '--win', action='store_true')
  parser.add_option('-l', '--linux', action='store_true')
  parser.add_option('-m', '--mac', action='store_true')


  options, args = parser.parse_args()

  if len(args) > 0:
    parser.error('Unknown arguments, ' + str(args))
  if not options.bot:
    parser.error('Must specify a bot.')
  if len([x for x in [options.win, options.linux, options.mac] if x]) != 1:
    parser.error('Must specify the bot\'s OS.')

  if options.win:
    platform = 'win'
  elif options.linux:
    platform = 'linux'
  elif options.mac:
    platform = 'mac'

  commands = BuildSetupCommands(options.user, options.bot, platform)

  if options.print_only:
    print commands
  else:
    for command in commands:
      subprocess.check_call(command)


if __name__ == '__main__':
  sys.exit(main())
