# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import json
import re
import urllib
from recipe_engine.types import freeze


MONORAIL_SEARCH_FLAKY_BUGS_TEMPLATE = (
    'https://bugs.chromium.org/p/v8/issues/list?q=label:Hotlist-Flake+%(name)s')

MONORAIL_FILE_FLAKY_BUG_TEMPLATE = (
    'https://bugs.chromium.org/p/v8/issues/entry?template=Report+flaky+test&'
    'summary=%(name)s+starts+flaking&description=Failing+test:+%(name)s%%0A'
    'Failure+link:+%(build_link)s%%0ALink+to+Flako+run:+%%3Cinsert%%3E')

MAX_FLAKE_LINKS = 5


# pylint: disable=abstract-method

class V8Variant(object):
  """Immutable class representing testing variants passed to v8."""
  def __init__(self, *variants):
    self.variants = variants

  def __str__(self):
    return ' '.join(self.variants)

  def pack(self):
    """Returns a serializable version of this object.

    This method is the counterpart to the method below.
    """
    return str(self)

  @staticmethod
  def unpack(packed):
    """Constructs a variant object from a serialized version of this class.

    This method is the counterpart to the method above.
    """
    return V8Variant(*(packed or '').split(' '))


def test_args_from_variants(*variants):
  """Merge variant specification from bot, test type and test step.

  Returns: Flags for the v8 test driver with either 1) all specific
      variants if any, or 2) flags for exhaustive testing.
  """
  specific_variants = [v for v in variants if v]
  if specific_variants:
    _variants = sorted(list(set(itertools.chain(
        *[v.variants for v in specific_variants]))))
  else:
    _variants = ['more', 'dev']
  assert _variants
  return ['--variants=' + ','.join(_variants)]


TEST_CONFIGS = freeze({
  'benchmarks': {
    'name': 'Benchmarks',
    'tests': ['benchmarks'],
  },
  'd8testing': {
    'name': 'Check - d8',
    'tests': ['d8_default'],
    'suite_mapping': [
      'debugger',
      'intl',
      'message',
      'mjsunit',
      'preparser',
      'webkit',
    ],
  },
  'd8testing_random_gc': {
    'name': 'Check - d8',
    'tests': ['d8_default'],
    'suite_mapping': [
      'debugger',
      'intl',
      'message',
      'mjsunit',
      'preparser',
      'webkit',
    ],
    'test_args': ['--random-gc-stress'],
  },
  'jsfunfuzz': {
    'tool': 'jsfunfuzz',
    'isolated_target': 'jsfunfuzz',
  },
  'gcmole': {
    'tool': 'run-gcmole',
    'isolated_target': 'run-gcmole',
  },
  'mjsunit': {
    'name': 'Mjsunit',
    'tests': ['mjsunit'],
  },
  'mjsunit_sp_frame_access': {
    'name': 'Mjsunit - sp frame access',
    'tests': ['mjsunit'],
    'test_args': ['--extra-flags=--turbo_sp_frame_access'],
    'variants': V8Variant('default'),
  },
  'mozilla': {
    'name': 'Mozilla',
    'tests': ['mozilla'],
  },
  'numfuzz': {
    'name': 'Num Fuzz',
    'tool': 'run-num-fuzzer',
    'isolated_target': 'run-num-fuzzer',
    'idempotent': False,
    'use_random_seed': False,
    'variants': V8Variant('default'),
  },
  'optimize_for_size': {
    'name': 'OptimizeForSize',
    'tests': ['optimize_for_size'],
    'suite_mapping': [
      'cctest',
      'debugger',
      'mjsunit',
      'inspector',
      'intl',
      'webkit',
    ],
    'test_args': ['--extra-flags=--optimize-for-size'],
    'variants': V8Variant('default'),
  },
  'test262': {
    'name': 'Test262 - no variants',
    'tests': ['test262'],
    'variants': V8Variant('default'),
  },
  'test262_variants': {
    'name': 'Test262',
    'tests': ['test262'],
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
      'cctest',
      'debugger',
      'fuzzer',
      'inspector',
      'intl',
      'message',
      'mjsunit',
      'mkgrokdump',
      'preparser',
      'unittests',
      'wasm-spec-tests',
      'webkit',
    ],
  },
  'webkit': {
    'name': 'Webkit',
    'tests': ['webkit'],
  },
})


class NullCoverageContext(object):
  """Null object to represent testing without collecting coverage."""
  def get_test_runner_args(self):
    return []

  def get_swarming_collect_args(self):
    return []

  def setup(self):
    pass

  def post_run(self):
    pass

  def maybe_upload(self):
    pass

NULL_COVERAGE = NullCoverageContext()


class SanitizerCoverageContext(object):
  """Context during testing to collect coverage data.

  Only testing on swarming is supported.
  """
  def __init__(self, api):
    self.api = api
    self.coverage_dir = api.path.mkdtemp('coverage_output')

  def get_test_runner_args(self):
    """Returns the test runner arguments for collecting coverage data."""
    return ['--sancov-dir', '${ISOLATED_OUTDIR}']

  def get_swarming_collect_args(self):
    """Returns the swarming collect step's arguments for merging."""
    return [
      '--coverage-dir', self.coverage_dir,
      '--sancov-merger', self.api.path['checkout'].join(
          'tools', 'sanitizers', 'sancov_merger.py'),
    ]

  def setup(self):
    """Build data file with initial zero coverage data.

    To be called before any coverage data from testing is merged in.
    """
    self.api.python(
        'Initialize coverage data',
        self.api.path['checkout'].join(
            'tools', 'sanitizers', 'sancov_formatter.py'),
        [
          'all',
          '--json-output', self.coverage_dir.join('data.json'),
        ],
    )

  def post_run(self):
    """Merge coverage data from one test run.

    To be called after every test step. Requires existing initial zero
    coverage data, obtained by calling setup().
    """
    self.api.python(
        'Merge coverage data',
        self.api.path['checkout'].join(
            'tools', 'sanitizers', 'sancov_formatter.py'),
        [
          'merge',
          '--json-input', self.coverage_dir.join('data.json'),
          '--json-output', self.coverage_dir.join('data.json'),
          '--coverage-dir', self.coverage_dir,
        ],
    )

    self.api.python.inline(
        'Purge sancov files',
        """
        import glob
        import os
        for f in glob.glob('%s'):
          os.remove(f)
        """ % self.coverage_dir.join('*.sancov'),
    )

  def maybe_upload(self):
    """Uploads coverage data to google storage if on tryserver."""

    if self.api.tryserver.gerrit_change:
      cl = self.api.tryserver.gerrit_change
      results_path = 'tryserver/sanitizer_coverage/gerrit/%d/%d/%s%d' % (
        cl.change, cl.patchset, self.api.platform.name, self.api.v8.target_bits)


      self.api.gsutil.upload(
          self.coverage_dir.join('data.json'),
          'chromium-v8',
          results_path + '/data.json',
      )

      data_dir = self.api.path.mkdtemp('coverage_data')
      self.api.python(
          'Split coverage data',
          self.api.path['checkout'].join(
              'tools', 'sanitizers', 'sancov_formatter.py'),
          [
            'split',
            '--json-input', self.coverage_dir.join('data.json'),
            '--output-dir', data_dir,
          ],
          # Allow to work with older v8 revisions that don't have the split
          # function in which case the directory will stay empty.
          # TODO(machenbach): Remove this when v8's passed CP 34834 + 1000.
          ok_ret='any',
      )

      self.api.gsutil(
          [
            '-m', 'cp', '-a', 'public-read', '-R', data_dir.join('*'),
            'gs://chromium-v8/%s/' % results_path,
          ],
          'coverage data',
          # Same as in the step above.
          ok_ret='any',
      )


class BaseTest(object):
  def __init__(self, test_step_config, api):
    self.test_step_config = test_step_config
    self.name = test_step_config.name
    self.api = api

  @property
  def id(self):
    """Identifier for deduping identical test configs."""
    return self.test_step_config.name + self.test_step_config.step_name_suffix

  def _get_isolated_hash(self, test):
    isolated = test.get('isolated_target')
    if not isolated:
      # Normally we run only one test and the isolate name is the same as the
      # test name.
      assert len(test['tests']) == 1
      isolated = test['tests'][0]

    isolated_hash = self.api.v8.isolated_tests.get(isolated)

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

  def pre_run(self, test=None, coverage_context=NULL_COVERAGE, **kwargs):
    pass  # pragma: no cover

  def run(self, test=None, coverage_context=NULL_COVERAGE, **kwargs):
    raise NotImplementedError()  # pragma: no cover

  def rerun(self, failure_dict, **kwargs):  # pragma: no cover
    raise NotImplementedError()


class V8Test(BaseTest):
  def __init__(self, *args, **kwargs):
    super(V8Test, self).__init__(*args, **kwargs)
    self.applied_test_filter = ''

  def apply_filter(self):
    test_config = self.api.v8.test_configs[self.name]
    self.applied_test_filter = self.api.v8._applied_test_filter(test_config)
    if self.api.v8.test_filter and not self.applied_test_filter:
      self.api.step(test_config['name'] + ' - skipped', cmd=None)
      return False
    return True

  def run(self, test=None, coverage_context=NULL_COVERAGE, **kwargs):
    test = test or self.api.v8.test_configs[self.name]

    full_args, env = self.api.v8._setup_test_runner(
        test, self.applied_test_filter, self.test_step_config)
    full_args += [
      '--json-test-results',
      self.api.json.output(add_json_log=False),
    ]
    with self.api.context(cwd=self.api.path['checkout'], env=env):
      self.api.python(
        test['name'] + self.test_step_config.step_name_suffix,
        self.api.path['checkout'].join('tools', 'run-tests.py'),
        full_args,
        step_test_data=self.api.v8.test_api.output_json,
        **kwargs
      )
    return self.post_run(test)

  def post_run(self, test, coverage_context=NULL_COVERAGE):
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
    self.api.v8._update_durations(json_output[0], step_result.presentation)
    failure_factory = Failure.factory_func(self)
    failure_log, failures, flake_log, flakes = (
        self.api.v8._get_failure_logs(json_output[0], failure_factory))
    self.api.v8._update_failure_presentation(
        failure_log, failures, step_result.presentation)

    if failure_log and failures:
      # Mark the test step as failure only if there were real failures (i.e.
      # non-flakes) present.
      step_result.presentation.status = self.api.step.FAILURE

    infra_failures = []
    if 'UNRELIABLE_RESULTS' in json_output[0].get('tags', []):
      infra_failures.append('One ore more shards did not complete.')
      step_result.presentation.status = self.api.step.EXCEPTION

    if flake_log and flakes:
      # Emit a separate step to show flakes from the previous step
      # to not close the tree.
      step_result = self.api.step(
          test['name'] + self.test_step_config.step_name_suffix + ' (flakes)',
          cmd=None)
      # TODO(sergiyb): Use WARNING result type after crbug.com/854099 is fixed.
      step_result.presentation.status = self.api.step.FAILURE
      self.api.v8._update_failure_presentation(
            flake_log, flakes, step_result.presentation)
      self._add_flake_links(flakes, step_result.presentation)

    coverage_context.post_run()

    return TestResults(failures, flakes, infra_failures)

  def _add_flake_links(self, flakes, presentation):
    """Adds links to search/file bugs for up to MAX_FLAKE_LINKS flaky tests."""
    for flake in flakes[:MAX_FLAKE_LINKS]:
      test_name = flake.results[0]['name']
      ui_label = self.api.v8.ui_test_label(test_name)
      link_params = {
        'name': test_name,
        'build_link': urllib.quote(self.api.buildbucket.build_url()),
      }
      presentation.links['%s (bugs)' % ui_label] = (
          MONORAIL_SEARCH_FLAKY_BUGS_TEMPLATE % link_params)
      presentation.links['%s (new)' % ui_label] = (
          MONORAIL_FILE_FLAKY_BUG_TEMPLATE % link_params)
    if len(flakes) > MAX_FLAKE_LINKS:  # pragma: no cover
      presentation.step_text += (
          'too many flakes, only showing some links below<br/>')

  def _setup_rerun_config(self, failure_dict):
    """Return: A test config that reproduces a specific failure."""
    # Make sure bisection is only activated on builders that give enough
    # information to retry.
    assert failure_dict.get('variant')
    assert failure_dict.get('random_seed')

    orig_config = self.api.v8.test_configs[self.name]

    # If not specified, the isolated target is the same as the first test of
    # the original list. We need to set it explicitly now, as the tests
    # parameter changes on rerun, but the isolated target is still the same.
    isolated_target = orig_config.get(
        'isolated_target', orig_config['tests'][0])

    test_args = list(orig_config.get('test_args', [])) + [
      '--random-seed', failure_dict['random_seed'],
    ]

    rerun_config = {
      'name': 'Retry',
      'isolated_target': isolated_target,
      'tests': [failure_dict['name']],
      'test_args': test_args,
      'variants': V8Variant(failure_dict['variant'])
    }

    # Switch off test filters on rerun.
    self.applied_test_filter = None
    return rerun_config

  def rerun(self, failure_dict, **kwargs):
    return self.run(test=self._setup_rerun_config(failure_dict), **kwargs)


def _trigger_swarming_task(api, task, test_step_config):
  """Triggers a task on swarming setting custom dimensions and task attributes.

  Args:
    api: Recipe modules api.
    task: Task object from swarming recipe module.
    test_step_config: Configuration object used to configure this task. Contains
        e.g. dimension and task-attribute overrides.
  """
  # Add custom dimensions.
  task.dimensions.update(api.v8.bot_config.get('swarming_dimensions', {}))

  # Override with per-test dimensions.
  task.dimensions.update(test_step_config.swarming_dimensions or {})

  # Override cpu and gpu defaults for Android as such devices don't have these
  # dimensions.
  if task.dimensions['os'] == 'Android':
    task.dimensions.pop('cpu')
    task.dimensions.pop('gpu')

  # Override attributes with per-test settings.
  for k, v in test_step_config.swarming_task_attrs.iteritems():
    setattr(task, k, v)

  api.chromium_swarming.trigger_task(task)


class V8SwarmingTest(V8Test):
  def __init__(self, *args, **kwargs):
    super(V8SwarmingTest, self).__init__(*args, **kwargs)
    self.task = None
    self.test = None

  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return True

  def _v8_collect_step(self, task, coverage_context=NULL_COVERAGE, **kwargs):
    """Produces a step that collects and processes a result of a v8 task."""
    # Placeholder for the merged json output.
    json_output = self.api.json.output(add_json_log=False)

    # Shim script's own arguments.
    args = [
      '--temp-root-dir', self.api.path['tmp_base'],
      '--merged-test-output', json_output,
    ] + coverage_context.get_swarming_collect_args()

    # Arguments for actual 'collect' command.
    args.append('--')
    args.extend(self.api.chromium_swarming.get_collect_cmd_args(task))

    with self.api.swarming_client.on_path():
      return self.api.build.python(
          name=self.test['name'] + self.test_step_config.step_name_suffix,
          script=self.api.v8.resource('collect_v8_task.py'),
          args=args,
          allow_subannotations=True,
          infra_step=True,
          step_test_data=kwargs.pop('step_test_data', None),
          **kwargs)

  def pre_run(self, test=None, coverage_context=NULL_COVERAGE, **kwargs):
    # Set up arguments for test runner.
    self.test = test or self.api.v8.test_configs[self.name]
    extra_args, _ = self.api.v8._setup_test_runner(
        self.test, self.applied_test_filter, self.test_step_config)

    # Let json results be stored in swarming's output folder. The collect
    # step will copy the folder's contents back to the client.
    extra_args += [
      '--swarming',
      '--json-test-results',
      '${ISOLATED_OUTDIR}/output.json',
    ] + coverage_context.get_test_runner_args()

    # Initialize number of shards, either per test or per builder.
    shards = 1
    if self.api.v8.c.testing.may_shard:
      shards = self.test_step_config.shards

    command = 'tools/%s.py' % self.test.get('tool', 'run-tests')
    idempotent = self.test.get('idempotent')

    # Initialize swarming task with custom data-collection step for v8
    # test-runner output.
    self.task = self.api.chromium_swarming.task(
        title=self.test['name'] + self.test_step_config.step_name_suffix,
        idempotent=idempotent,
        isolated_hash=self._get_isolated_hash(self.test),
        shards=shards,
        raw_cmd=[command] + extra_args,
    )
    self.task.collect_step = lambda task, **kw: (
        self._v8_collect_step(task, coverage_context, **kw))

    _trigger_swarming_task(self.api, self.task, self.test_step_config)

  def run(self, coverage_context=NULL_COVERAGE, **kwargs):
    # TODO(machenbach): Soften this when softening 'assert isolated_hash'
    # above.
    assert self.task
    result = TestResults.empty()
    try:
      # Collect swarming results. Use the same test simulation data for the
      # swarming collect step like for local testing.
      self.api.chromium_swarming.collect_task(
        self.task,
        step_test_data=self.api.v8.test_api.output_json,
      )
    except self.api.step.InfraFailure as e:
      result += TestResults.infra_failure(e)

    return result + self.post_run(self.test, coverage_context)

  def rerun(self, failure_dict, **kwargs):
    self.pre_run(test=self._setup_rerun_config(failure_dict), **kwargs)
    return self.run(**kwargs)


class V8GenericSwarmingTest(BaseTest):
  # FIXME: BaseTest.rerun is an abstract method which isn't implemented in this
  # class.  Should it be abstract?
  def __init__(self, test_step_config, api, title=None, command=None):
    super(V8GenericSwarmingTest, self).__init__(test_step_config, api)
    self._command = command or []
    self._title = (
        title or
        self.api.v8.test_configs[self.name].get('name', 'Generic test'))
    self.test = None
    self.task = None

  @property
  def title(self):
    return self._title + self.test_step_config.step_name_suffix

  @property
  def command(self):
    """Command to pass to the swarming task."""
    return self._command

  @property
  def task_output_dir(self):
    return None  # pragma: no cover

  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return True

  def pre_run(self, test=None, **kwargs):
    self.test = test or self.api.v8.test_configs[self.name]
    self.task = self.api.chromium_swarming.task(
        title=self.title,
        isolated_hash=self._get_isolated_hash(self.test),
        task_output_dir=self.task_output_dir,
        raw_cmd=self.command,
    )

    _trigger_swarming_task(self.api, self.task, self.test_step_config)

  def run(self, **kwargs):
    assert self.task
    self.api.chromium_swarming.collect_task(self.task)
    return TestResults.empty()


class V8CompositeSwarmingTest(BaseTest):
  # FIXME: BaseTest.rerun is an abstract method which isn't implemented in this
  # class.  Should it be abstract?
  def __init__(self, *args, **kwargs):
    super(V8CompositeSwarmingTest, self).__init__(*args, **kwargs)
    self.composites = []

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
  def command(self):
    return [
      'tools/check-static-initializers.sh',
      self.api.v8.relative_path_to_d8,
    ]


class V8Fuzzer(V8GenericSwarmingTest):
  def __init__(self, test_step_config, api, title='Generic test',
               command=None):
    self.output_dir = api.path.mkdtemp('swarming_output')
    self.archive = 'fuzz-results-%s.tar.bz2' % (
        api.properties['parent_got_revision'])
    super(V8Fuzzer, self).__init__(
        test_step_config, api,
        title='Fuzz',
        command=[
          'tools/jsfunfuzz/fuzz-harness.sh',
          api.v8.relative_path_to_d8,
          '${ISOLATED_OUTDIR}/%s' % self.archive,
        ],
    )

  @property
  def task_output_dir(self):
    return self.output_dir

  def run(self, **kwargs):
    try:
      super(V8Fuzzer, self).run(**kwargs)
    except self.api.step.StepFailure as e:
      self.api.gsutil.upload(
          self.output_dir.join(self.task.get_task_shard_output_dirs()[0],
                               self.archive),
          'chromium-v8',
          self.api.path.join('fuzzer-archives', self.archive),
      )
      raise e
    return TestResults.empty()


class V8GCMole(V8CompositeSwarmingTest):
  @property
  def composite_tests(self):
    return [
      V8GenericSwarmingTest(
          self.test_step_config, self.api,
          title='GCMole %s' % arch,
          command=['tools/gcmole/run-gcmole.py', arch],
      ) for arch in ['ia32', 'x64', 'arm', 'arm64']
    ]


TOOL_TO_TEST = freeze({
  'run-tests': V8Test,
})


TOOL_TO_TEST_SWARMING = freeze({
  'check-static-initializers': V8CheckInitializers,
  'jsfunfuzz': V8Fuzzer,
  'run-gcmole': V8GCMole,
  'run-num-fuzzer': V8SwarmingTest,
  'run-tests': V8SwarmingTest,
})


class Failure(object):
  """Represents a test run leading to a failure (possibly re-run several times).
  """
  def __init__(self, test, results):
    """
    Args:
      test: Test (type V8Test) that led to this failure.
      results: List of failure dicts with one item per run of the test. The
          first item is the original failure, the other items are re-runs for
          flake checking. Each failure dict consists of the data as returned by
          the V8-side test runner.
    """
    assert results
    assert test
    self.test = test
    self.results = results
    # A failure is flaky if not all results are the same (e.g. all 'FAIL').
    self.is_flaky = not all(
        x['result'] == results[0]['result'] for x in results)

  @property
  def failure_dict(self):
    return self.results[0]

  @property
  def duration(self):
    return self.failure_dict['duration']

  @property
  def test_step_config(self):
    return self.test.test_step_config

  @property
  def api(self):
    return self.test.api

  def _format_swarming_dimensions(self, dims):
    return ['%s:%s' % (k, dims[k]) for k in sorted(dims.keys())]

  def _flako_cmd_line(self):
    """Returns the command line for bisecting this failure with flako."""
    test_config = self.api.v8.test_configs[self.test.name]
    properties = {
      # This assumes the builder's master is the same as the tester.
      'bisect_mastername': self.api.properties['mastername'],
      # Use builds from parent builder to bisect if any.
      'bisect_buildername': self.api.properties.get(
          'parent_buildername') or self.api.buildbucket.builder_name,
      # Start bisecting backwards at the revision that was tested.
      'to_revision': self.api.buildbucket.gitiles_commit.id,
      # Use the same dimensions as the swarming task that ran this test.
      'swarming_dimensions': self._format_swarming_dimensions(
          self.test.task.dimensions),
      # The isolated name is either specified in the test configurations or
      # corresponds to the name of the test suite.
      'isolated_name': test_config.get('isolated_target') or
                       test_config['tests'][0],
      # Full qualified test name that failed (e.g. mjsunit/foo/bar).
      'test_name': self.results[0]['name'],
      # Release or Debug.
      'build_config': self.api.chromium.c.build_config_fs,
      # Add timeout default for convenience.
      'timeout_sec': 60,
      # Add total timeout default for convenience.
      'total_timeout_sec': 120,
      # The variant the failing test ran in.
      'variant': self.results[0]['variant'],
      # Extra arguments passed to the V8 test runner.
      # TODO(machenbach): The api should hide the details how to get the args.
      'extra_args': list(test_config.get('test_args', [])) +
                    list(self.api.v8.c.testing.test_args) +
                    list(self.test_step_config.test_args),
    }
    return (
        'echo \'%s\' | '
        'buildbucket.py put -b luci.v8.try.triggered -n v8_flako -p -'
        % json.dumps(properties, sort_keys=True)
    )

  def log_lines(self):
    """Return a list of lines for logging all runs of this failure."""
    lines = []

    # Add common description for multiple runs.
    flaky_suffix = ' (flaky in a repeated run)' if self.is_flaky else ''
    lines.append('Test: %s%s' % (self.results[0]['name'], flaky_suffix))
    lines.append('Flags: %s' % ' '.join(self.results[0]['flags']))
    lines.append('Command: %s' % self.results[0]['command'])
    lines.append('Variant: %s' % self.results[0]['variant'])
    lines.append('')
    lines.append('Build environment:')
    if self.api.v8.build_environment is None:
      lines.append(
          'Not available. Please look up the builder\'s configuration.')
    else:
      for key in sorted(self.api.v8.build_environment):
        lines.append(' %s: %s' % (key, self.api.v8.build_environment[key]))
    lines.append('')

    # Print the command line for flake bisect if the test is flaky. Only
    # supports tests run on swarming and CI.
    if (self.is_flaky and
        isinstance(self.test, V8SwarmingTest) and
        not self.api.tryserver.is_tryserver):
      lines.append('Trigger flake bisect on command line:')
      lines.append(self._flako_cmd_line())
      lines.append('')

    # Add results for each run of a command.
    for result in sorted(self.results, key=lambda r: int(r['run'])):
      lines.append('Run #%d' % int(result['run']))
      lines.append('Exit code: %s' % result['exit_code'])
      lines.append('Result: %s' % result['result'])
      if result.get('expected'):
        lines.append('Expected outcomes: %s' % ", ".join(result['expected']))
      lines.append(
          'Duration: %s' % self.api.v8.format_duration(result['duration']))
      lines.append('')
      if result['stdout']:
        lines.append('Stdout:')
        lines.extend(result['stdout'].splitlines())
        lines.append('')
      if result['stderr']:
        lines.append('Stderr:')
        lines.extend(result['stderr'].splitlines())
        lines.append('')
    return lines

  @staticmethod
  def factory_func(test):
    def create(results):
      return Failure(test, results)
    return create


class TestResults(object):
  def __init__(self, failures, flakes, infra_failures):
    self.failures = failures
    self.flakes = flakes
    self.infra_failures = infra_failures

  @staticmethod
  def empty():
    return TestResults([], [], [])

  @staticmethod
  def infra_failure(exception):
    return TestResults([], [], [exception])

  @property
  def is_negative(self):
    return bool(self.failures or self.flakes or self.infra_failures)

  @property
  def has_failures(self):
    return bool(self.failures or self.infra_failures)

  def __add__(self, other):
    return TestResults(
        self.failures + other.failures,
        self.flakes + other.flakes,
        self.infra_failures + other.infra_failures,
    )


def create_test(test_step_config, api):
  if api.v8.bot_config.get('enable_swarming', True):
    tools_mapping = TOOL_TO_TEST_SWARMING
  else:
    tools_mapping = TOOL_TO_TEST

  # The tool the test is going to use. Default: V8 test runner (run-tests).
  tool = api.v8.test_configs[test_step_config.name].get('tool', 'run-tests')
  test_cls = tools_mapping[tool]
  return test_cls(test_step_config, api)
