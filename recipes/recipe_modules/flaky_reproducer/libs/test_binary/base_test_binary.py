# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
from . import utils


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
    # with_* info
    self.tests = kwargs.get('tests', None)
    self.repeat = kwargs.get('repeat', None)

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
    return dict(
        class_name=self.__class__.__name__,
        command=self.command,
        cwd=self.cwd,
        env_vars=self.env_vars,
        dimensions=self.dimensions,
        cas_input_root=self.cas_input_root,
        tests=self.tests,
        repeat=self.repeat,
    )

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
    ret.command = utils.strip_command_wrappers(ret.command, command_wrappers)
    ret.env_vars = utils.strip_env_vars(ret.env_vars, ('LLVM_PROFILE_FILE',))
    return ret

  def with_options_from_other(self, other):
    """Sets the with_* options from another TestBinary.

    Args:
      other (TestBinary): The other TestBinary that contains with_* options that
        self copy from.

    Returns:
      A copy of TestBinary with given options.
    """
    ret = copy.deepcopy(self)
    ret.tests = other.tests
    ret.repeat = other.repeat
    return ret

  def with_tests(self, tests):
    """Sets the tests to run.

    Args:
      tests (list[str]): List of test names.

    Returns:
      A copy of TestBinary with given tests.
    """
    ret = copy.deepcopy(self)
    ret.tests = tests[:]
    return ret

  def with_repeat(self, repeat):
    """Sets the tests run repeat times.

    Args:
      repeat (int): Repeat times for each test.

    Returns:
      A copy of TestBinary with given tests.
    """
    ret = copy.deepcopy(self)
    ret.repeat = repeat
    return ret

  def run(self):
    """Runs the tests.

    Returns:
      TestResultSummary
    """
    raise NotImplementedError('Method should be implemented in sub-classes.')

  def readable_command(self):
    """Return a human readable command line instruction.

    Returns:
      String of command line for the TestBinary.
    """
    raise NotImplementedError('Method should be implemented in sub-classes.')

  def as_command(self, output=None):
    """Return a executable command line.

    Args:
      output (str): output summary filename.

    Returns:
      Command line args array for the TestBinary.
    """
    raise NotImplementedError('Method should be implemented in sub-classes.')


class TestBinaryWithBatchMixin:
  """Mixin class for TestBinary that support tests batching."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.single_batch = kwargs.get('single_batch', None)

  def to_jsonish(self):
    ret = super().to_jsonish()
    ret['single_batch'] = self.single_batch
    return ret

  def with_options_from_other(self, other):
    ret = super().with_options_from_other(other)
    ret.single_batch = other.single_batch
    return ret

  def with_single_batch(self):
    """Sets the tests run in same batch.

    Returns:
      A copy of TestBinary with given tests.
    """
    ret = copy.deepcopy(self)
    ret.single_batch = True
    return ret


class TestBinaryWithParallelMixin:
  """Mixin class for TestBinary that runs tests in parallel."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.parallel_jobs = kwargs.get('parallel_jobs', None)

  def to_jsonish(self):
    ret = super().to_jsonish()
    ret['parallel_jobs'] = self.parallel_jobs
    return ret

  def with_options_from_other(self, other):
    ret = super().with_options_from_other(other)
    ret.parallel_jobs = other.parallel_jobs
    return ret

  def with_parallel_jobs(self, jobs):
    """Sets the tests run in given parallel jobs.

    Args:
      jobs (int): Number of parallel jobs.

    Returns:
      A copy of TestBinary with given tests.
    """
    ret = copy.deepcopy(self)
    ret.parallel_jobs = jobs
    return ret
