# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import copy
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


class BaseTestBinary:
  """
  The base abstract class for executable TestBinary.

  For the functions marked as optional, you could use cls.support_*() class
  method to check if it's supported by the test suite.

  Attributes:
    command (list[str]): The base command line for the binary.  Should contains
      the executable with arguments for the test suite.
    cwd (str): Current working directory for the test binary.
    env_vars (dict): Environment variables applied on swarming task, may
      contain swarming magic values, e.g. ${ISOLATED_OUTDIR}.
    dimensions (dict): dimensions on which to filter swarming bots.
    cas_input_root (str): digest of an uploaded directory tree on the default
      cas server.
  """

  def __init__(self, command, **kwargs):
    # test binary info
    self.command = command[:]
    self.cwd = kwargs.get('cwd', None)

    # test environment info
    self.env_vars = kwargs.get('env_vars', {})
    self.dimensions = kwargs.get('dimensions', {})
    self.cas_input_root = kwargs.get('cas_input_root', None)

  @classmethod
  def from_task_request(cls, task_request):
    """Gets test binary information from a swarming TaskRequest

    This method always use the last TaskSlice in the TaskRequest to exclude any
    optional caches.

    Args:
      task_request (TaskRequest): A recipe_engine/swarming TaskRequest instance.
        https://source.chromium.org/chromium/infra/infra/+/main:recipes-py/recipe_modules/swarming/api.py;l=26;drc=e3cd9ebd631fa88e0d6ecb9920ba0b6ed42a1325

    Returns:
      A new TestBinary instance.
    """
    if len(task_request) < 1:
      raise ValueError("No TaskSlice found in the TaskRequest.")
    request_slice = task_request[-1]

    ret = cls(
        request_slice.command,
        cwd=request_slice.relative_cwd,
        env_vars=request_slice.env_vars,
        dimensions=request_slice.dimensions,
        cas_input_root=request_slice.cas_input_root,
    )
    return ret

  def to_jsonish(self):
    """Return a JSON-serializable dict."""
    ret = dict(
        command=self.command,
        cwd=self.cwd,
        env_vars=self.env_vars,
        dimensions=self.dimensions,
        cas_input_root=self.cas_input_root,
    )
    return ret

  @classmethod
  def from_jsonish(cls, d):
    """Create a new TestBinary from a JSON-serializable dict"""
    return cls(**copy.deepcopy(d))

  def strip_for_bots(self):
    """Strip the command and/or env for bot reproducing.

    This method strips the test wrappers for ResultDB integration and
    environment variables for sharding and coverage that might not related to
    the flaky reproducing.

    Returns:
      A processed copy of current TestBinary.
    """
    ret = copy.deepcopy(self)

    command_wrappers = (
        'rdb',
        'result_adapter',
        'luci-auth',
    )
    ret.command = strip_command_wrappers(ret.command, command_wrappers)
    ret.env_vars = strip_env_vars(ret.env_vars, ('LLVM_PROFILE_FILE',))
    return ret

  def run_cmd(self, argv, cwd=None):
    """Run command locally.

    Args:
      argv (list[str]): Sequence of program arguments.
      env (dict): Dict of environment variables (override self.env when set).
      cwd (str): Change working directory (override self.cwd when set).

    Returns:
      Process return code.
    """
    # FIXME(kuanhuang): This method could be improved to handle the swarming
    # signals. Inheriting and merging the current process' environment.
    cwd = cwd or self.cwd
    print('Running {0!r} in {1!r}'.format(argv, cwd), file=sys.stderr)
    process = subprocess.Popen(argv, cwd=cwd)
    return process.wait()

  def run_tests(self, tests, repeat=1):
    """Runs the tests [repeat] times with given [tests].

    Args:
      tests (list[str]): List of test names.
      repeat (int): Repeat times for each test.

    Returns:
      TestResultSummary
    """
    raise NotImplementedError('Method should be implemented in sub-classes.')
