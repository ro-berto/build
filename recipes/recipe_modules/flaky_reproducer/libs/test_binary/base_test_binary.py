# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy


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

  def run_tests(self, tests, repeat=1):
    """Runs the tests [repeat] times with given [tests].

    Args:
      tests (list[str]): List of test names.
      repeat (int): Repeat times for each test.

    Returns:
      TestResultSummary
    """
    raise NotImplementedError('Method should be implemented in sub-classes.')
