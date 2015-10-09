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
  'mjsunit': {
    'name': 'Mjsunit',
    'tests': ['mjsunit'],
    'can_use_on_swarming_builders': True,
  },
  'mozilla': {
    'name': 'Mozilla',
    'tests': ['mozilla'],
    'gclient_apply_config': ['mozilla_tests'],
  },
  'optimize_for_size': {
    'name': 'OptimizeForSize',
    'tests': ['optimize_for_size'],
    'suite_mapping': ['mjsunit', 'cctest', 'webkit'],
    'test_args': ['--no-variants', '--extra-flags=--optimize-for-size'],
  },
  'simdjs_small': {
    'name': 'SimdJs - small',
    'tests': ['simdjs/shell_test_runner'],
    'test_args': ['--download-data'],
  },
  'simdjs': {
    'name': 'SimdJs - all',
    'tests': ['simdjs'],
    'test_args': ['--download-data'],
  },
  'test262': {
    'name': 'Test262 - no variants',
    'tests': ['test262'],
    'test_args': ['--no-variants', '--download-data'],
  },
  'test262_variants': {
    'name': 'Test262',
    'tests': ['test262'],
    'test_args': ['--download-data'],
  },
  'unittests': {
    'name': 'Unittests',
    'tests': ['unittests'],
    'can_use_on_swarming_builders': True,
  },
  'v8testing': {
    'name': 'Check',
    'tests': ['default'],
    'suite_mapping': ['mjsunit', 'cctest', 'message', 'preparser'],
    'can_use_on_swarming_builders': True,
  },
  'webkit': {
    'name': 'Webkit',
    'tests': ['webkit'],
  },
})


class BaseTest(object):
  def __init__(self, name, api, v8):
    self.name = name
    self.api = api
    self.v8 = v8

  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return False

  def apply_filter(self):
    # Run all tests by default.
    return True

  def pre_run(self, **kwargs):  # pragma: no cover
    pass

  def run(self, **kwargs):  # pragma: no cover
    raise NotImplementedError()

  def rerun(self, failure_dict, **kwargs):  # pragma: no cover
    raise NotImplementedError()

  def gclient_apply_config(self):
    pass


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
    failure_factory=Failure.factory_func(self.name)

    def step_test_data():
      return self.v8.test_api.output_json(
          self.v8._test_data.get('test_failures', False),
          self.v8._test_data.get('wrong_results', False),
          self.v8._test_data.get('flakes', False))

    full_args, env = self.v8._setup_test_runner(test, self.applied_test_filter)
    step_result = self.api.python(
      test['name'],
      self.api.path['checkout'].join('tools', 'run-tests.py'),
      full_args,
      cwd=self.api.path['checkout'],
      env=env,
      # The outcome is controlled by the json test result of the step.
      ok_ret='any',
      step_test_data=step_test_data,
      **kwargs
    )

    # Log used test filters.
    if self.applied_test_filter:
      step_result.presentation.logs['test filter'] = self.applied_test_filter

    # The output is expected to be a list of architecture dicts that
    # each contain a results list. On buildbot, there is only one
    # architecture.
    assert len(step_result.json.output) == 1
    self.v8._update_durations(
        step_result.json.output[0], step_result.presentation)
    failure_log, failures, flake_log, flakes = (
        self.v8._get_failure_logs(step_result.json.output[0], failure_factory))
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

  def rerun(self, failure_dict, **kwargs):
    # Make sure bisection is only activated on builders that give enough
    # information to retry.
    assert failure_dict.get('variant')
    assert failure_dict.get('random_seed')

    # Filter variant manipulation and from test arguments.
    # We'll specify exactly the variant which failed.
    orig_args = [x for x in TEST_CONFIGS[self.name].get('test_args', [])
                 if x != '--no-variants']
    new_args = [
      '--variants', failure_dict['variant'],
      '--random-seed', failure_dict['random_seed'],
    ]
    rerun_config = {
      'name': 'Retry',
      'tests': [failure_dict['name']],
      'test_args' : orig_args + new_args,
    }
    # Switch off test filters on rerun.
    self.applied_test_filter = None
    return self.run(test=rerun_config, **kwargs)

  def gclient_apply_config(self):
    for c in TEST_CONFIGS[self.name].get('gclient_apply_config', []):
      self.api.gclient.apply_config(c)


class V8Presubmit(BaseTest):
  def run(self, **kwargs):
    self.api.python(
      'Presubmit',
      self.api.path['checkout'].join('tools', 'presubmit.py'),
      cwd=self.api.path['checkout'],
    )
    return TestResults.empty()


class V8CheckInitializers(BaseTest):
  def run(self, **kwargs):
    self.api.step(
      'Static-Initializers',
      ['bash',
       self.api.path['checkout'].join('tools', 'check-static-initializers.sh'),
       self.api.path.join(
           self.api.path.basename(self.api.chromium.c.build_dir),
           self.api.chromium.c.build_config_fs,
           'd8'),
      ],
      cwd=self.api.path['checkout'],
    )
    return TestResults.empty()


class V8Fuzzer(BaseTest):
  def run(self, **kwargs):
    assert self.api.chromium.c.HOST_PLATFORM == 'linux'
    try:
      self.api.step(
        'Fuzz',
        ['bash',
         self.api.path['checkout'].join('tools', 'fuzz-harness.sh'),
         self.api.path.join(
             self.api.path.basename(self.api.chromium.c.build_dir),
             self.api.chromium.c.build_config_fs,
             'd8'),
        ],
        cwd=self.api.path['checkout'],
        stdout=self.api.raw_io.output(),
      )
    except self.api.step.StepFailure as e:
      # Check if the fuzzer left a fuzz archive and upload to GS.
      match = re.search(r'^Creating archive (.*)$', e.result.stdout, re.M)
      if match:
        self.api.gsutil.upload(
            self.api.path['checkout'].join(match.group(1)),
            'chromium-v8',
            self.api.path.join('fuzzer-archives', match.group(1)),
        )
      else:  # pragma: no cover
        self.api.step('No fuzzer archive found.', cmd=None)
      raise e
    return TestResults.empty()


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


class V8GCMole(BaseTest):
  def run(self, **kwargs):
    # TODO(machenbach): Make gcmole work with absolute paths. Currently, a
    # particular clang version is installed on one slave in '/b'.
    env = {
      'CLANG_BIN': (
        self.api.path.join('..', '..', '..', '..', '..', 'gcmole', 'bin')
      ),
      'CLANG_PLUGINS': (
        self.api.path.join('..', '..', '..', '..', '..', 'gcmole')
      ),
    }
    for arch in ['ia32', 'x64', 'arm', 'arm64']:
      self.api.step(
        'GCMole %s' % arch,
        ['lua', self.api.path.join('tools', 'gcmole', 'gcmole.lua'), arch],
        cwd=self.api.path['checkout'],
        env=env,
      )
    return TestResults.empty()


class V8SimpleLeakCheck(BaseTest):
  def run(self, **kwargs):
    # TODO(machenbach): Add task kill step for windows.
    relative_d8_path = self.api.path.join(
        self.api.path.basename(self.api.chromium.c.build_dir),
        self.api.chromium.c.build_config_fs,
        'd8')
    step_result = self.api.step(
      'Simple Leak Check',
      ['valgrind', '--leak-check=full', '--show-reachable=yes',
       '--num-callers=20', relative_d8_path, '-e', '"print(1+2)"'],
      cwd=self.api.path['checkout'],
      stderr=self.api.raw_io.output(),
      step_test_data=lambda: self.api.raw_io.test_api.stream_output(
          'tons of leaks', stream='stderr')
    )
    step_result.presentation.logs['stderr'] = step_result.stderr.splitlines()
    if not 'no leaks are possible' in (step_result.stderr):
      step_result.presentation.status = self.api.step.FAILURE
      raise self.api.step.StepFailure('Failed leak check')
    return TestResults.empty()


V8_NON_STANDARD_TESTS = freeze({
  'deopt': V8DeoptFuzzer,
  'fuzz': V8Fuzzer,
  'gcmole': V8GCMole,
  'presubmit': V8Presubmit,
  'simpleleak': V8SimpleLeakCheck,
  'v8initializers': V8CheckInitializers,
})


class Failure(object):
  def __init__(self, test_config, failure_dict, duration):
    self.test_config = test_config
    self.failure_dict = failure_dict
    self.duration = duration

  @staticmethod
  def factory_func(test_config):
    def create(failure_dict, duration):
      return Failure(test_config, failure_dict, duration)
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


def create_test(test, v8_api, api):
  return V8_NON_STANDARD_TESTS.get(test, V8Test)(test, v8_api, api)

