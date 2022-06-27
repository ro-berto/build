# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import subprocess
import sys


def strip_command_wrappers(command, strip_wrappers):
  """Strip command wrapper (e.g. ResultDB integration - rdb) from command line.

  Expecting the following wrappers use -- to signify the start of actual
  commands.

  Args:
    strip_wrappers (list[str]): Name of wrapper commands.

  Returns:
    A copy of command without command wrappers.
  """
  cmd = command[:]
  stripped = True
  while cmd and stripped:
    stripped = False
    cmd_0 = cmd[0].lower()
    if cmd_0.endswith('.exe'):
      cmd_0 = cmd_0[:-4]
    if cmd_0 in strip_wrappers:
      try:
        dash_index = cmd.index('--')
      except ValueError:
        raise ValueError('Unsupported command wrapper: {0} in {1}'.format(
            cmd_0, command))
      cmd = cmd[dash_index + 1:]
      stripped = True
  if not cmd:
    raise ValueError('Empty command after strip: {0}'.format(command))
  # Should strip all wrappers
  is_local = len(cmd) >= 1 and cmd[0].startswith('.')
  is_test_env_py = len(cmd) >= 2 and cmd[1].endswith('testing/test_env.py')
  if not (is_local or is_test_env_py):
    raise ValueError('Command line contains unknown wrapper: {0} in {1}'.format(
        cmd[0], command))
  return cmd


def strip_command_switches(command, strip_switches):
  """Strip specified switches and its value.

  Args:
    strip_switches (map[str, int]): Map of switch name and number of values it's
      expecting.

  Returns:
    A copy of command without strip_switches and their values.
  """
  cmd = []
  # strip switch with value like: --switch value
  strip_next_arg = 0
  for arg in command:
    if arg.startswith('--'):
      if '=' in arg:
        switch, value = arg.split('=', 1)
      else:
        switch, value = arg, None
      switch = switch.strip('- ').lower()

      if switch in strip_switches:
        strip_next_arg = 0 if value else strip_switches[switch]
      else:
        strip_next_arg = 0  # Reset when accepting a new switch.
        cmd.append(arg)
    elif strip_next_arg:
      strip_next_arg -= 1
    else:
      cmd.append(arg)
  return cmd


def strip_env_vars(env_vars, strip_keys):
  """Strip specified keys from environnement variables

  Args:
    strip_keys (list[str]): Name of the environnement variables.

  Returns:
    A copy of env_vars without strip_keys.
  """
  return {
      key: value for key, value in env_vars.items() if key not in strip_keys
  }


def run_cmd(argv, cwd=None, env=None):
  """Run command locally.

  Args:
    argv (list[str]): Sequence of program arguments.
    cwd (str): Change working directory.
    env (dict): Dict of environment variables.

  Raise:
    ChildProcessError if command return code is not 0.
  """
  # FIXME(kuanhuang): This method could be improved to handle the swarming
  # signals. Inheriting and merging the current process' environment.
  print(
      'Running {0!r} in {1!r} with {2!r}'.format(argv, cwd, env),
      file=sys.stderr)
  process = subprocess.Popen(argv, env=env, cwd=cwd)
  ret_code = process.wait()
  if ret_code != 0:
    raise ChildProcessError(
        "Run command failed with code {0}.".format(ret_code))
