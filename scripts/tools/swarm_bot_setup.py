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

SWARM_COPY_SFTP_PATH = os.path.join(SWARM_DIRECTORY_PATH, 'copy_swarm_sftp')

SWARM_CLEAN_SFTP_PATH = os.path.join(SWARM_DIRECTORY_PATH, 'clean_swarm_sftp')


def BuildSFTPCommand(user, host, command_file):
  return ['sftp', '-obatchmode=no', '-b', command_file,
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


def BuildCleanCommands(user, host):
  return [
      BuildSFTPCommand(user, host, SWARM_CLEAN_SFTP_PATH)
      ]


def BuildSetupCommands(user, host, platform):
  assert platform in ('linux', 'mac', 'win')

  return [
      BuildSFTPCommand(user, host, SWARM_COPY_SFTP_PATH),
      BuildSSHCommand(user, host, platform)
      ]


def main():
  parser = optparse.OptionParser(usage='%prog [options]',
                                 description=sys.modules[__name__].__doc__)
  parser.add_option('-b', '--bot', action='append', default=[],
                    help='The bot to setup as a swarm bot')
  parser.add_option('-r', '--raw',
                    help='The name of a file containing line separated slaves '
                    'to setup. The slaves must all be the same os.')
  parser.add_option('-c', '--clean', action='store_true',
                    help='Removes any old swarm files before setting '
                    'up the bot.')
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
  if not options.bot and not options.raw:
    parser.error('Must specify a bot or bot file.')
  if len([x for x in [options.win, options.linux, options.mac] if x]) != 1:
    parser.error('Must specify the bot\'s OS.')

  if options.win:
    platform = 'win'
  elif options.linux:
    platform = 'linux'
  elif options.mac:
    platform = 'mac'

  bots = options.bot
  if options.raw:
    # Remove extra spaces and empty lines.
    bots.extend(filter(None, (s.strip() for s in open(options.raw, 'r'))))

  for bot in bots:
    commands = []

    if options.clean:
      commands.extend(BuildCleanCommands(options.user, bot))

    commands.extend(BuildSetupCommands(options.user, bot, platform))

    if options.print_only:
      print commands
    else:
      for command in commands:
        subprocess.check_call(command)


if __name__ == '__main__':
  sys.exit(main())
