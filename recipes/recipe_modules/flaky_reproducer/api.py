# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

from .libs import (create_test_binary_from_task_request,
                   create_result_summary_from_output_json)
from .strategies import strategies, ReproducingStep


def nest_step(func):
  """Wrap the class method into a nested step."""

  def wrapper(self, *args, **kwargs):
    with self.m.step.nest(func.__name__.strip('_')):
      return func(self, *args, **kwargs)

  wrapper.__name__ = func.__name__
  return wrapper


class FlakyReproducer(recipe_api.RecipeApi):
  """Module for Chrome Flaky Reproducer Controller.

  The FlakyReproducer.run is the entrypoint that runs as a recipe controls the
  execution of the strategies and verifications.
  """

  RUNNER_PACKAGE_PATH = 'flaky_reproducer_runner'
  TEST_BINARY_JSON_FILENAME = 'test_binary.json'
  RESULT_SUMMARY_FILENAME = 'result_summary.json'

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
    test_binary = create_test_binary_from_task_request(task_request)
    return test_binary.strip_for_bots()

  @nest_step
  def repack_test_binary(self, test_binary, result_summary):
    """Repack original test binary CAS with strategy runner."""
    tmp_dir = self.m.path.mkdtemp()
    self.m.cas.download('download test binary', test_binary.cas_input_root,
                        tmp_dir)
    runner_dir = tmp_dir.join(self.RUNNER_PACKAGE_PATH)
    self.m.file.copytree(
        'copy flaky_reproducer source',
        self.repo_resource('recipes', 'recipe_modules', 'flaky_reproducer'),
        runner_dir)
    self.m.file.write_text('dump ResultSummary',
                           runner_dir.join(self.RESULT_SUMMARY_FILENAME),
                           result_summary.dump_raw_data())
    self.m.file.write_json('dump TestBinary',
                           runner_dir.join(self.TEST_BINARY_JSON_FILENAME),
                           test_binary.to_jsonish())

    return self.m.cas.archive('new test binary', tmp_dir)

  @nest_step
  def launch_strategy_in_swarming(self, strategy, repacked_cas_input_root):
    """Launches a swarming task that runs the strategy logic."""
    command = [
        'vpython3',
        'strategy_runner.py',
        strategy.name,
        '--test-binary={0}'.format(self.TEST_BINARY_JSON_FILENAME),
        '--result-summary={0}'.format(self.RESULT_SUMMARY_FILENAME),
        strategy.test_name,
    ]

    # yapf: disable
    request = (self.m.swarming.task_request().
      with_name("flaky reproducer strategy {0} for {1}".format(
                strategy.name, strategy.test_name)).
      with_priority(self.c.priority)
    )
    request_slice = (request[0].
      with_command(command).
      with_relative_cwd(self.RUNNER_PACKAGE_PATH).
      with_cas_input_root(repacked_cas_input_root).
      with_env_vars(**strategy.test_binary.env_vars).
      with_dimensions(**strategy.test_binary.dimensions).
      with_execution_timeout_secs(self.c.strategy_timeout).
      with_expiration_secs(self.c.expiration)
    )
    request = request.with_slice(0, request_slice)
    # yapf: enable

    return self.m.swarming.trigger(
        "swarming strategy {0}".format(strategy.name), [request])[0]

  def collect_swarming_result(self, output):
    """Collect strategy result from swarming task output."""
    # TODO(kuanhuang): implementation.
    return ReproducingStep(None)

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
    repacked_cas = self.repack_test_binary(test_binary, result_summary)

    swarming_tasks = []
    for strategy in self.choose_strategies(test_binary, result_summary,
                                           test_name):
      swarming_tasks.append(
          self.launch_strategy_in_swarming(strategy, repacked_cas))
    strategy_results = self.m.swarming.collect('collect strategy results',
                                               swarming_tasks)

    reproducing_steps = []
    for task_result in strategy_results:
      task_result.analyze()
      reproducing_steps.append(self.collect_swarming_result(task_result.output))
    reproducing_step = self.choose_best_reproducing_step(reproducing_steps)

    self.m.step.empty('result', step_text=reproducing_step.readable_info())
