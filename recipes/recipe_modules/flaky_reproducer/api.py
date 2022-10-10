# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import re

from google.protobuf import timestamp_pb2
from recipe_engine import recipe_api

from PB.go.chromium.org.luci.analysis.proto.v1 import common as common_v1
from PB.go.chromium.org.luci.analysis.proto.v1 import predicate as predicate_pb2
from PB.go.chromium.org.luci.analysis.proto.v1 import test_verdict as test_verdict_pb2

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
    ['task_id', 'reproduced_runs', 'total_runs', 'duration', 'error'])
BuilderVerifyResult.__new__.__defaults__ = (None, 0, 0, 0, None)


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

  # Chromite includes a symlink which points to a file it expects to exist in a
  # chroot. We aren't using chromite in a chroot, so this is an invalid symlink.
  # This causes `cas archive` commands which have this directory to fail, so for
  # now we're removing this directory if we see it in any isolate we modify.
  # See https://crbug.com/1298283 for more detail.
  CHROMITE_BAD_SYMLINK_DIR = ('third_party', 'chromite', 'sdk', 'etc',
                              'bash_completion.d')

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
    for output_json in ('run_histories.json', 'output.json'):
      if output_json in cas_output.raw_io.output_dir:
        return create_result_summary_from_output_json(
            self.m.json.loads(cas_output.raw_io.output_dir[output_json]))

    raise self.m.step.StepFailure('Not supported task result.')

  def get_test_binary(self, task_id):
    """Gets TestBinary from the task request properties for a swarming task.

    The actual executable binary are not bound.

    Args:
      task_id (str|TaskRequestMetadata): The task_id for the swarming task.

    Returns:
      TestBinary
    """
    task_request = self.m.swarming.show_request(
        'get_test_binary from {0}'.format(task_id), task_id)
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

    # Delete bad symlink that causing CAS upload failure.
    bad_symlink_dir = tmp_dir.join(*self.CHROMITE_BAD_SYMLINK_DIR)
    self.m.file.rmtree('remove bad symlink directory', bad_symlink_dir)

    self.m.file.write_text('dump ResultSummary',
                           runner_dir.join(self.RESULT_SUMMARY_FILENAME),
                           result_summary.dump_raw_data())
    self.m.file.write_json('dump TestBinary',
                           runner_dir.join(self.TEST_BINARY_JSON_FILENAME),
                           test_binary.to_jsonish())

    return self.m.cas.archive('new test binary', tmp_dir)

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
        .with_io_timeout_secs(self.c.io_timeout)  #
        .with_expiration_secs(self.c.expiration)  #
    )
    request = request.with_slice(0, request_slice)

    return self.m.swarming.trigger(
        "swarming strategy {0}".format(strategy.name), [request])[0]

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
    for strategy_cls in strategies.values():
      strategy = strategy_cls(test_binary, result_summary, test_name)
      if strategy.valid_for_test():
        chosen_strategies.append(strategy)
    return chosen_strategies

  @nest_step
  def collect_strategy_results(self, strategy_results):
    reproducing_steps = []
    for task_result in strategy_results:
      task_result.analyze()
      step = self.collect_strategy_result(task_result)
      if step is not None:
        step.debug_info['task_ui_link'] = self._swarming_task_url(
            task_result.id)
        reproducing_steps.append(step)
    return reproducing_steps

  def collect_strategy_result(self, task_result):
    """Collect strategy result from swarming task output."""
    if self.REPRODUCING_STEP_FILENAME not in task_result.outputs:
      return None
    return ReproducingStep.from_jsonish(
        self.m.file.read_json(
            'load ReproducingStep',
            task_result.outputs[self.REPRODUCING_STEP_FILENAME]))

  def choose_best_reproducing_step(self, reproducing_steps):
    """Chooses the best ReproducingStep produced by the strategies."""
    best_step = None
    for step in reproducing_steps:
      if not best_step or step.better_than(best_step):
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
        .with_io_timeout_secs(self.c.io_timeout)  #
        .with_expiration_secs(self.c.expiration)  #
    )
    request = request.with_slice(0, request_slice)

    return self.m.swarming.trigger("swarming verify {0}".format(builder),
                                   [request])[0]

  def collect_verify_test_results(self, task_result, failing_sample):
    """Collect builder verify test results from swarming task output."""
    reproduced_runs = 0
    total_runs = 0
    for filename, filepath in task_result.outputs.items():
      if re.match(r'result_summary_\d+.json', filename):
        result_summary = create_result_summary_from_output_json(
            self.m.file.read_json('load verify result', filepath))
        total_runs += 1
        for result in result_summary.get_all(failing_sample.test_name):
          if failing_sample.similar_with(result):
            reproduced_runs += 1
            break
    return BuilderVerifyResult(task_result.id, reproduced_runs, total_runs,
                               task_result.duration_secs)

  @nest_step
  def verify_reproducing_step(self, task_id, failing_sample, reproducing_step):
    if not reproducing_step:
      return {}
    builder_results = {}
    swarming_tasks = {}  # { task_id: (builder, task_meta) }
    # Verify failing builder sample
    builder = 'Failing Sample'
    if reproducing_step.test_binary.builder:
      builder = '{0} (failing sample)'.format(
          reproducing_step.test_binary.builder)
    task = self.launch_verify_in_swarming(builder, failing_sample.test_name,
                                          reproducing_step.test_binary)
    swarming_tasks[task.id] = (builder, task)
    # Launch verify swarming tasks
    verify_builders = self._find_related_builders(task_id,
                                                  failing_sample.test_name)
    for builder, builder_task_id in verify_builders.items():
      try:
        test_binary = self.get_test_binary(builder_task_id)
        test_binary = test_binary.with_options_from_other(
            reproducing_step.test_binary)
        task = self.launch_verify_in_swarming(builder, failing_sample.test_name,
                                              test_binary)
        swarming_tasks[task.id] = (builder, task)
      except Exception as err:
        builder_results[builder] = BuilderVerifyResult(error=str(err))
    # Collect swarming task result
    verify_results = self.m.swarming.collect(
        'collect verify results', [t for _, t in swarming_tasks.values()],
        output_dir=self.m.path.mkdtemp())
    for result in verify_results:
      builder, _ = swarming_tasks[result.id]
      try:
        result.analyze()
        builder_results[builder] = self.collect_verify_test_results(
            result, failing_sample)
      except Exception as err:
        builder_results[builder] = BuilderVerifyResult(
            task_id=result.id, error=str(err))
    return builder_results

  @nest_step
  def summarize_results(self, task_id, failing_sample, test_binary,
                        reproducing_step, all_reproducing_steps,
                        builder_results):
    summary = []

    # sample failure info
    message = 'For {0}'.format(failing_sample.test_name)
    if test_binary and test_binary.builder:
      message += ' from {0}'.format(test_binary.builder)
    message += ' {0}'.format(self._swarming_task_url(task_id))
    summary.append(message)
    if failing_sample.primary_error_message:
      summary.append(failing_sample.primary_error_message)

    # reproduce info
    summary.append('\n')
    if reproducing_step:
      summary.append(reproducing_step.readable_info())
    else:
      summary.append("The failure could NOT be reproduced.")

    # strategies info
    if all_reproducing_steps:
      summary.append("\nIt's verified with following strategies:")
      for step in all_reproducing_steps:
        if step.reproduced_cnt:
          message = "{0} strategy reproduced {1} times ({2:.1f}%)".format(
              step.strategy, step.reproduced_cnt, step.reproducing_rate * 100)
        else:
          message = "{0} strategy not reproduced".format(step.strategy)
        if step.debug_info.get('task_ui_link'):
          message += " {0}".format(step.debug_info['task_ui_link'])
        summary.append(message)

    # Group builder results in reproduced, not reproduced, error.
    if builder_results:
      builder_summary = []
      builder_summary.append(
          '\nThe failure could be reproduced on following builders:')
      sorted_builder_results = sorted([x for x in builder_results.items()],
                                      key=lambda kv: (not bool(kv[1].error), kv[
                                          1].reproduced_runs, kv[1].duration),
                                      reverse=True)
      for builder, result in sorted_builder_results:
        if result.error:
          builder_summary.append('{0:<30s} failed:\n{1}\n{2}'.format(
              builder, result.error, (self._swarming_task_url(result.task_id)
                                      if result.task_id else '')))
        elif result.reproduced_runs:
          builder_summary.append('{0:<30s} reproduced {1:d}/{2:d} {3}'.format(
              builder, result.reproduced_runs, result.total_runs,
              self._swarming_task_url(result.task_id)))
        else:
          builder_summary.append('{0:<30s} not reproduced {1}'.format(
              builder, self._swarming_task_url(result.task_id)))
      summary.append('\n'.join(builder_summary))

    presentation = self.m.step.active_result.presentation
    presentation.step_summary_text = "```\n" + '\n'.join(summary) + "\n```"
    if reproducing_step:
      presentation.logs['reproducing_step.json'] = self.m.json.dumps(
          reproducing_step.to_jsonish(), indent=2)
    if builder_results:
      presentation.logs['builder_results.json'] = self.m.json.dumps(
          builder_results, indent=2)

  def query_resultdb_for_task_id_and_test_name(self,
                                               build_id=None,
                                               task_id=None,
                                               test_id=None,
                                               test_name=None):
    """Query ResultDB for task_id and test_name."""
    if not (task_id or build_id):
      raise self.m.step.StepFailure('Must specify task_id or build_id.')
    if not (test_name or test_id):
      raise self.m.step.StepFailure('Must specify test_name or test_id.')

    if task_id and test_name:
      return (task_id, test_name)

    if task_id:
      inv_id = self._generate_invocation_id_from_task_id(task_id)
    else:
      inv_id = self.generate_invocation_id_from_build_id(build_id)

    if test_id:
      test_id_regexp = re.escape(test_id)
    else:
      # test_id contains test_name but might have a different format. It's using
      # the longest word in test_name for filtering to reduce the data
      # retrieved.
      longest_word = max(re.split('\W+', test_name), key=len)
      test_id_regexp = r'.*%s.*' % longest_word

    def tag_test_name(tags):
      for tag in tags:
        if tag.key == 'test_name':
          return tag.value

    # Search for first unexpected result or return the last match.
    last_test_result = None
    res = None
    while True:
      res = self.m.resultdb.query_test_results(
          invocations=['invocations/' + inv_id],
          test_id_regexp=test_id_regexp,
          field_mask_paths=['name', 'test_id', 'tags', 'expected'],
          page_token=res and res.next_page_token,
      )
      for test_result in res.test_results:
        if test_id and test_result.test_id == test_id:
          last_test_result = test_result
        elif test_name and test_name == tag_test_name(test_result.tags):
          last_test_result = test_result
        if last_test_result and not last_test_result.expected:
          break
      if last_test_result and not last_test_result.expected:
        break
      if not res.next_page_token:
        break
    if not last_test_result:
      raise self.m.step.StepFailure('Cannot find TestResult.')

    return (
        self._extract_task_id_from_invocation_name(last_test_result.name),
        test_name or tag_test_name(last_test_result.tags),
    )

  def run(self, task_id=None, build_id=None, test_name=None, test_id=None):
    task_id, test_name = self.query_resultdb_for_task_id_and_test_name(
        task_id=task_id,
        build_id=build_id,
        test_name=test_name,
        test_id=test_id)
    return self._run(task_id, test_name)

  def _run(self, task_id, test_name):
    """Runs the Chrome Flaky Reproducer as a recipe.

    This method is expected to run as a standalone recipe that:
      1. Takes a test and the swarming task runs it.
      2. Applies to multiple reproducing strategies.
      3. Verifies the best reproducing step on all variants for the test.
      4. Summarize the results of above.
    """
    # Retrieve failing test info.
    try:
      result_summary = self.get_test_result_summary(task_id)
      if test_name not in result_summary:
        raise self.m.step.StepFailure(
            'Cannot find test {0} in test result for task {1}.'.format(
                test_name, task_id))
      failing_sample = result_summary.get_failing_sample(test_name)
      test_binary = self.get_test_binary(task_id)
    except NotImplementedError as err:
      # Raise as StepWarning instead of failure.
      raise self.m.step.StepWarning(repr(err))
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
    reproducing_steps = self.collect_strategy_results(strategy_results)
    reproducing_step = self.choose_best_reproducing_step(reproducing_steps)
    builder_results = self.verify_reproducing_step(task_id, failing_sample,
                                                   reproducing_step)

    # output
    return self.summarize_results(
        task_id=task_id,
        failing_sample=failing_sample,
        test_binary=test_binary,
        reproducing_step=reproducing_step,
        all_reproducing_steps=reproducing_steps,
        builder_results=builder_results)

  def _extract_task_id_from_invocation_name(self, inv_name):
    assert '//' in self.m.swarming.current_server
    swarming_server = self.m.swarming.current_server.split('//', 1)[1]
    m = re.match(r"^invocations/task-{0}-(\w+)".format(swarming_server),
                 inv_name)
    if m:
      return m.group(1)

  def generate_invocation_id_from_build_id(self, build_id):
    return 'build-{0}'.format(build_id)

  def _generate_invocation_id_from_task_id(self, task_id):
    assert '//' in self.m.swarming.current_server
    swarming_server = self.m.swarming.current_server.split('//', 1)[1]
    return "task-{0}-{1}".format(swarming_server, task_id)

  def _swarming_task_url(self, task_id):
    return '{0}/task?id={1}'.format(self.m.swarming.current_server, task_id)

  @nest_step
  def _find_related_builders(self, task_id, test_name):
    """Search for builders that run the given test."""
    # Query TestResult from invocation.
    inv_id = self._generate_invocation_id_from_task_id(task_id)
    inv_map = self.m.resultdb.query(
        [inv_id], limit=0, tr_fields=['testId', 'variant', 'tags', 'startTime'])
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

    # Query all variants with the given test.
    project, bucket = invocation.proto.realm.split(':')
    sample_builder = None
    if 'builder' in getattr(test_result.variant, 'def'):
      sample_builder = getattr(test_result.variant, 'def').get('builder')
    variant_predicate = None
    if 'test_suite' in getattr(test_result.variant, 'def'):
      variant_predicate = predicate_pb2.VariantPredicate(
          contains={
              'def': {
                  'test_suite':
                      getattr(test_result.variant, 'def').get('test_suite')
              }
          })
    all_variants = []
    next_page_token = None
    while True:
      variants, next_page_token = self.m.weetbix.query_variants(
          test_id=test_result.test_id,
          project=project,
          sub_realm=bucket,
          variant_predicate=variant_predicate,
          page_token=next_page_token,
      )
      for variant_info in variants:
        builder_name = getattr(variant_info.variant, 'def').get('builder')
        if not builder_name or builder_name == sample_builder:
          continue
        all_variants.append(variant_info)
      if not next_page_token:
        break

    # Query test histories for test variants.
    time_range = common_v1.TimeRange(
        earliest=timestamp_pb2.Timestamp(
            seconds=invocation.proto.create_time.seconds),
        latest=timestamp_pb2.Timestamp(
            seconds=invocation.proto.finalize_time.seconds + 24 * 60 * 60),
    )
    selected_invocations = []
    for variant_info in all_variants:
      verdicts, _ = self.m.weetbix.query_test_history(
          test_id=test_result.test_id,
          # project=project  # This API hardcoded project as chromium.
          sub_realm=bucket,
          variant_predicate=predicate_pb2.VariantPredicate(
              hash_equals=variant_info.variant_hash),
          partition_time_range=time_range,
          page_size=10,
      )
      if not verdicts:
        continue

      # Query build-bucket input for verdicts
      assert all(re.match('^build-\d+$', v.invocation_id) for v in verdicts)
      builds = self.m.buildbucket.get_multi(
          [int(v.invocation_id[len('build-'):]) for v in verdicts])

      selected_verdict = None
      for v in verdicts:
        build = builds.get(int(v.invocation_id[len('build-'):]))
        # Select CQ or sheriff builders.
        if not build or not (
            '$recipe_engine/cq' in build.input.properties.fields or
            'sheriff_rotations' in build.input.properties.fields):
          continue
        # Select first EXPECTED or FLAKY sample over UNEXPECTED or EXONERATED
        # samples.
        if v.status in (test_verdict_pb2.TestVerdictStatus.FLAKY,
                        test_verdict_pb2.TestVerdictStatus.EXPECTED):
          selected_verdict = v
          break
        elif (v.status in (test_verdict_pb2.TestVerdictStatus.UNEXPECTED,
                           test_verdict_pb2.TestVerdictStatus.EXONERATED) and
              not selected_verdict):
          selected_verdict = v
      if selected_verdict:
        selected_invocations.append(selected_verdict.invocation_id)

    # Query task_id for selected verdicts.
    builders = {}
    if not selected_invocations:
      return builders
    res = None
    while True:
      res = self.m.resultdb.query_test_results(
          invocations=['invocations/%s' % inv for inv in selected_invocations],
          test_id_regexp=re.escape(test_result.test_id),
          field_mask_paths=['name', 'variant'],
          page_token=res and res.next_page_token,
      )
      for each in res.test_results:
        builder = getattr(each.variant, 'def').get('builder', None)
        if not builder or builder in builders:
          continue
        task_id = self._extract_task_id_from_invocation_name(each.name)
        if not task_id:
          continue
        builders[builder] = task_id
      if not res.next_page_token:
        break

    presentation = self.m.step.active_result.presentation
    presentation.logs['builders.json'] = self.m.json.dumps(builders, indent=2)
    return builders
