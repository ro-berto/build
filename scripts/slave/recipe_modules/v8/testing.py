# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
from recipe_engine.types import freeze


TEST_CONFIGS = freeze({
  'benchmarks': {
    'name': 'Benchmarks',
    'tests': ['benchmarks'],
    'test_args': ['--download-data'],
  },
  'deopt': {
    'tool': 'run-deopt-fuzzer',
    'isolated_target': 'run-deopt-fuzzer',
  },
  'gcmole': {
    'tool': 'run-gcmole',
    'isolated_target': 'run-gcmole',
  },
  'ignition': {
    'name': 'Ignition',
    'tests': ['ignition'],
    'test_args': ['--variants=ignition', '--ignition'],
  },
  'mjsunit': {
    'name': 'Mjsunit',
    'tests': ['mjsunit'],
  },
  'mjsunit_sp_frame_access': {
    'name': 'Mjsunit - sp frame access',
    'tests': ['mjsunit'],
    'test_args': [
      '--variants=turbofan', '--extra-flags=--turbo_sp_frame_access'],
  },
  'mozilla': {
    'name': 'Mozilla',
    'tests': ['mozilla'],
  },
  'optimize_for_size': {
    'name': 'OptimizeForSize',
    'tests': ['optimize_for_size'],
    'suite_mapping': ['mjsunit', 'cctest', 'webkit', 'intl'],
    'test_args': ['--no-variants', '--extra-flags=--optimize-for-size'],
  },
  'simdjs': {
    'name': 'SimdJs - all',
    'tests': ['simdjs'],
    'test_args': ['--download-data'],
  },
  'simpleleak': {
    'tool': 'run-valgrind',
    'isolated_target': 'run-valgrind',
  },
  'test262': {
    'name': 'Test262 - no variants',
    'tests': ['test262'],
    'test_args': ['--no-variants', '--download-data'],
  },
  'test262_ignition': {
    'name': 'Test262 - ignition',
    'tests': ['test262'],
    'test_args': ['--variants=ignition', '--ignition'],
  },
  'test262_variants': {
    'name': 'Test262',
    'tests': ['test262'],
    'test_args': ['--download-data'],
  },
  'unittests': {
    'name': 'Unittests',
    'tests': ['unittests'],
  },
  'v8initializers': {
    'tool': 'check-static-initializers',
    'isolated_target': 'check-static-initializers',
  },
  'v8testing': {
    'name': 'Check',
    'tests': ['bot_default'],
    'suite_mapping': [
        'mjsunit', 'cctest', 'webkit', 'message', 'preparser', 'intl'],
  },
  'webkit': {
    'name': 'Webkit',
    'tests': ['webkit'],
  },
})


class BaseTest(object):
  def __init__(self, test_step_config, api, v8):
    self.test_step_config = test_step_config
    self.name = test_step_config.name
    self.api = api
    self.v8 = v8

  def _get_isolated_hash(self, test):
    isolated = test.get('isolated_target')
    if not isolated:
      # Normally we run only one test and the isolate name is the same as the
      # test name.
      assert len(test['tests']) == 1
      isolated = test['tests'][0]

    isolated_hash = self.v8.isolated_tests.get(isolated)

    # TODO(machenbach): Maybe this is too hard. Implement a more forgiving
    # solution.
    assert isolated_hash
    return isolated_hash

  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return False

  def apply_filter(self):
    # Run all tests by default.
    return True

  def pre_run(self, test=None, **kwargs):  # pragma: no cover
    pass

  def run(self, test=None, **kwargs):  # pragma: no cover
    raise NotImplementedError()

  def rerun(self, failure_dict, **kwargs):  # pragma: no cover
    raise NotImplementedError()


class V8Test(BaseTest):
  def apply_filter(self):
    self.applied_test_filter = self.v8._applied_test_filter(
        TEST_CONFIGS[self.name])
    if self.v8.test_filter and not self.applied_test_filter:
      self.api.step(TEST_CONFIGS[self.name]['name'] + ' - skipped', cmd=None)
      return False
    return True

  def run(self, test=None, **kwargs):
    test = test or TEST_CONFIGS[self.name]

    def step_test_data():
      return self.v8.test_api.output_json(
          self.v8._test_data.get('test_failures', False),
          self.v8._test_data.get('wrong_results', False),
          self.v8._test_data.get('flakes', False))

    full_args, env = self.v8._setup_test_runner(test, self.applied_test_filter)
    if self.v8.c.testing.may_shard and self.v8.c.testing.SHARD_COUNT > 1:
      full_args += [
        '--shard-count=%d' % self.v8.c.testing.SHARD_COUNT,
        '--shard-run=%d' % self.v8.c.testing.SHARD_RUN,
      ]
    full_args += [
      '--json-test-results',
      self.api.json.output(add_json_log=False),
    ]
    self.api.python(
      test['name'],
      self.api.path['checkout'].join('tools', 'run-tests.py'),
      full_args,
      cwd=self.api.path['checkout'],
      env=env,
      step_test_data=step_test_data,
      **kwargs
    )
    return self.post_run(test)

  def post_run(self, test):
    # The active step was either a local test run or the swarming collect step.
    step_result = self.api.step.active_result
    json_output = step_result.json.output

    # Log used test filters.
    if self.applied_test_filter:
      step_result.presentation.logs['test filter'] = self.applied_test_filter

    # The output is expected to be a list of architecture dicts that
    # each contain a results list. On buildbot, there is only one
    # architecture.
    assert len(json_output) == 1
    self.v8._update_durations(json_output[0], step_result.presentation)
    failure_factory=Failure.factory_func(self.test_step_config)
    failure_log, failures, flake_log, flakes = (
        self.v8._get_failure_logs(json_output[0], failure_factory))
    self.v8._update_failure_presentation(
        failure_log, failures, step_result.presentation)

    if failure_log and failures:
      # Mark the test step as failure only if there were real failures (i.e.
      # non-flakes) present.
      step_result.presentation.status = self.api.step.FAILURE

    if flake_log and flakes:
      # Emit a separate step to show flakes from the previous step
      # to not close the tree.
      step_result = self.api.step(test['name'] + ' (flakes)', cmd=None)
      step_result.presentation.status = self.api.step.WARNING
      self.v8._update_failure_presentation(
            flake_log, flakes, step_result.presentation)

    return TestResults(failures, flakes, [])

  def _setup_rerun_config(self, failure_dict):
    """Return: A test config that reproduces a specific failure."""
    # Make sure bisection is only activated on builders that give enough
    # information to retry.
    assert failure_dict.get('variant')
    assert failure_dict.get('random_seed')

    orig_config = TEST_CONFIGS[self.name]

    # If not specified, the isolated target is the same as the first test of
    # the original list. We need to set it explicitly now, as the tests
    # parameter changes on rerun, but the isolated target is still the same. 
    isolated_target = orig_config.get(
        'isolated_target', orig_config['tests'][0])

    # Filter variant manipulation from test arguments.
    # We'll specify exactly the variant which failed.
    orig_args = [x for x in orig_config.get('test_args', [])
                 if x != '--no-variants']

    new_args = [
      '--variants', failure_dict['variant'],
      '--random-seed', failure_dict['random_seed'],
    ]

    rerun_config = {
      'name': 'Retry',
      'isolated_target': isolated_target,
      'tests': [failure_dict['name']],
      'test_args' : orig_args + new_args,
    }

    # Switch off test filters on rerun.
    self.applied_test_filter = None
    return rerun_config

  def rerun(self, failure_dict, **kwargs):
    return self.run(test=self._setup_rerun_config(failure_dict), **kwargs)


class V8SwarmingTest(V8Test):
  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return True

  def _v8_collect_step(self, task, **kwargs):
    """Produces a step that collects and processes a result of a v8 task."""
    # Placeholder for the merged json output.
    json_output = self.api.json.output(add_json_log=False)

    # Shim script's own arguments.
    args = [
      '--swarming-client-dir', self.api.swarming_client.path,
      '--temp-root-dir', self.api.path['tmp_base'],
      '--merged-test-output', json_output,
    ]

    # Arguments for actual 'collect' command.
    args.append('--')
    args.extend(self.api.swarming.get_collect_cmd_args(task))

    # We need to wait longer for tasks on arm as there the hard
    # timeout and expiration are also higher.
    if (self.task.dimensions.get('cpu') and
        self.task.dimensions['cpu'].startswith('arm')):
      args.extend(['--timeout', '%d' % (7 * 60 * 60)])

    return self.api.python(
        name=self.test['name'],
        script=self.v8.resource('collect_v8_task.py'),
        args=args,
        allow_subannotations=True,
        step_test_data=kwargs.pop('step_test_data', None),
        **kwargs)

  def pre_run(self, test=None, **kwargs):
    # Set up arguments for test runner.
    self.test = test or TEST_CONFIGS[self.name]
    extra_args, _ = self.v8._setup_test_runner(
        self.test, self.applied_test_filter)

    # Let json results be stored in swarming's output folder. The collect
    # step will copy the folder's contents back to the client.
    extra_args += [
      '--swarming',
      '--json-test-results',
      '${ISOLATED_OUTDIR}/output.json',
    ]

    # Initialize number of shards, either per test or per builder.
    shards = 1
    if self.v8.c.testing.may_shard:
      shards = self.test_step_config.shards
      if self.v8.c.testing.SHARD_COUNT > 1:  # pragma: no cover
        shards = self.v8.c.testing.SHARD_COUNT

    # Initialize swarming task with custom data-collection step for v8
    # test-runner output.
    self.task = self.api.swarming.task(
        title=self.test['name'],
        isolated_hash=self._get_isolated_hash(self.test),
        shards=shards,
        extra_args=extra_args,
    )
    self.task.collect_step = lambda task, **kw: (
        self._v8_collect_step(task, **kw))

    # Add custom dimensions.
    if self.v8.bot_config.get('swarming_dimensions'):
      self.task.dimensions.update(self.v8.bot_config['swarming_dimensions'])

    # Set default value.
    if 'os' not in self.task.dimensions:  # pragma: no cover
      # TODO(machenbach): Remove pragma as soon as there's a builder without
      # default value.
      self.task.dimensions['os'] = self.api.swarming.prefered_os_dimension(
          self.api.platform.name)

    # Increase default timeout and expiration on arm.
    if (self.task.dimensions.get('cpu') and
        self.task.dimensions['cpu'].startswith('arm')):
      self.task.hard_timeout = 60 * 60
      self.task.expiration = 6 * 60 * 60

    self.api.swarming.trigger_task(self.task)

  def run(self, **kwargs):
    # TODO(machenbach): Soften this when softening 'assert isolated_hash'
    # above.
    assert self.task
    try:
      # Collect swarming results. Use the same test simulation data for the
      # swarming collect step like for local testing.
      result = self.api.swarming.collect_task(
        self.task,
        step_test_data=lambda: self.v8.test_api.output_json(),
      )
    finally:
      # Note: Exceptions from post_run might hide a pending exception from the
      # try block.
      return self.post_run(self.test)

  def rerun(self, failure_dict, **kwargs):
    self.pre_run(test=self._setup_rerun_config(failure_dict), **kwargs)
    return self.run(**kwargs)


class V8Presubmit(BaseTest):
  def run(self, **kwargs):
    self.api.python(
      'Presubmit',
      self.api.path['checkout'].join('tools', 'presubmit.py'),
      cwd=self.api.path['checkout'],
    )
    return TestResults.empty()


class V8GenericSwarmingTest(BaseTest):
  def __init__(self, test_step_config, api, v8,
               title='Generic test', extra_args=None):
    super(V8GenericSwarmingTest, self).__init__(test_step_config, api, v8)
    self._extra_args = extra_args or []
    self._title = title

  @property
  def title(self):
    return self._title  # pragma: no cover

  @property
  def extra_args(self):
    return self._extra_args  # pragma: no cover

  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return True

  def pre_run(self, test=None, **kwargs):
    self.test = test or TEST_CONFIGS[self.name]
    self.task = self.api.swarming.task(
        title=self.title,
        isolated_hash=self._get_isolated_hash(self.test),
        extra_args=self.extra_args,
    )

    # Set default value.
    if 'os' not in self.task.dimensions:
      self.task.dimensions['os'] = self.api.swarming.prefered_os_dimension(
          self.api.platform.name)
    self.api.swarming.trigger_task(self.task)

  def run(self, **kwargs):
    assert self.task
    self.api.swarming.collect_task(self.task)
    return TestResults.empty()


class V8CompositeSwarmingTest(BaseTest):
  @property
  def composite_tests(self):
    """Returns: An iterable of V8GenericSwarmingTest instances."""
    raise NotImplementedError()  # pragma: no cover

  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return True

  def pre_run(self, test=None, **kwargs):
    self.composites = list(self.composite_tests)
    for c in self.composites:
      c.pre_run(test, **kwargs)

  def run(self, **kwargs):
    for c in self.composites:
      c.run(**kwargs)
    return TestResults.empty()


class V8CheckInitializers(V8GenericSwarmingTest):
  @property
  def title(self):
    return 'Static-Initializers'

  @property
  def extra_args(self):
    return [self.v8.relative_path_to_d8]


class V8Fuzzer(BaseTest):
  def run(self, **kwargs):
    archive = self.api.path['slave_build'].join(
        'fuzz-results-%s.tar.bz2' % self.v8.revision)
    try:
      self.api.step(
        'Fuzz',
        ['bash',
         self.api.path['checkout'].join('tools', 'fuzz-harness.sh'),
         self.v8.relative_path_to_d8,
         archive,
        ],
      )
    except self.api.step.StepFailure as e:
      self.api.gsutil.upload(
          archive,
          'chromium-v8',
          self.api.path.join(
              'fuzzer-archives', self.api.path.basename(archive)),
      )
      raise e
    finally:
      self.api.file.remove('remove archive', archive)
    return TestResults.empty()


# TODO(machenbach): Remove after staging the swarming version below.
class V8DeoptFuzzer(BaseTest):
  def run(self, **kwargs):
    full_args = [
      '--mode', self.api.chromium.c.build_config_fs,
      '--arch', self.api.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
      '--progress', 'verbose',
      '--buildbot',
    ]

    # Add builder-specific test arguments.
    full_args += self.v8.c.testing.test_args

    self.api.python(
      'Deopt Fuzz',
      self.api.path['checkout'].join('tools', 'run-deopt-fuzzer.py'),
      full_args,
      cwd=self.api.path['checkout'],
    )
    return TestResults.empty()


class V8DeoptFuzzerSwarming(V8GenericSwarmingTest):
  @property
  def title(self):
    return 'Deopt Fuzz'

  @property
  def extra_args(self):
    return [
      '--mode', self.api.chromium.c.build_config_fs,
      '--arch', self.api.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
      '--progress', 'verbose',
      '--buildbot',
    ] + self.v8.c.testing.test_args


class V8GCMole(V8CompositeSwarmingTest):
  @property
  def composite_tests(self):
    return [
      V8GenericSwarmingTest(
          self.test_step_config, self.api, self.v8,
          title='GCMole %s' % arch,
          extra_args=[arch],
      ) for arch in ['ia32', 'x64', 'arm', 'arm64']
    ]


class V8SimpleLeakCheck(V8GenericSwarmingTest):
  @property
  def title(self):
    return 'Simple Leak Check'

  @property
  def extra_args(self):
    return [self.v8.relative_path_to_d8, '-e', 'print(1+2)']


V8_NON_STANDARD_TESTS = freeze({
  'fuzz': V8Fuzzer,
  'presubmit': V8Presubmit,
})


TOOL_TO_TEST = freeze({
  'run-deopt-fuzzer': V8DeoptFuzzer,
  'run-tests': V8Test,
})


TOOL_TO_TEST_SWARMING = freeze({
  'check-static-initializers': V8CheckInitializers,
  'run-deopt-fuzzer': V8DeoptFuzzerSwarming,
  'run-gcmole': V8GCMole,
  'run-valgrind': V8SimpleLeakCheck,
  'run-tests': V8SwarmingTest,
})


class Failure(object):
  def __init__(self, test_step_config, failure_dict, duration):
    self.test_step_config = test_step_config
    self.failure_dict = failure_dict
    self.duration = duration

  @staticmethod
  def factory_func(test_step_config):
    def create(failure_dict, duration):
      return Failure(test_step_config, failure_dict, duration)
    return create


class TestResults(object):
  def __init__(self, failures, flakes, infra_failures):
    self.failures = failures
    self.flakes = flakes
    self.infra_failures = infra_failures

  @staticmethod
  def empty():
    return TestResults([], [], [])

  @property
  def is_negative(self):
    return bool(self.failures or self.flakes or self.infra_failures)

  def __add__(self, other):
    return TestResults(
        self.failures + other.failures,
        self.flakes + other.flakes,
        self.infra_failures + other.infra_failures,
    )


def create_test(test_step_config, api, v8_api):
  test_cls = V8_NON_STANDARD_TESTS.get(test_step_config.name)
  if not test_cls:
    # TODO(machenbach): Implement swarming for non-standard tests.
    if v8_api.bot_config.get('enable_swarming') and test_step_config.swarming:
      tools_mapping = TOOL_TO_TEST_SWARMING
    else:
      tools_mapping = TOOL_TO_TEST

    # The tool the test is going to use. Default: V8 test runner (run-tests).
    tool = TEST_CONFIGS[test_step_config.name].get('tool', 'run-tests')
    test_cls = tools_mapping[tool]
  return test_cls(test_step_config, api, v8_api)
