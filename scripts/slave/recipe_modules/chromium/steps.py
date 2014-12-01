# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re


class Test(object):
  """
  Base class for tests that can be retried after deapplying a previously
  applied patch.
  """

  def __init__(self):
    super(Test, self).__init__()
    self._test_runs = {}

  @property
  def abort_on_failure(self):
    """If True, abort build when test fails."""
    return False

  @property
  def name(self):  # pragma: no cover
    """Name of the test."""
    raise NotImplementedError()

  @property
  def isolate_target(self):
    """Returns isolate target name. Defaults to name."""
    return self.name

  @staticmethod
  def compile_targets(api):
    """List of compile targets needed by this test."""
    raise NotImplementedError()

  def pre_run(self, api, suffix):  # pragma: no cover
    """Steps to execute before running the test."""
    return []

  def run(self, api, suffix):  # pragma: no cover
    """Run the test. suffix is 'with patch' or 'without patch'."""
    raise NotImplementedError()

  def post_run(self, api, suffix):  # pragma: no cover
    """Steps to execute after running the test."""
    return []

  def has_valid_results(self, api, suffix):  # pragma: no cover
    """
    Returns True if results (failures) are valid.

    This makes it possible to distinguish between the case of no failures
    and the test failing to even report its results in machine-readable
    format.
    """
    raise NotImplementedError()

  def failures(self, api, suffix):  # pragma: no cover
    """Return list of failures (list of strings)."""
    raise NotImplementedError()

  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return False

  def _step_name(self, suffix):
    """Helper to uniformly combine tests's name with a suffix."""
    if not suffix:
      return self.name
    return '%s (%s)' % (self.name, suffix)


class ArchiveBuildStep(Test):
  def __init__(self, gs_bucket, gs_acl=None):
    self.gs_bucket = gs_bucket
    self.gs_acl = gs_acl

  def run(self, api, suffix):
    return api.chromium.archive_build(
        'archive build',
        self.gs_bucket,
        gs_acl=self.gs_acl,
    )

  @staticmethod
  def compile_targets(_):
    return []


class ScriptTest(Test):  # pylint: disable=W0232
  """
  Test which uses logic from script inside chromium repo.

  This makes it possible to keep the logic src-side as opposed
  to the build repo most Chromium developers are unfamiliar with.

  Another advantage is being to test changes to these scripts
  on trybots.

  All new tests are strongly encouraged to use this infrastructure.
  """

  def __init__(self, name, script, all_compile_targets):
    super(ScriptTest, self).__init__()
    self._name = name
    self._script = script
    self._all_compile_targets = all_compile_targets

  @property
  def name(self):
    return self._name

  def compile_targets(self, api):
    try:
      return self._all_compile_targets[self._script]
    except KeyError:
      # Not all scripts will have test data inside recipes,
      # so return a default value.
      # TODO(phajdan.jr): Revisit this when all script tests
      # lists move src-side. We should be able to provide
      # test data then.
      if api.chromium._test_data.enabled:
        return []

      raise

  def run(self, api, suffix):
    name = self.name
    if suffix:
      name += ' (%s)' % suffix

    run_args = []
    if suffix == 'without patch':
      run_args.extend([
          '--filter-file', api.json.input(self.failures(api, 'with patch'))
      ])

    try:
      api.python(
          name,
          # Enforce that all scripts are in the specified directory
          # for consistency.
          api.path['checkout'].join(
              'testing', 'scripts', api.path.basename(self._script)),
          args=(api.chromium.get_common_args_for_scripts() +
                ['run', '--output', api.json.output()] +
                run_args),
          step_test_data=lambda: api.json.test_api.output(
              {'valid': True, 'failures': []}))
    finally:
      self._test_runs[suffix] = api.step.active_result

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    try:
      # Make sure the JSON includes all necessary data.
      self.failures(api, suffix)

      return self._test_runs[suffix].json.output['valid']
    except Exception:
      return False

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.output['failures']


class CheckdepsTest(Test):  # pylint: disable=W0232
  name = 'checkdeps'

  @staticmethod
  def compile_targets(_):
    return []

  def run(self, api, suffix):
    try:
      api.chromium.checkdeps(suffix)
    finally:
      self._test_runs[suffix] = api.step.active_result

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    return self._test_runs[suffix].json.output is not None

  def failures(self, api, suffix):
    results = self._test_runs[suffix].json.output
    result_set = set()
    for result in results:
      for violation in result['violations']:
        result_set.add((result['dependee_path'], violation['include_path']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]


class CheckpermsTest(Test):  # pylint: disable=W0232
  name = 'checkperms'

  @staticmethod
  def compile_targets(_):
    return []

  def run(self, api, suffix):
    try:
      api.chromium.checkperms(suffix)
    finally:
      self._test_runs[suffix] = api.step.active_result

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    return self._test_runs[suffix].json.output is not None

  def failures(self, api, suffix):
    results = self._test_runs[suffix].json.output
    result_set = set()
    for result in results:
      result_set.add((result['rel_path'], result['error']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]

class ChecklicensesTest(Test):  # pylint: disable=W0232
  name = 'checklicenses'

  @staticmethod
  def compile_targets(_):
    return []

  def run(self, api, suffix):
    try:
      api.chromium.checklicenses(suffix)
    finally:
      self._test_runs[suffix] = api.step.active_result

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    return self._test_runs[suffix].json.output is not None

  def failures(self, api, suffix):
    results = self._test_runs[suffix].json.output
    result_set = set()
    for result in results:
      result_set.add((result['filename'], result['license']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]


class LocalGTestTest(Test):
  def __init__(self, name, args=None, target_name=None, use_isolate=False,
               revision=None, webkit_revision=None, **runtest_kwargs):
    """Constructs an instance of LocalGTestTest.

    Args:
      name: Displayed name of the test. May be modified by suffixes.
      args: Arguments to be passed to the test.
      target_name: Actual name of the test. Defaults to name.
      use_isolate: When set, uses api.isolate.runtest to invoke the test.
          Calling recipe should have isolate in their DEPS.
      revision: Revision of the Chrome checkout.
      webkit_revision: Revision of the WebKit checkout.
      runtest_kwargs: Additional keyword args forwarded to the runtest.
    """
    super(LocalGTestTest, self).__init__()
    self._name = name
    self._args = args or []
    self._target_name = target_name
    self._use_isolate = use_isolate
    self._revision = revision
    self._webkit_revision = webkit_revision
    self._runtest_kwargs = runtest_kwargs

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def isolate_target(self):
    return self.target_name

  def compile_targets(self, api):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return [self.target_name + '_apk']

    # On iOS we rely on 'All' target being compiled instead of using
    # individual targets.
    if api.chromium.c.TARGET_PLATFORM == 'ios':
      return []

    return [self.target_name]

  def run(self, api, suffix):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return api.chromium_android.run_test_suite(self.target_name, self._args)

    # Copy the list because run can be invoked multiple times and we modify
    # the local copy.
    args = self._args[:]

    if suffix == 'without patch':
      args.append(api.chromium.test_launcher_filter(
          self.failures(api, 'with patch')))

    kwargs = {}
    kwargs['name'] = self._step_name(suffix)
    kwargs['xvfb'] = True
    kwargs['test_type'] = self.name
    kwargs['annotate'] = 'gtest'
    kwargs['args'] = args
    kwargs['step_test_data'] = lambda: api.json.test_api.canned_gtest_output(
        True)
    kwargs['test_launcher_summary_output'] = api.json.gtest_results(
        add_json_log=False)
    kwargs.update(self._runtest_kwargs)

    try:
      if self._use_isolate:
        api.isolate.runtest(self.target_name, self._revision,
                            self._webkit_revision, **kwargs)
      else:
        api.chromium.runtest(self.target_name, revision=self._revision,
                             webkit_revision=self._webkit_revision, **kwargs)
    finally:
      step_result = api.step.active_result
      self._test_runs[suffix] = step_result

      r = step_result.json.gtest_results
      p = step_result.presentation

      if r.valid:
        p.step_text += api.test_utils.format_step_text([
            ['failures:', r.failures]
        ])
    return step_result

  def has_valid_results(self, api, suffix):
    gtest_results = self._test_runs[suffix].json.gtest_results
    if not gtest_results.valid:  # pragma: no cover
      return False
    global_tags = gtest_results.raw.get('global_tags', [])
    return 'UNRELIABLE_RESULTS' not in global_tags

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.gtest_results.failures


def generate_gtest(api, mastername, buildername, test_spec,
                   enable_swarming=False, scripts_compile_targets=None):
  def canonicalize_test(test):
    if isinstance(test, basestring):
      canonical_test = {'test': test}
    else:
      canonical_test = test.copy()

    canonical_test.setdefault('shard_index', 0)
    canonical_test.setdefault('total_shards', 1)
    return canonical_test

  def get_tests(api):
    return [canonicalize_test(t) for t in
            test_spec.get(buildername, {}).get('gtest_tests', [])]

  for test in get_tests(api):
    args = test.get('args', [])
    if test['shard_index'] != 0 or test['total_shards'] != 1:
      args.extend(['--test-launcher-shard-index=%d' % test['shard_index'],
                   '--test-launcher-total-shards=%d' % test['total_shards']])
    use_swarming = False
    swarming_shards = 1
    if enable_swarming:
      swarming_spec = test.get('swarming', {})
      if swarming_spec.get('can_use_on_swarming_builders'):
        use_swarming = True
        swarming_shards = swarming_spec.get('shards', 1)
    yield GTestTest(str(test['test']), args=args, flakiness_dash=True,
                    enable_swarming=use_swarming,
                    swarming_shards=swarming_shards)


def generate_script(api, mastername, buildername, test_spec,
                    enable_swarming=False, scripts_compile_targets=None):
  for script_spec in test_spec.get(buildername, {}).get('scripts', []):
    yield ScriptTest(
        str(script_spec['name']),
        script_spec['script'],
        scripts_compile_targets)


class DynamicPerfTests(Test):
  def __init__(self, browser, perf_id, shard_index, num_shards):
    self.browser = browser
    self.perf_id = perf_id
    self.shard_index = shard_index
    self.num_shards = num_shards

  @property
  def name(self):
    return 'dynamic_perf_tests'

  def run(self, api, suffix):
    exception = None
    tests = api.chromium.list_perf_tests(self.browser, self.num_shards)
    tests = dict((k, v) for k, v in tests.json.output['steps'].iteritems()
        if v['device_affinity'] == self.shard_index)
    for test_name, test in sorted(tests.iteritems()):
      test_name = str(test_name)
      annotate = api.chromium.get_annotate_by_test_name(test_name)
      cmd = test['cmd'].split()
      try:
        api.chromium.runtest(
            cmd[1] if len(cmd) > 1 else cmd[0],
            args=cmd[2:],
            name=test_name,
            annotate=annotate,
            python_mode=True,
            results_url='https://chromeperf.appspot.com',
            perf_dashboard_id=test.get('perf_dashboard_id', test_name),
            perf_id=self.perf_id,
            test_type=test.get('perf_dashboard_id', test_name),
            xvfb=True,
            chartjson_file=test.get('chartjson_file', False))
      except api.step.StepFailure as f:
        exception = f
    if exception:
      raise exception

  @staticmethod
  def compile_targets(_):
    return []


class AndroidPerfTests(Test):
  def __init__(self, perf_id, num_shards):
    self.perf_id = perf_id
    self.num_shards = num_shards

  def run(self, api, suffix):
    exception = None
    api.adb.list_devices(step_test_data=api.adb.test_api.two_devices)
    perf_tests = api.chromium.list_perf_tests(
        browser='android-chrome-shell',
        num_shards=self.num_shards,
        devices=api.adb.devices[0:1]).json.output
    try:
      api.chromium_android.run_sharded_perf_tests(
        config=api.json.input(data=perf_tests),
        perf_id=self.perf_id)
    except api.step.StepFailure as f:
      exception = f
    if exception:
      raise exception

  @staticmethod
  def compile_targets(_):
    return []


class SwarmingTest(Test):
  def __init__(self, name, dimensions=None, target_name=None):
    self._name = name
    self._tasks = {}
    self._results = {}
    self._target_name = target_name
    self._dimensions = dimensions

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def isolate_target(self):
    return self.target_name

  def create_task(self, api, suffix, isolated_hash):
    """Creates a swarming task. Must be overridden in subclasses.

    Args:
      api: Caller's API.
      suffix: Suffix added to the test name.
      isolated_hash: Hash of the isolated test to be run.

    Returns:
      A SwarmingTask object.
    """
    raise NotImplementedError()

  def pre_run(self, api, suffix):
    """Launches the test on Swarming."""
    assert suffix not in self._tasks, (
        'Test %s was already triggered' % self._step_name(suffix))

    # *.isolated may be missing if *_run target is misconfigured. It's a error
    # in gyp, not a recipe failure. So carry on with recipe execution.
    isolated_hash = api.isolate.isolated_tests.get(self.target_name)
    if not isolated_hash:
      return api.python.inline(
          '[error] %s' % self._step_name(suffix),
          r"""
          import sys
          print '*.isolated file for target %s is missing' % sys.argv[1]
          sys.exit(1)
          """,
          args=[self.target_name])

    # Create task.
    self._tasks[suffix] = self.create_task(api, suffix, isolated_hash)

    # Add custom dimensions.
    if self._dimensions:
      self._tasks[suffix].dimensions.update(self._dimensions)

    # Set default value.
    if 'os' not in self._tasks[suffix].dimensions:
      self._tasks[suffix].dimensions['os'] = api.swarming.prefered_os_dimension(
          api.platform.name)

    return api.swarming.trigger_task(self._tasks[suffix])

  def run(self, api, suffix):  # pylint: disable=R0201
    """Not used. All logic in pre_run, post_run."""
    return []

  def validate_task_results(self, api, step_result):
    """Interprets output of a task (provided as StepResult object).

    Called for successful and failed tasks.

    Args:
      api: Caller's API.
      step_result: StepResult object to examine.

    Returns:
      A tuple (valid, failures), where valid is True if valid results are
      available and failures is a list of names of failed tests (ignored if
      valid is False).
    """
    raise NotImplementedError()

  def post_run(self, api, suffix):
    """Waits for launched test to finish and collects the results."""
    assert suffix not in self._results, (
        'Results of %s were already collected' % self._step_name(suffix))

    # Emit error if test wasn't triggered. This happens if *.isolated is not
    # found. (The build is already red by this moment anyway).
    if suffix not in self._tasks:
      return api.python.inline(
          '[collect error] %s' % self._step_name(suffix),
          r"""
          import sys
          print '%s wasn\'t triggered' % sys.argv[1]
          sys.exit(1)
          """,
          args=[self.target_name])

    try:
      api.swarming.collect_task(self._tasks[suffix])
    finally:
      valid, failures = self.validate_task_results(api, api.step.active_result)
      self._results[suffix] = {'valid': valid, 'failures': failures}

  def has_valid_results(self, api, suffix):
    # Test wasn't triggered or wasn't collected.
    if suffix not in self._tasks or not suffix in self._results:
      return False
    return self._results[suffix]['valid']

  def failures(self, api, suffix):
    assert self.has_valid_results(api, suffix)
    return self._results[suffix]['failures']

  @property
  def uses_swarming(self):
    return True


class SwarmingGTestTest(SwarmingTest):
  def __init__(self, name, args=None, shards=1, dimensions=None,
               target_name=None):
    super(SwarmingGTestTest, self).__init__(name, dimensions, target_name)
    self._args = args or []
    self._shards = shards

  def compile_targets(self, api):
    # <X>_run target depends on <X>, and then isolates it invoking isolate.py.
    # It is a convention, not a hard coded rule.
    # Also include name without the _run suffix to help recipes correctly
    # interpret results returned by "analyze".
    return [self.target_name, self.target_name + '_run']

  def create_task(self, api, suffix, isolated_hash):
    # For local tests test_args are added inside api.chromium.runtest.
    args = self._args[:]
    args.extend(api.chromium.c.runtests.test_args)

    # If rerunning without a patch, run only tests that failed.
    if suffix == 'without patch':
      failed_tests = sorted(self.failures(api, 'with patch'))
      args.append('--gtest_filter=%s' % ':'.join(failed_tests))

    return api.swarming.gtest_task(
        title=self._step_name(suffix),
        isolated_hash=isolated_hash,
        shards=self._shards,
        test_launcher_summary_output=api.json.gtest_results(add_json_log=False),
        extra_args=args)

  def validate_task_results(self, api, step_result):
    gtest_results = step_result.json.gtest_results
    if not gtest_results:
      return False, None

    global_tags = gtest_results.raw.get('global_tags', [])
    if 'UNRELIABLE_RESULTS' in global_tags:
      return False, None

    return True, gtest_results.failures


class GTestTest(Test):
  def __init__(self, name, args=None, target_name=None, enable_swarming=False,
               swarming_shards=1, swarming_dimensions=None, **runtest_kwargs):
    super(GTestTest, self).__init__()
    self._name = name
    self._args = args
    self._target_name = target_name
    self._swarming_dimensions = swarming_dimensions
    if enable_swarming:
      self._test = SwarmingGTestTest(name, args, swarming_shards,
                                     swarming_dimensions, target_name)
    else:
      self._test = LocalGTestTest(name, args, target_name, **runtest_kwargs)

  @property
  def name(self):
    return self._test.name

  @property
  def isolate_target(self):
    return self._test.isolate_target

  def compile_targets(self, api):
    return self._test.compile_targets(api)

  def pre_run(self, api, suffix):
    return self._test.pre_run(api, suffix)

  def run(self, api, suffix):
    return self._test.run(api, suffix)

  def post_run(self, api, suffix):
    return self._test.post_run(api, suffix)

  def has_valid_results(self, api, suffix):
    return self._test.has_valid_results(api, suffix)

  def failures(self, api, suffix):
    return self._test.failures(api, suffix)

  @property
  def uses_swarming(self):
    return self._test.uses_swarming


class PythonBasedTest(Test):
  @staticmethod
  def compile_targets(_):
    return []

  def run_step(self, api, suffix, cmd_args, **kwargs):
    raise NotImplementedError()

  def run(self, api, suffix):
    cmd_args = ['--write-full-results-to',
                api.json.test_results(add_json_log=False)]
    if suffix == 'without patch':
      cmd_args.extend(self.failures(api, 'with patch'))

    try:
      self.run_step(
          api,
          suffix,
          cmd_args,
          step_test_data=lambda: api.json.test_api.canned_test_output(True))
    finally:
      step_result = api.step.active_result
      r = step_result.json.test_results
      p = step_result.presentation
      p.step_text += api.test_utils.format_step_text([
        ['unexpected_failures:', r.unexpected_failures.keys()],
      ])
      self._test_runs[suffix] = step_result

    return step_result

  def has_valid_results(self, api, suffix):
    # TODO(dpranke): we should just return zero/nonzero for success/fail.
    # crbug.com/357866
    step = self._test_runs[suffix]
    return (step.json.test_results.valid and
            step.retcode <= step.json.test_results.MAX_FAILURES_EXIT_STATUS and
            (step.retcode == 0) or self.failures(api, suffix))

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.test_results.unexpected_failures


class PrintPreviewTests(PythonBasedTest):  # pylint: disable=W032
  name = 'print_preview_tests'

  def run_step(self, api, suffix, cmd_args, **kwargs):
    platform_arg = '.'.join(['browser_test',
        api.platform.normalize_platform_name(api.platform.name)])
    args = cmd_args
    path = api.path['checkout'].join(
        'third_party', 'WebKit', 'Tools', 'Scripts', 'run-webkit-tests')
    args.extend(['--platform', platform_arg])

    # This is similar to how api.chromium.run_telemetry_test() sets the
    # environment variable for the sandbox.
    env = {}
    if api.platform.is_linux:
      env['CHROME_DEVEL_SANDBOX'] = api.path.join(
          '/opt', 'chromium', 'chrome_sandbox')

    return api.chromium.runtest(
        test=path,
        args=args,
        xvfb=True,
        name=self._step_name(suffix),
        python_mode=True,
        env=env,
        **kwargs)

  @staticmethod
  def compile_targets(api):
    targets = ['browser_tests', 'blink_tests']
    if api.platform.is_win:
      targets.append('crash_service')

    return targets


class TelemetryGPUTest(Test):  # pylint: disable=W0232
  def __init__(self, name, revision=None, webkit_revision=None,
               target_name=None, args=None, enable_swarming=False,
               swarming_dimensions=None, **runtest_kwargs):
    if enable_swarming:
      self._test = SwarmingTelemetryGPUTest(name, args=args,
                                            dimensions=swarming_dimensions,
                                            target_name=target_name)
    else:
      self._test = LocalTelemetryGPUTest(name, revision, webkit_revision,
                                         args=args, target_name=target_name,
                                         **runtest_kwargs)

  @property
  def name(self):
    return self._test.name

  @property
  def isolate_target(self):
    return self._test.isolate_target

  def compile_targets(self, api):
    return self._test.compile_targets(api)

  def pre_run(self, api, suffix):
    return self._test.pre_run(api, suffix)

  def run(self, api, suffix):
    return self._test.run(api, suffix)

  def post_run(self, api, suffix):
    return self._test.post_run(api, suffix)

  def has_valid_results(self, api, suffix):
    return self._test.has_valid_results(api, suffix)

  def failures(self, api, suffix):
    return self._test.failures(api, suffix)

  @property
  def uses_swarming(self):
    return self._test.uses_swarming


class LocalTelemetryGPUTest(Test):  # pylint: disable=W0232
  def __init__(self, name, revision, webkit_revision,
               target_name=None, **runtest_kwargs):
    """Constructs an instance of LocalTelemetryGPUTest.

    Args:
      name: Displayed name of the test. May be modified by suffixes.
      revision: Revision of the Chrome checkout.
      webkit_revision: Revision of the WebKit checkout.
      target_name: Actual name of the test. Defaults to name.
      runtest_kwargs: Additional keyword args forwarded to the runtest.
    """
    super(LocalTelemetryGPUTest, self).__init__()
    self._name = name
    self._target_name = target_name
    self._revision = revision
    self._webkit_revision = webkit_revision
    self._failures = {}
    self._valid = {}
    self._runtest_kwargs = runtest_kwargs

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def isolate_target(self):
    return self.target_name

  def compile_targets(self, _):
    # TODO(sergiyb): Build 'chrome_shell_apk' instead of 'chrome' on Android.
    return ['chrome', 'telemetry_gpu_test_run']

  def run(self, api, suffix):  # pylint: disable=R0201
    kwargs = self._runtest_kwargs.copy()
    kwargs['args'].extend(['--output-format', 'json',
                           '--output-dir', api.raw_io.output_dir()])
    step_test_data=lambda: api.json.test_api.canned_telemetry_gpu_output(False)
    try:
      api.isolate.run_telemetry_test(
          'telemetry_gpu_test',
          self.target_name,
          self._revision,
          self._webkit_revision,
          name=self._step_name(suffix),
          spawn_dbus=True,
          step_test_data=step_test_data,
          **self._runtest_kwargs)
    finally:
      step_result = api.step.active_result
      self._test_runs[suffix] = step_result

      try:
        res = api.json.loads(step_result.raw_io.output_dir['results.json'])
        self._failures[suffix] = [res['pages'][str(value['page_id'])]['name']
                                  for value in res['per_page_values']
                                  if value['type'] == 'failure']

        self._valid[suffix] = True
      except (ValueError, KeyError):
        self._valid[suffix] = False

      if self._valid[suffix]:
        step_result.presentation.step_text += api.test_utils.format_step_text([
          ['failures:', self._failures[suffix]]
        ])

  def has_valid_results(self, api, suffix):
    return suffix in self._valid and self._valid[suffix]

  def failures(self, api, suffix):
    assert self.has_valid_results(api, suffix)
    assert suffix in self._failures
    return self._failures[suffix]


class SwarmingTelemetryGPUTest(SwarmingTest):
  def __init__(self, name, args=None, dimensions=None, target_name=None):
    super(SwarmingTelemetryGPUTest, self).__init__(name, dimensions,
                                                   'telemetry_gpu_test')
    self._args = args
    self._telemetry_target_name = target_name or name

  def compile_targets(self, _):
    # TODO(sergiyb): Build 'chrome_shell_apk' instead of 'chrome' on Android.
    return ['chrome', 'telemetry_gpu_test_run']

  def create_task(self, api, suffix, isolated_hash):
    # For local tests args are added inside api.chromium.run_telemetry_test.
    browser_config = api.chromium.c.BUILD_CONFIG.lower()
    args = [self._telemetry_target_name, '--show-stdout',
            '--browser=%s' % browser_config] + self._args

    # If rerunning without a patch, run only tests that failed.
    if suffix == 'without patch':
      failed_tests = sorted(self.failures(api, 'with patch'))
      # Telemetry test launcher uses re.compile to parse --page-filter argument,
      # therefore we escape any special characters in test names.
      failed_tests = [re.escape(test_name) for test_name in failed_tests]
      args.append('--page-filter=%s' % '|'.join(failed_tests))

    return api.swarming.telemetry_gpu_task(
        title=self._step_name(suffix), isolated_hash=isolated_hash,
        extra_args=args)

  def validate_task_results(self, api, step_result):
    results = getattr(step_result, 'telemetry_results', None) or {}

    try:
      failures = [results['pages'][str(value['page_id'])]['name']
                  for value in results['per_page_values']
                  if value['type'] == 'failure']

      valid = True
    except (ValueError, KeyError):
      valid = False
      failures = None

    if valid:
      step_result.presentation.step_text += api.test_utils.format_step_text([
        ['failures:', failures]
      ])

    return valid, failures


class AndroidInstrumentationTest(Test):
  def __init__(self, name, compile_target, test_data=None,
               adb_install_apk=None):
    self._name = name
    self.compile_target = compile_target

    self.test_data = test_data
    self.adb_install_apk = adb_install_apk

  @property
  def name(self):
    return self._name

  def run(self, api, suffix):
    assert api.chromium.c.TARGET_PLATFORM == 'android'
    if self.adb_install_apk:
      api.chromium_android.adb_install_apk(
          self.adb_install_apk[0], self.adb_install_apk[1])
    api.chromium_android.run_instrumentation_suite(
        self.name, test_data=self.test_data,
        flakiness_dashboard='test-results.appspot.com',
        verbose=True)

  def compile_targets(self, _):
    return [self.compile_target]


class BlinkTest(Test):
  # TODO(dpranke): This should be converted to a PythonBasedTest, although it
  # will need custom behavior because we archive the results as well.

  name = 'webkit_tests'

  @staticmethod
  def compile_targets(api):
    return []

  def run(self, api, suffix):
    results_dir = api.path['slave_build'].join('layout-test-results')

    args = ['--target', api.chromium.c.BUILD_CONFIG,
            '-o', results_dir,
            '--build-dir', api.chromium.c.build_dir,
            '--json-test-results', api.json.test_results(add_json_log=False)]
    if suffix == 'without patch':
      test_list = "\n".join(self.failures(api, 'with patch'))
      args.extend(['--test-list', api.raw_io.input(test_list),
                   '--skipped', 'always'])

    if 'oilpan' in api.properties['buildername']:
      args.extend(['--additional-expectations',
                   api.path['checkout'].join('third_party', 'WebKit',
                                             'LayoutTests',
                                             'OilpanExpectations')])

    try:
      step_result = api.chromium.runtest(
          api.path['build'].join('scripts', 'slave', 'chromium',
                                 'layout_test_wrapper.py'),
          args, name=self._step_name(suffix),
          step_test_data=lambda: api.json.test_api.canned_test_output(
              passing=True, minimal=True))
    except api.step.StepFailure as f:
      step_result = f.result

    self._test_runs[suffix] = step_result

    if step_result:
      r = step_result.json.test_results
      p = step_result.presentation

      p.step_text += api.test_utils.format_step_text([
        ['unexpected_flakes:', r.unexpected_flakes.keys()],
        ['unexpected_failures:', r.unexpected_failures.keys()],
        ['Total executed: %s' % r.num_passes],
      ])

      if r.unexpected_flakes or r.unexpected_failures:
        p.status = api.step.WARNING
      else:
        p.status = api.step.SUCCESS

    if suffix == 'with patch':
      buildername = api.properties['buildername']
      buildnumber = api.properties['buildnumber']

      archive_layout_test_results = api.path['build'].join(
          'scripts', 'slave', 'chromium', 'archive_layout_test_results.py')

      archive_result = api.python(
        'archive_webkit_tests_results',
        archive_layout_test_results,
        [
          '--results-dir', results_dir,
          '--build-dir', api.chromium.c.build_dir,
          '--build-number', buildnumber,
          '--builder-name', buildername,
          '--gs-bucket', 'gs://chromium-layout-test-archives',
        ] + api.json.property_args(),
      )

      # TODO(infra): http://crbug.com/418946 .
      sanitized_buildername = re.sub('[ .()]', '_', buildername)
      base = (
        "https://storage.googleapis.com/chromium-layout-test-archives/%s/%s"
        % (sanitized_buildername, buildnumber))

      archive_result.presentation.links['layout_test_results'] = (
          base + '/layout-test-results/results.html')
      archive_result.presentation.links['(zip)'] = (
          base + '/layout-test-results.zip')

  def has_valid_results(self, api, suffix):
    step = self._test_runs[suffix]
    # TODO(dpranke): crbug.com/357866 - note that all comparing against
    # MAX_FAILURES_EXIT_STATUS tells us is that we did not exit early
    # or abnormally; it does not tell us how many failures there actually
    # were, which might be much higher (up to 5000 diffs, where we
    # would bail out early with --exit-after-n-failures) or lower
    # if we bailed out after 100 crashes w/ -exit-after-n-crashes, in
    # which case the retcode is actually 130
    return (step.json.test_results.valid and
            step.retcode <= step.json.test_results.MAX_FAILURES_EXIT_STATUS)

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.test_results.unexpected_failures


class MiniInstallerTest(PythonBasedTest):  # pylint: disable=W0232
  name = 'test_installer'

  @staticmethod
  def compile_targets(_):
    return ['mini_installer']

  def run_step(self, api, suffix, cmd_args, **kwargs):
    test_path = api.path['checkout'].join('chrome', 'test', 'mini_installer')
    args = [
      '--build-dir', api.chromium.c.build_dir,
      '--target', api.chromium.c.build_config_fs,
      '--force-clean',
      '--config', test_path.join('config', 'config.config'),
    ]
    args.extend(cmd_args)
    return api.python(
      self._step_name(suffix),
      test_path.join('test_installer.py'),
      args,
      **kwargs)


class GenerateTelemetryProfileStep(Test):
  name = 'generate_telemetry_profiles'

  def __init__(self, target, profile_type_to_create):
    super(GenerateTelemetryProfileStep, self).__init__()
    self._target = target
    self._profile_type_to_create = profile_type_to_create

  def run(self, api, suffix):
    args = ['--run-python-script',
            '--target', self._target,
            api.path['build'].join('scripts', 'slave',
                                   'generate_profile_shim.py'),
            '--target=' + self._target,
            '--profile-type-to-generate=' + self._profile_type_to_create]
    api.python('generate_telemetry_profiles',
               api.path['build'].join('scripts', 'slave','runtest.py'),
               args)

  @property
  def abort_on_failure(self):
    """If True, abort build when test fails."""
    return True

  @staticmethod
  def compile_targets(_):
    return []

IOS_TESTS = [
  GTestTest('base_unittests'),
  GTestTest('components_unittests'),
  GTestTest('crypto_unittests'),
  GTestTest('gfx_unittests'),
  GTestTest('url_unittests'),
  GTestTest('content_unittests'),
  GTestTest('net_unittests'),
  GTestTest('ui_base_unittests'),
  GTestTest('ui_ios_unittests'),
  GTestTest('sync_unit_tests'),
  GTestTest('sql_unittests'),
]
