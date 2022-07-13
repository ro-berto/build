# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import re
from recipe_engine import recipe_api
from PB.go.chromium.org.luci.resultdb.proto.v1 import predicate as predicate_pb2

from .libs import (create_test_binary_from_task_request,
                   create_result_summary_from_output_json, strategies,
                   ReproducingStep)


def nest_step(func):
  """Wrap the class method into a nested step."""

  def wrapper(self, *args, **kwargs):
    with self.m.step.nest(func.__name__.strip('_')):
      return func(self, *args, **kwargs)

  wrapper.__name__ = func.__name__
  return wrapper


BuilderVerifyResult = collections.namedtuple(
    'BuilderVerifyResult',
    ['reproduced_cnt', 'total_retries', 'duration', 'error'])
BuilderVerifyResult.__new__.__defaults__ = (0, 0, 0, None)


class FlakyReproducer(recipe_api.RecipeApi):
  """Module for Chrome Flaky Reproducer Controller.

  The FlakyReproducer.run is the entrypoint that runs as a recipe controls the
  execution of the strategies and verifications.
  """

  RUNNER_PACKAGE_PATH = 'flaky_reproducer_runner'
  TEST_BINARY_JSON_FILENAME = 'test_binary.json'
  RESULT_SUMMARY_FILENAME = 'result_summary.json'
  REPRODUCING_STEP_FILENAME = 'reproducing_step.json'
  VERIFY_RESULT_SUMMARY_FILENAME = 'result_summary_$N$.json'

  # TODO(kuanhuang): Use sheriffed and CQ builders.
  ALLOWED_VERIFY_BUILDERS = set([
      'Fuchsia x64',
      'Linux Tests',
      'Mac11 Tests',
      'Win10 Tests x64',
      'android-marshmallow-x86-rel',
      'android-x86-rel',
      'ios-simulator',
      'lacros-amd64-generic-rel',
      'linux-rel',
      'mac-rel',
      'win10_chromium_x64_rel_ng',
  ])

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
      raise self.m.step.StepFailure(
          'Cannot find TaskResult for task {0}.'.format(task_id))
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
        '--output=${{ISOLATED_OUTDIR}}/{0}'.format(
            self.REPRODUCING_STEP_FILENAME),
        strategy.test_name,
    ]

    request = (
        self.m.swarming.task_request()  # go/pyformat-break
        .with_name("flaky reproducer strategy {0} for {1}".format(
            strategy.name, strategy.test_name))  #
        .with_priority(self.c.priority)  #
    )
    request_slice = (
        request[0]  # go/pyformat-break
        .with_command(command)  #
        .with_relative_cwd(self.RUNNER_PACKAGE_PATH)  #
        .with_cas_input_root(repacked_cas_input_root)  #
        .with_env_vars(**strategy.test_binary.env_vars)  #
        .with_dimensions(**strategy.test_binary.dimensions)  #
        .with_execution_timeout_secs(self.c.strategy_timeout)  #
        .with_expiration_secs(self.c.expiration)  #
    )
    request = request.with_slice(0, request_slice)

    return self.m.swarming.trigger(
        "swarming strategy {0}".format(strategy.name), [request])[0]

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

  def collect_strategy_result(self, task_result):
    """Collect strategy result from swarming task output."""
    if self.REPRODUCING_STEP_FILENAME not in task_result.outputs:
      return None
    return ReproducingStep.from_jsonish(
        self.m.file.read_json(
            'load ReproducingStep',
            task_result.outputs[self.REPRODUCING_STEP_FILENAME]))

  @nest_step
  def choose_best_reproducing_step(self, reproducing_steps):
    """Chooses the best ReproducingStep produced by the strategies."""
    best_step = None
    for step in reproducing_steps:
      if not best_step or step.better_tan(best_step):
        best_step = step
    return best_step

  def launch_verify_in_swarming(self,
                                builder,
                                test_name,
                                test_binary,
                                retries=3):
    """Launches a swarming task that verify the reproducing step."""
    command = [
        "vpython3",
        "-c",
        ("import subprocess, sys; "
         "[subprocess.Popen("
         " [x.replace('$N$', str(i)) for x in sys.argv[1:]]"
         ").wait() for i in range({0})]").format(retries),
    ] + test_binary.as_command('${{ISOLATED_OUTDIR}}/{0}'.format(
        self.VERIFY_RESULT_SUMMARY_FILENAME))
    request = (
        self.m.swarming.task_request()  # go/pyformat-break
        .with_name("flaky reproducer verify on {0} for {1}".format(
            builder, test_name))  #
        .with_priority(self.c.priority)  #
        .with_tags({'builder': [builder]})  #
    )
    request_slice = (
        request[0]  # go/pyformat-break
        .with_command(command)  #
        .with_relative_cwd(test_binary.cwd)  #
        .with_cas_input_root(test_binary.cas_input_root)  #
        .with_env_vars(**test_binary.env_vars)  #
        .with_dimensions(**test_binary.dimensions)  #
        .with_execution_timeout_secs(self.c.verify_timeout)  #
        .with_expiration_secs(self.c.expiration)  #
    )
    request = request.with_slice(0, request_slice)

    return self.m.swarming.trigger("swarming verify {0}".format(builder),
                                   [request])[0]

  def collect_verify_test_results(self, task_result, failing_sample):
    """Collect builder verify test results from swarming task output."""
    reproduced = 0
    total_retries = 0
    for filename, filepath in task_result.outputs.items():
      if re.match(r'result_summary_\d+.json', filename):
        result_summary = create_result_summary_from_output_json(
            self.m.file.read_json('load verify result', filepath))
        for result in result_summary.get_all(failing_sample.test_name):
          total_retries += 1
          if failing_sample.similar_with(result):
            reproduced += 1
    return BuilderVerifyResult(reproduced, total_retries,
                               task_result.duration_secs)

  @nest_step
  def verify_reproducing_step(self, task_id, failing_sample, reproducing_step):
    verify_builders = self._find_related_builders(task_id,
                                                  failing_sample.test_name)
    if not verify_builders:
      return
    # Launch verify swarming tasks
    swarming_tasks = {}  # { task_id: (builder, task_meta) }
    for builder, builder_task_id in verify_builders.items():
      test_binary = self.get_test_binary(builder_task_id)
      test_binary = test_binary.with_options_from_other(
          reproducing_step.test_binary)
      task = self.launch_verify_in_swarming(builder, failing_sample.test_name,
                                            test_binary)
      swarming_tasks[task.id] = (builder, task)
    # Collect swarming task result
    verify_results = self.m.swarming.collect(
        'collect verify results', [t for _, t in swarming_tasks.values()],
        output_dir=self.m.path.mkdtemp())
    builder_results = {}
    for result in verify_results:
      builder, _ = swarming_tasks[result.id]
      try:
        result.analyze()
        builder_results[builder] = self.collect_verify_test_results(
            result, failing_sample)
      except Exception as err:
        builder_results[builder] = BuilderVerifyResult(error=str(err))
    return builder_results

  @nest_step
  def summarize_results(self, reproducing_step, builder_results):
    presentation = self.m.step.active_result.presentation
    if not reproducing_step:
      presentation.step_text = 'Not reproducible.'
      return

    summary = []
    summary.append(reproducing_step.readable_info())
    # Group builder results in reproduced, not reproduced, error.
    if builder_results:
      builder_summary = []
      builder_summary.append(
          'The failure could also be reproduced on following builders:')
      builder_summary.append('{0:<23s} {1}/{2}'.format('builder', 'reproduced',
                                                       'total_retries'))
      sorted_builder_results = sorted([x for x in builder_results.items()],
                                      key=lambda kv: (not bool(kv[1].error), kv[
                                          1].reproduced_cnt, kv[1].duration),
                                      reverse=True)
      for builder, result in sorted_builder_results:
        if result.error:
          builder_summary.append('\n{0} failed:\n{1}\n'.format(
              builder, result.error))
        elif result.reproduced_cnt:
          builder_summary.append('{0:<30s} {1:>3d}/{2:d}'.format(
              builder, result.reproduced_cnt, result.total_retries))
        else:
          builder_summary.append(
              '{0:<30s} {1:>3d}/{2:d} (not reproduced)'.format(
                  builder, result.reproduced_cnt, result.total_retries))
      summary.append('\n'.join(builder_summary))

    presentation.step_summary_text = '\n\n'.join(summary)
    presentation.logs['reproducing_step.json'] = self.m.json.dumps(
        reproducing_step.to_jsonish(), indent=2)
    presentation.logs['builder_results.json'] = self.m.json.dumps(
        builder_results, indent=2)

  def run(self, task_id, test_name):
    """Runs the Chrome Flaky Reproducer as a recipe.

    This method is expected to run as a standalone recipe that:
      1. takes a test and the swarming task runs it.
      2. Applies to multiple reproducing strategies.
      3. TODO: Verify the best reproducing step on all variants for the test.
      4. Summarize the results of above.
    """
    # Retrieve failing test info.
    result_summary = self.get_test_result_summary(task_id)
    if test_name not in result_summary:
      raise self.m.step.StepFailure(
          'Cannot find test {0} in test result for task {1}.'.format(
              test_name, task_id))
    test_binary = self.get_test_binary(task_id)
    repacked_cas = self.repack_test_binary(test_binary, result_summary)

    # Trigger reproducing strategies in swarming
    swarming_tasks = []
    for strategy in self.choose_strategies(test_binary, result_summary,
                                           test_name):
      swarming_tasks.append(
          self.launch_strategy_in_swarming(strategy, repacked_cas))
    strategy_results = self.m.swarming.collect(
        'collect strategy results',
        swarming_tasks,
        output_dir=self.m.path.mkdtemp())

    # Verify reproducing steps
    reproducing_steps = []
    for task_result in strategy_results:
      task_result.analyze()
      step = self.collect_strategy_result(task_result)
      if step:
        reproducing_steps.append(step)
    reproducing_step = self.choose_best_reproducing_step(reproducing_steps)
    builder_results = self.verify_reproducing_step(
        task_id, result_summary.get_failing_sample(test_name), reproducing_step)

    # output
    return self.summarize_results(reproducing_step, builder_results)

  def _extract_task_id_from_invocation_name(self, inv_name):
    assert '//' in self.m.swarming.current_server
    swarming_server = self.m.swarming.current_server.split('//', 1)[1]
    m = re.match(r"^invocations/task-{0}-(\w+)".format(swarming_server),
                 inv_name)
    if m:
      return m.group(1)

  def _generate_invocation_id_from_task_id(self, task_id):
    assert '//' in self.m.swarming.current_server
    swarming_server = self.m.swarming.current_server.split('//', 1)[1]
    return "task-{0}-{1}".format(swarming_server, task_id)

  def _find_related_builders(self, task_id, test_name):
    """Search for builders that run the given test."""
    # Query TestResult from invocation.
    inv_id = self._generate_invocation_id_from_task_id(task_id)
    inv_map = self.m.resultdb.query([inv_id],
                                    limit=0,
                                    tr_fields=['testId', 'variant', 'tags'])
    invocation = inv_map.get(inv_id, None)
    if not invocation:
      raise self.m.step.StepFailure(
          'Cannot retrieve invocation for task {0}.'.format(task_id))
    test_result = None
    for test_result in invocation.test_results:
      found = False
      for tag in test_result.tags:
        if tag.key == 'test_name' and tag.value == test_name:
          found = True
          break
      if found:
        break
    else:
      raise self.m.step.StepFailure(
          'Cannot find TestResult for test {0}.'.format(test_name))

    # Query builders with the given test.
    variant_predicate = None
    if 'test_suite' in getattr(test_result.variant, 'def'):
      variant_predicate = predicate_pb2.VariantPredicate(
          contains={
              'def': {
                  'test_suite':
                      getattr(test_result.variant, 'def').get('test_suite')
              }
          })
    escaped_test_id = re.escape(test_result.test_id)
    result_history = None
    next_page_token = None
    builders = {}
    while result_history is None or next_page_token:
      result_history = self.m.resultdb.get_test_result_history(
          realm=invocation.proto.realm,
          test_id_regexp=escaped_test_id,
          variant_predicate=variant_predicate,
          page_size=100,
          page_token=next_page_token)
      next_page_token = result_history.next_page_token
      for each in result_history.entries:
        builder = getattr(each.result.variant, 'def').get('builder', None)
        if (not builder  # go/pyformat-break
            or builder in builders or
            builder not in self.ALLOWED_VERIFY_BUILDERS):
          continue
        task_id = self._extract_task_id_from_invocation_name(each.result.name)
        if not task_id:
          continue
        builders[builder] = task_id

    return builders
