# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

from .libs import (create_test_binary_from_task_request,
                   create_result_summary_from_output_json)
from .strategies import strategies


def nest_step(func):
  """Wrap the class method into a nested step."""

  def wrapper(self, *args, **kwargs):
    with self.m.step.nest(func.__name__):
      return func(self, *args, **kwargs)

  wrapper.__name__ = func.__name__
  return wrapper


class FlakyReproducer(recipe_api.RecipeApi):
  """Module for Chrome Flaky Reproducer Controller.

  The FlakyReproducer.run is the entrypoint that runs as a recipe controls the
  execution of the strategies and verifications.
  """

  def __init__(self, *args, **kwargs):
    super(FlakyReproducer, self).__init__(*args, **kwargs)

  @nest_step
  def get_test_result_summary(self, task_id):
    """Gets TestResultSummary from the output of a swarming task result.

    Args:
      task_id (str|TaskRequestMetadata): The task_id for the swarming task.

    Returns:
      TestResultSummary
    """
    task_results = self.m.swarming.collect('swarming collect', [task_id])
    if not task_results:
      raise self.m.step.StepFailure('Cannot find TaskResult for task %s.' %
                                    task_id)
    task_result = task_results[0]

    cas_output = self.m.cas.download('download swarming outputs',
                                     task_result.cas_outputs.digest,
                                     self.m.raw_io.output_dir())
    if 'output.json' in cas_output.raw_io.output_dir:
      test_result = create_result_summary_from_output_json(
          self.m.json.loads(cas_output.raw_io.output_dir['output.json']))
    else:
      raise self.m.step.StepFailure('Not supported task result.')

    return test_result

  @nest_step
  def get_test_binary(self, task_id):
    """Gets TestBinary from the task request properties for a swarming task.

    The actual executable binary are not bound.

    Args:
      task_id (str|TaskRequestMetadata): The task_id for the swarming task.

    Returns:
      TestBinary
    """
    task_request = self.m.swarming.show_request('show request', task_id)
    return create_test_binary_from_task_request(task_request)

  @nest_step
  def choose_strategies(self, test_binary, result_summary, test_name):
    """Chooses the strategies that be applied to the test.

    Args:
      test_binary (TestBinary)
      result_summary (TestResultSummary)
      test_name (str): the test name used in TestResultSummary.

    Return:
      A list of Strategy objects that can be applied to the test.
    """
    chosen_strategies = []
    # TODO(kuanhuang): actually return strategies that can be applied to the
    # test case.
    for strategy_cls in strategies.values():
      chosen_strategies.append(
          strategy_cls(test_binary, result_summary, test_name))
    return chosen_strategies

  @nest_step
  def choose_best_reproducing_step(self, reproducing_steps):
    """Chooses the best ReproducingStep produced by the strategies."""
    # TODO(kuanhuang): actually choose the best step.
    if not reproducing_steps:
      raise self.m.step.StepFailure('No reproducible step could be found.')
    return reproducing_steps[0]

  @nest_step
  def verify_reproducing_step(self):
    raise NotImplementedError()  # pragma: no cover

  @nest_step
  def summarize_results(self):
    raise NotImplementedError()  # pragma: no cover

  def run(self, task_id, test_name):
    """Runs the Chrome Flaky Reproducer as a recipe.

    This method is expected to run as a standalone recipe that:
      1. takes a test and the swarming task runs it.
      2. Applies to multiple reproducing strategies.
      3. TODO: Verify the best reproducing step on all variants for the test.
      4. Summarize the results of above.
    """
    result_summary = self.get_test_result_summary(task_id)
    test_binary = self.get_test_binary(task_id)

    futures = []
    for strategy in self.choose_strategies(test_binary, result_summary,
                                           test_name):
      futures.append(self.m.futures.spawn(strategy.launch_strategy_in_swarming))

    reproducing_steps = [
        x.result() for x in self.m.futures.wait(futures) if x.result()
    ]

    reproducing_step = self.choose_best_reproducing_step(reproducing_steps)
    self.m.step.empty('result', step_text=reproducing_step.readable_info())
