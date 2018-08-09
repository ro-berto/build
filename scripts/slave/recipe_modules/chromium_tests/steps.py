# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import datetime
import hashlib
import json
import re
import string
import struct
import textwrap
import traceback

from recipe_engine.types import freeze


RESULTS_URL = 'https://chromeperf.appspot.com'
MAX_FAILS = 30


class TestOptions(object):
  """Abstracts command line flags to be passed to the test."""
  def __init__(self, repeat_count=None, test_filter=None, run_disabled=False,
               retry_limit=None):
    """Construct a TestOptions object with immutable attributes.

    Args:
      repeat_count - how many times to run each test
      test_filter - a list of tests, e.g.
                       ['suite11.test1',
                        'suite12.test2']
      run_disabled - whether to run tests that have been disabled.
      retry_limit - how many times to retry a test until getting a pass.
     """
    self._test_filter = freeze(test_filter)
    self._repeat_count = repeat_count
    self._run_disabled = run_disabled
    self._retry_limit = retry_limit

  @property
  def repeat_count(self):
    return self._repeat_count

  @property
  def run_disabled(self):
    return self._run_disabled

  @property
  def retry_limit(self):
    return self._retry_limit

  @property
  def test_filter(self):
    return self._test_filter


def _merge_arg(args, flag, value):
  args = [a for a in args if not a.startswith(flag)]
  if value is not None:
    return args + ['%s=%s' % (flag, str(value))]
  else:
    return args + [flag]


def _merge_args_and_test_options(test, args):
  args = args[:]

  if not (isinstance(test, (SwarmingGTestTest, LocalGTestTest)) or (isinstance(
              test, (SwarmingIsolatedScriptTest, LocalIsolatedScriptTest)) and
              'webkit_layout_tests' in test.target_name)):
    # The args that are being merged by this function are only supported
    # by gtest and webkit_layout_tests.
    return args

  options = test.test_options
  if options.test_filter:
    args = _merge_arg(args, '--gtest_filter', ':'.join(options.test_filter))
  if options.repeat_count and options.repeat_count > 1:
    args = _merge_arg(args, '--gtest_repeat', options.repeat_count)
  if options.retry_limit is not None:
    args = _merge_arg(args, '--test-launcher-retry-limit', options.retry_limit)
  if options.run_disabled:
    args = _merge_arg(args, '--gtest_also_run_disabled_tests', value=None)
  return args


def _merge_failures_for_retry(args, step, api, suffix):
    if suffix == 'without patch':
      # This will override any existing --gtest_filter specification; this
      # is okay because the failures are a subset of the initial specified
      # tests. When a patch is adding a new test (and it fails), the test
      # runner is required to just ignore the unknown test.
      failures = step.failures(api, 'with patch')
      if failures:
        return _merge_arg(args, '--gtest_filter', ':'.join(failures))
    return args


class Test(object):
  """
  Base class for tests that can be retried after deapplying a previously
  applied patch.
  """

  def __init__(self, waterfall_mastername=None, waterfall_buildername=None):
    """
    Args:
      waterfall_mastername (str): Matching waterfall buildbot master name.
        This value would be different from trybot master name.
      waterfall_buildername (str): Matching waterfall buildbot builder name.
        This value would be different from trybot builder name.
    """
    super(Test, self).__init__()
    self._test_runs = {}
    self._waterfall_mastername = waterfall_mastername
    self._waterfall_buildername = waterfall_buildername
    self._test_options = None

  @property
  def set_up(self):
    return None

  @property
  def tear_down(self):
    return None

  @property
  def test_options(self):
    return self._test_options or TestOptions()

  @test_options.setter
  def test_options(self, value):  # pragma: no cover
    raise NotImplementedError(
        'This test %s does not support test options objects yet' % type(self))

  @property
  def abort_on_failure(self):
    """If True, abort build when test fails."""
    return False

  @property
  def name(self):  # pragma: no cover
    """Name of the test."""
    raise NotImplementedError()

  @property
  def canonical_name(self):
    """Canonical name of the test, no suffix attached."""
    return self.name

  def isolate_target(self, _api):
    """Returns isolate target name. Defaults to name.

    The _api is here in case classes want to use api information to alter the
    isolation target.
    """
    return self.name  # pragma: no cover

  def compile_targets(self, api):
    """List of compile targets needed by this test."""
    raise NotImplementedError()  # pragma: no cover

  def pre_run(self, api, suffix):  # pragma: no cover
    """Steps to execute before running the test."""
    return []

  def run(self, api, suffix):  # pragma: no cover
    """Run the test. suffix is 'with patch' or 'without patch'."""
    raise NotImplementedError()

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
  def uses_isolate(self):
    """Returns true if the test is run via an isolate."""
    return False

  @property
  def uses_local_devices(self):
    return False # pragma: no cover

  def _step_name(self, suffix):
    """Helper to uniformly combine tests's name with a suffix."""
    if not suffix:
      return self.name
    return '%s (%s)' % (self.name, suffix)

  def step_metadata(self, api, suffix=None):
    data = {
        'waterfall_mastername': self._waterfall_mastername,
        'waterfall_buildername': self._waterfall_buildername,
        'canonical_step_name': self.canonical_name,
        'isolate_target_name': self.isolate_target(api),
    }
    if suffix is not None:
      data['patched'] = (suffix == 'with patch')
    return data


class TestWrapper(Test):  # pragma: no cover
  """ A base class for Tests that wrap other Tests.

  By default, all functionality defers to the wrapped Test.
  """

  def __init__(self, test):
    super(TestWrapper, self).__init__()
    self._test = test

  @property
  def set_up(self):
    return self._test.set_up

  @property
  def tear_down(self):
    return self._test.tear_down

  @property
  def test_options(self):
    return self._test.test_options

  @test_options.setter
  def test_options(self, value):
    self._test.test_options = value

  @property
  def abort_on_failure(self):
    return self._test.abort_on_failure

  @property
  def name(self):
    return self._test.name

  def isolate_target(self, api):
    return self._test.isolate_target(api)

  def compile_targets(self, api):
    return self._test.compile_targets(api)

  def pre_run(self, api, suffix):
    return self._test.pre_run(api, suffix)

  def run(self, api, suffix):
    return self._test.run(api, suffix)

  def has_valid_results(self, api, suffix):
    return self._test.has_valid_results(api, suffix)

  def failures(self, api, suffix):
    return self._test.failures(api, suffix)

  @property
  def uses_isolate(self):
    return self._test.uses_isolate

  @property
  def uses_local_devices(self):
    return self._test.uses_local_devices

  def step_metadata(self, api, suffix=None):
    return self._test.step_metadata(api, suffix=suffix)


class ExperimentalTest(TestWrapper):
  """A test wrapper that runs the wrapped test on an experimental test.

  Experimental tests:
    - can run at <= 100%, depending on the experiment_percentage.
    - will not cause the build to fail.
  """

  def __init__(self, test, experiment_percentage):
    super(ExperimentalTest, self).__init__(test)
    self._experiment_percentage = max(0, min(100, int(experiment_percentage)))

  def _experimental_suffix(self, suffix):
    if not suffix:
      return 'experimental'
    return '%s, experimental' % (suffix)

  def _is_in_experiment(self, api):
    # Arbitrarily determine whether to run the test based on its experiment
    # key. Tests with the same experiment key should always either be in the
    # experiment or not; i.e., given the same key, this should always either
    # return True or False, but not both.
    #
    # The experiment key is either:
    #   - builder name + patchset + name of the test, for trybots
    #   - builder name + build number + name of the test, for CI bots
    #
    # These keys:
    #   - ensure that the same experiment configuration is always used for
    #     a given patchset
    #   - allow independent variation of experiments on the same test
    #     across different builders
    #   - allow independent variation of experiments on different tests
    #     across a single build
    #
    # The overall algorithm is copied from the CQ's implementation of
    # experimental builders, albeit with different experiment keys.

    criteria = [
      api.properties.get('buildername', ''),
      api.properties.get('patch_issue') or api.properties.get('buildnumber') or '0',
      self.name,
    ]

    digest = hashlib.sha1(''.join(str(c) for c in criteria)).digest()
    short = struct.unpack_from('<H', digest)[0]
    return self._experiment_percentage * 0xffff >= short * 100

  @property
  def abort_on_failure(self):
    return False

  #override
  def pre_run(self, api, suffix):
    if not self._is_in_experiment(api):
      return []

    try:
      return super(ExperimentalTest, self).pre_run(
          api, self._experimental_suffix(suffix))
    except api.step.StepFailure:
      pass

  #override
  def run(self, api, suffix):
    if not self._is_in_experiment(api):
      return []

    try:
      return super(ExperimentalTest, self).run(
          api, self._experimental_suffix(suffix))
    except api.step.StepFailure:
      pass

  #override
  def has_valid_results(self, api, suffix):
    if self._is_in_experiment(api):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).has_valid_results(
          api, self._experimental_suffix(suffix))
    return True

  #override
  def failures(self, api, suffix):
    if (self._is_in_experiment(api)
        # Only call into the implementation if we have valid results to avoid
        # violating wrapped class implementations' preconditions.
        and super(ExperimentalTest, self).has_valid_results(
            api, self._experimental_suffix(suffix))):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).failures(
          api, self._experimental_suffix(suffix))
    return []


class ArchiveBuildStep(Test):
  def __init__(self, gs_bucket, gs_acl=None):
    self.gs_bucket = gs_bucket
    self.gs_acl = gs_acl

  def run(self, api, suffix):
    bucket = self.gs_bucket
    if api.chromium.m.runtime.is_experimental:
      bucket += "/experimental"
    return api.chromium.archive_build(
        'archive build',
        bucket,
        gs_acl=self.gs_acl,
    )

  def compile_targets(self, _):
    return []


class SizesStep(Test):
  def __init__(self, results_url, perf_id):
    self.results_url = results_url
    self.perf_id = perf_id

  def run(self, api, suffix):
    return api.chromium.sizes(self.results_url, self.perf_id)

  def compile_targets(self, _):
    return ['chrome']

  @property
  def name(self):
    return 'sizes'  # pragma: no cover

  def has_valid_results(self, api, suffix):
    # TODO(sebmarchand): implement this function as well as the
    # |failures| one.
    return True

  def failures(self, api, suffix):
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

  def __init__(self, name, script, all_compile_targets, script_args=None,
               override_compile_targets=None,
               waterfall_mastername=None, waterfall_buildername=None):
    super(ScriptTest, self).__init__(
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._name = name
    self._script = script
    self._all_compile_targets = all_compile_targets
    self._script_args = script_args
    self._override_compile_targets = override_compile_targets

  @property
  def name(self):
    return self._name

  def compile_targets(self, api):
    if self._override_compile_targets:
      return self._override_compile_targets

    try:
      substitutions = {'name': self._name}

      return [string.Template(s).safe_substitute(substitutions)
              for s in self._all_compile_targets[self._script]]
    except KeyError:  # pragma: no cover
      # There are internal recipes that appear to configure
      # test script steps, but ones that don't have data.
      # We get around this by returning a default value for that case.
      # But the recipes should be updated to not do this.
      # We mark this as pragma: no cover since the public recipes
      # will not exercise this block.
      #
      # TODO(phajdan.jr): Revisit this when all script tests
      # lists move src-side. We should be able to provide
      # test data then.
      if api.chromium._test_data.enabled:
        return []

      raise

  def run(self, api, suffix):
    name = self.name
    if suffix:
      name += ' (%s)' % suffix  # pragma: no cover

    run_args = []
    if suffix == 'without patch':
      run_args.extend([
          '--filter-file', api.json.input(self.failures(api, 'with patch'))
      ])  # pragma: no cover

    try:
      script_args = []
      if self._script_args:
        script_args = ['--args', api.json.input(self._script_args)]
      api.python(
          name,
          # Enforce that all scripts are in the specified directory
          # for consistency.
          api.path['checkout'].join(
              'testing', 'scripts', api.path.basename(self._script)),
          args=(api.chromium_tests.get_common_args_for_scripts() +
                script_args +
                ['run', '--output', api.json.output()] +
                run_args),
          step_test_data=lambda: api.json.test_api.output(
              {'valid': True, 'failures': []}))
    finally:
      self._test_runs[suffix] = api.step.active_result
      if self.has_valid_results(api, suffix):
        _, failures = api.test_utils.limit_failures(
            self.failures(api, suffix), MAX_FAILS)
        self._test_runs[suffix].presentation.step_text += (
            api.test_utils.format_step_text([
              ['failures:', failures]
            ]))

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    try:
      # Make sure the JSON includes all necessary data.
      self.failures(api, suffix)

      return self._test_runs[suffix].json.output['valid']
    except Exception as e:  # pragma: no cover
      if suffix in self._test_runs:
        self._test_runs[suffix].presentation.logs['no_results_exc'] = [
          str(e), '\n', api.traceback.format_exc()]
      return False

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.output['failures']


class LocalGTestTest(Test):
  def __init__(self, name, args=None, target_name=None, revision=None,
               webkit_revision=None, android_shard_timeout=None,
               android_tool=None, override_compile_targets=None,
               override_isolate_target=None,
               commit_position_property='got_revision_cp', use_xvfb=True,
               waterfall_mastername=None, waterfall_buildername=None,
               set_up=None, tear_down=None, **runtest_kwargs):
    """Constructs an instance of LocalGTestTest.

    Args:
      name: Displayed name of the test. May be modified by suffixes.
      args: Arguments to be passed to the test.
      target_name: Actual name of the test. Defaults to name.
      revision: Revision of the Chrome checkout.
      webkit_revision: Revision of the WebKit checkout.
      override_compile_targets: List of compile targets for this test
          (for tests that don't follow target naming conventions).
      override_isolate_target: List of isolate targets for this test
          (for tests that don't follow target naming conventions).
      commit_position_property: Property to get Chromium's commit position.
          Defaults to 'got_revision_cp'.
      use_xvfb: whether to use the X virtual frame buffer. Only has an
          effect on Linux. Defaults to True. Mostly harmless to
          specify this, except on GPU bots.
      set_up: Optional setup scripts.
      tear_down: Optional teardown script.
      runtest_kwargs: Additional keyword args forwarded to the runtest.

    """
    super(LocalGTestTest, self).__init__(
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._name = name
    self._args = args or []
    self._target_name = target_name
    self._revision = revision
    self._webkit_revision = webkit_revision
    self._android_shard_timeout = android_shard_timeout
    self._android_tool = android_tool
    self._override_compile_targets = override_compile_targets
    self._override_isolate_target = override_isolate_target
    self._commit_position_property = commit_position_property
    self._use_xvfb = use_xvfb
    self._runtest_kwargs = runtest_kwargs
    self._gtest_results = {}
    self._set_up = set_up
    self._tear_down = tear_down

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  @property
  def set_up(self):
    return self._set_up

  @property
  def tear_down(self):
    return self._tear_down

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def uses_local_devices(self):
    return True  # pragma: no cover

  def isolate_target(self, _api):  # pragma: no cover
    if self._override_isolate_target:
      return self._override_isolate_target
    return self.target_name

  def compile_targets(self, api):
    # TODO(phajdan.jr): clean up override_compile_targets (remove or cover).
    if self._override_compile_targets:  # pragma: no cover
      return self._override_compile_targets
    return [self.target_name]

  def run(self, api, suffix):
    is_android = api.chromium.c.TARGET_PLATFORM == 'android'
    is_fuchsia = api.chromium.c.TARGET_PLATFORM == 'fuchsia'

    args = _merge_args_and_test_options(self, self._args)
    args = _merge_failures_for_retry(args, self, api, suffix)

    gtest_results_file = api.test_utils.gtest_results(add_json_log=False)
    step_test_data = lambda: api.test_utils.test_api.canned_gtest_output(True)

    kwargs = {
      'name': self._step_name(suffix),
      'args': args,
      'step_test_data': step_test_data,
    }

    if is_android:
      kwargs['json_results_file'] = gtest_results_file
      kwargs['shard_timeout'] = self._android_shard_timeout
      kwargs['tool'] = self._android_tool
    else:
      kwargs['xvfb'] = self._use_xvfb
      kwargs['test_type'] = self.name
      kwargs['annotate'] = 'gtest'
      kwargs['test_launcher_summary_output'] = gtest_results_file
      kwargs.update(self._runtest_kwargs)

    try:
      if is_android:
        api.chromium_android.run_test_suite(self.target_name, **kwargs)
      elif is_fuchsia:
        script = api.chromium.output_dir.join('bin',
                                              'run_%s' % self.target_name)
        api.python(
            self.target_name, script,
            args + ['--test_launcher_summary_output', gtest_results_file])
      else:
        api.chromium.runtest(self.target_name, revision=self._revision,
                             webkit_revision=self._webkit_revision, **kwargs)
      # TODO(kbr): add functionality to generate_gtest to be able to
      # force running these local gtests via isolate from the src-side
      # JSON files. crbug.com/584469
    finally:
      step_result = api.step.active_result
      self._test_runs[suffix] = step_result

      r = api.test_utils.present_gtest_failures(step_result)
      if r:
        self._gtest_results[suffix] = r

        api.test_results.upload(
            api.json.input(r.raw),
            test_type=self.name,
            chrome_revision=api.bot_update.last_returned_properties.get(
                self._commit_position_property, 'x@{#0}'))

    return step_result

  def pass_fail_counts(self, suffix):
    if self._gtest_results.get(suffix):
      # test_result exists and is not None.
      return self._gtest_results[suffix].pass_fail_counts
    return {}

  def has_valid_results(self, api, suffix):
    if suffix not in self._test_runs:
      return False  # pragma: no cover
    if not hasattr(self._test_runs[suffix], 'test_utils'):
      return False  # pragma: no cover
    gtest_results = self._test_runs[suffix].test_utils.gtest_results
    if not gtest_results.valid:  # pragma: no cover
      return False
    global_tags = gtest_results.raw.get('global_tags', [])
    return 'UNRELIABLE_RESULTS' not in global_tags

  def failures(self, api, suffix):
    return self._test_runs[suffix].test_utils.gtest_results.failures


def get_args_for_test(api, chromium_tests_api, test_spec, bot_update_step):
  """Gets the argument list for a dynamically generated test, as
  provided by the JSON files in src/testing/buildbot/ in the Chromium
  workspace. This function provides the following build properties in
  the form of variable substitutions in the tests' argument lists:

      buildbucket_build_id
      buildername
      buildnumber
      got_revision
      mastername
      patch_issue
      patch_set

  so, for example, a test can declare the argument:

      --test-machine-name=\"${buildername}\"

  and ${buildername} will be replaced with the associated build
  property. In this example, it will also be double-quoted, to handle
  the case where the machine name contains contains spaces.

  This function also supports trybot-only and waterfall-only
  arguments, so that a test can pass a different argument lists on the
  continuous builders compared to tryjobs. This is useful when the
  waterfall bots generate some reference data that is tested against
  during tryjobs.
  """

  args = test_spec.get('args', [])
  extra_args = None
  if chromium_tests_api.is_precommit_mode():
    extra_args = test_spec.get('precommit_args', [])
  else:
    extra_args = test_spec.get('non_precommit_args', [])
  # Only add the extra args if there were any to prevent cases of mixed
  # tuple/list concatenation caused by assuming type
  if extra_args:
    args = args + extra_args

  # Perform substitution of known variables.
  substitutions = {
      'buildbucket_build_id': chromium_tests_api.m.buildbucket.build_id,
      'buildername': api.properties.get('buildername'),
      'buildnumber': api.properties.get('buildnumber'),
      'got_revision': (
          bot_update_step.presentation.properties.get('got_revision',
          bot_update_step.presentation.properties.get('got_src_revision'))),
      'mastername': api.properties.get('mastername'),
      'patch_issue': api.properties.get('patch_issue'),
      'patch_set': api.properties.get('patch_set'),
  }
  return [string.Template(arg).safe_substitute(substitutions) for arg in args]


def generator_common(api, spec, swarming_delegate, local_delegate, swarming_dimensions):
  """Common logic for generating tests from JSON specs.

  Args:
    spec: the configuration of the test(s) that should be generated.
    swarming_delegate: function to call to create a swarming test.
    local_delgate: function to call to create a local test.

  Yields:
    instances of Test.
  """

  tests = []
  kwargs = {}

  target_name = str(spec.get('test') or spec.get('isolate_name'))
  name = str(spec.get('name', target_name))

  kwargs['target_name'] = target_name
  kwargs['name'] = name

  set_up = list(spec.get('setup', []))
  processed_set_up = []
  for set_up_step in set_up:
    set_up_step_script = set_up_step.get('script')
    if set_up_step_script:
      if set_up_step_script.startswith('//'):
        set_up_step_new = dict(set_up_step)
        set_up_step_new['script'] = api.path['checkout'].join(
            set_up_step_script[2:].replace('/', api.path.sep))
        processed_set_up.append(set_up_step_new)
      else:
        api.python.failing_step(
          'test spec format error',
          textwrap.wrap(textwrap.dedent("""\
              The test target "%s" contains a custom set up script "%s"
              that doesn't match the expected format. Custom set up script entries
              should be a path relative to the top-level chromium src directory and
              should start with "//".
              """ % (name, set_up_step_script))),
          as_log='details')
  kwargs['set_up'] = processed_set_up

  tear_down = list(spec.get('teardown', []))
  processed_tear_down = []
  for tear_down_step in tear_down:
    tear_down_step_script = tear_down_step.get('script')
    if tear_down_step_script:
      if tear_down_step_script.startswith('//'):
        tear_down_step_new = dict(tear_down_step)
        tear_down_step_new['script'] = api.path['checkout'].join(
            tear_down_step_script[2:].replace('/', api.path.sep))
        processed_tear_down.append(tear_down_step_new)
      else:
        api.python.failing_step(
          'test spec format error',
          textwrap.wrap(textwrap.dedent("""\
              The test target "%s" contains a custom tear down script "%s"
              that doesn't match the expected format. Custom tear down script entries
              should be a path relative to the top-level chromium src directory and
              should start with "//".
              """ % (name, tear_down_step_script))),
          as_log='details')
  kwargs['tear_down'] = processed_tear_down

  swarming_spec = spec.get('swarming', {})
  if swarming_spec.get('can_use_on_swarming_builders'):
    swarming_dimension_sets = swarming_spec.get('dimension_sets')
    kwargs['expiration'] = swarming_spec.get('expiration')
    kwargs['hard_timeout'] = swarming_spec.get('hard_timeout')
    kwargs['io_timeout'] = swarming_spec.get('io_timeout')
    kwargs['priority'] = swarming_spec.get('priority_adjustment')
    kwargs['shards'] = swarming_spec.get('shards', 1)
    kwargs['upload_test_results'] = swarming_spec.get(
        'upload_test_results', True)

    packages = swarming_spec.get('cipd_packages')
    if packages:
      kwargs['cipd_packages'] = [
          (p['location'], p['cipd_package'], p['revision'])
          for p in packages
      ]

    merge = dict(spec.get('merge', {}))
    if merge:
      merge_script = merge.get('script')
      if merge_script:
        if merge_script.startswith('//'):
          merge['script'] = api.path['checkout'].join(
              merge_script[2:].replace('/', api.path.sep))
        else:
          api.python.failing_step(
              'test spec format error',
              textwrap.wrap(textwrap.dedent("""\
                  The test target "%s" contains a custom merge_script "%s"
                  that doesn't match the expected format. Custom merge_script entries
                  should be a path relative to the top-level chromium src directory and
                  should start with "//".
                  """ % (name, merge_script))),
              as_log='details')
    kwargs['merge'] = merge

    trigger_script = dict(spec.get('trigger_script', {}))
    if trigger_script:
      trigger_script_path = trigger_script.get('script')
      if trigger_script_path:
        if trigger_script_path.startswith('//'):
          trigger_script['script'] = api.path['checkout'].join(
              trigger_script_path[2:].replace('/', api.path.sep))
        else:
          api.python.failing_step(
              'test spec format error',
              textwrap.wrap(textwrap.dedent("""\
                  The test target "%s" contains a custom trigger_script "%s"
                  that doesn't match the expected format. Custom trigger_script entries
                  should be a path relative to the top-level chromium src directory and
                  should start with "//".
                  """ % (name, trigger_script_path))),
              as_log='details')
    kwargs['trigger_script'] = trigger_script

    swarming_dimensions = swarming_dimensions or {}
    for dimensions in swarming_dimension_sets or [{}]:
      # Yield potentially multiple invocations of the same test, on
      # different machine configurations.
      new_dimensions = dict(swarming_dimensions)
      new_dimensions.update(dimensions)
      kwargs['dimensions'] = new_dimensions

      tests.append(swarming_delegate(spec, **kwargs))

  else:
    tests.append(local_delegate(spec, **kwargs))

  experiment_percentage = spec.get('experiment_percentage')
  for t in tests:
    if experiment_percentage is not None:
      yield ExperimentalTest(t, experiment_percentage)
    else:
      yield t


def generate_gtest(api, chromium_tests_api, mastername, buildername, test_spec,
                   bot_update_step,
                   swarming_dimensions=None, scripts_compile_targets=None,
                   bot_config=None):
  def canonicalize_test(test):
    if isinstance(test, basestring):
      canonical_test = {'test': test}
    else:
      canonical_test = dict(test)

    canonical_test.setdefault('shard_index', 0)
    canonical_test.setdefault('total_shards', 1)
    return canonical_test

  def get_tests(api):
    tests = [canonicalize_test(t) for t in
             test_spec.get(buildername, {}).get('gtest_tests', [])]

    # Sort the test by the number of shards.
    # TODO(tikuta): Remove this when crbug.com/828937 is fixed.
    tests.sort(key=lambda x: x.get('swarming',{}).get('shards', 1))
    return tests

  def gtest_delegate_common(spec, name=None, **kwargs):
    common_gtest_kwargs = {}
    args = spec.get('args', [])
    if spec['shard_index'] != 0 or spec['total_shards'] != 1:
      args.extend(['--test-launcher-shard-index=%d' % spec['shard_index'],
                   '--test-launcher-total-shards=%d' % spec['total_shards']])
    common_gtest_kwargs['args'] = args

    common_gtest_kwargs['override_compile_targets'] = spec.get(
        'override_compile_targets', None)
    common_gtest_kwargs['override_isolate_target'] = spec.get(
        'override_isolate_target', None)

    common_gtest_kwargs['waterfall_mastername'] = mastername
    common_gtest_kwargs['waterfall_buildername'] = buildername

    return common_gtest_kwargs

  def gtest_swarming_delegate(spec, **kwargs):
    kwargs.update(gtest_delegate_common(spec, **kwargs))
    return SwarmingGTestTest(**kwargs)

  def gtest_local_delegate(spec, **kwargs):
    kwargs.update(gtest_delegate_common(spec, **kwargs))
    kwargs['use_xvfb'] = spec.get('use_xvfb', True)
    return LocalGTestTest(**kwargs)

  for spec in get_tests(api):
    for t in generator_common(
        api, spec, gtest_swarming_delegate, gtest_local_delegate,
        swarming_dimensions):
      yield t


def generate_instrumentation_test(api, chromium_tests_api, mastername,
                                  buildername, test_spec, bot_update_step,
                                  swarming_dimensions=None,
                                  scripts_compile_targets=None,
                                  bot_config=None):
  # Do not try to add swarming support here.
  # Instead, swarmed instrumentation tests should be specified as gtests.
  # (Yes, it's a little weird.)
  def instrumentation_swarming_delegate(spec, **kwargs):
    api.python.failing_step(
        'instrumentation test swarming error',
        'The tests can only be run locally.')

  def instrumentation_local_delegate(spec, **kwargs):
    kwargs['result_details'] = True
    kwargs['store_tombstones'] = True
    kwargs['trace_output'] = spec.get('trace_output', False)
    kwargs['timeout_scale'] = spec.get('timeout_scale')
    kwargs['args'] = get_args_for_test(
        api, chromium_tests_api, spec, bot_update_step)
    return AndroidInstrumentationTest(**kwargs)

  for spec in test_spec.get(buildername, {}).get('instrumentation_tests', []):
    for t in generator_common(
        api, spec, instrumentation_swarming_delegate,
        instrumentation_local_delegate, None):
      yield t


def generate_junit_test(api, chromium_tests_api, mastername, buildername,
                        test_spec, bot_update_step,
                        swarming_dimensions=None,
                        scripts_compile_targets=None,
                        bot_config=None):
  for test in test_spec.get(buildername, {}).get('junit_tests', []):
    yield AndroidJunitTest(
        str(test['test']),
        waterfall_mastername=mastername, waterfall_buildername=buildername)


def generate_cts_test(api, chromium_tests_api, mastername, buildername,
                      test_spec, bot_update_step,
                      swarming_dimensions=None,
                      scripts_compile_targets=None,
                      bot_config=None):
  for test in test_spec.get(buildername, {}).get('cts_tests', []):
    yield WebViewCTSTest(
        platform=str(test['platform']),
        command_line_args=test.get('command_line_args'),
        arch=test.get('arch', 'arm64'),
        waterfall_mastername=mastername, waterfall_buildername=buildername)


def generate_script(api, chromium_tests_api, mastername, buildername, test_spec,
                    bot_update_step,
                    swarming_dimensions=None, scripts_compile_targets=None,
                    bot_config=None):
  for script_spec in test_spec.get(buildername, {}).get('scripts', []):
    yield ScriptTest(
        str(script_spec['name']),
        script_spec['script'],
        scripts_compile_targets,
        script_spec.get('args', []),
        script_spec.get('override_compile_targets', []),
        waterfall_mastername=mastername, waterfall_buildername=buildername)


class ResultsHandler(object):
  def upload_results(self, api, results, step_name, step_suffix=None):  # pragma: no cover
    """Uploads test results to the Test Results Server.

    Args:
      api: Recipe API object.
      results: Results returned by the step.
      step_name: Name of the step that produced results.
      step_suffix: Suffix appended to the step name.
    """
    raise NotImplementedError()

  def render_results(self, api, results, presentation): # pragma: no cover
    """Renders the test result into the step's output presentation.

    Args:
      api: Recipe API object.
      results: Results returned by the step.
      presentation: Presentation output of the step.
    """
    raise NotImplementedError()

  def validate_results(self, api, results):  # pragma: no cover
    """Validates test results and returns a list of failures.

    Args:
      api: Recipe API object.
      results: Results returned by the step.

    Returns:
      (valid, failures), where valid is True when results are valid, and
      failures is a list of strings (typically names of failed tests).
    """
    raise NotImplementedError()


class JSONResultsHandler(ResultsHandler):
  MAX_FAILS = 30

  def __init__(self, ignore_task_failure=False):
    self._ignore_task_failure = ignore_task_failure

  @classmethod
  def _format_failures(cls, state, failures):
    failures.sort()
    num_failures = len(failures)
    if num_failures > cls.MAX_FAILS:
      failures = failures[:cls.MAX_FAILS]
      failures.append('... %d more (%d total) ...' % (
          num_failures - cls.MAX_FAILS, num_failures))
    return ('%s:' % state, ['* %s' % f for f in failures])

  # TODO(tansell): Make this better formatted when milo supports html rendering.
  @classmethod
  def _format_counts(cls, state, expected, unexpected, highlight=False):
    hi_left = ''
    hi_right = ''
    if highlight and unexpected > 0:
      hi_left = '>>>'
      hi_right = '<<<'
    return (
        "* %(state)s: %(total)d (%(expected)d expected, "
        "%(hi_left)s%(unexpected)d unexpected%(hi_right)s)") % dict(
            state=state, total=expected+unexpected,
            expected=expected, unexpected=unexpected,
            hi_left=hi_left, hi_right=hi_right)

  def upload_results(self, api, results, step_name, step_suffix=None):
    if hasattr(results, 'as_jsonish'):
      results = results.as_jsonish()

    # Only version 3 of results is supported by the upload server.
    if not results or results.get('version', None) != 3:
      return

    chrome_revision_cp = api.bot_update.last_returned_properties.get(
        'got_revision_cp', 'x@{#0}')
    chrome_revision = str(api.commit_position.parse_revision(
        chrome_revision_cp))
    api.test_results.upload(
      api.json.input(results), chrome_revision=chrome_revision,
      test_type=step_name)

  def render_results(self, api, results, presentation):
    failure_status = (
        api.step.WARNING if self._ignore_task_failure else api.step.FAILURE)
    try:
      results = api.test_utils.create_results_from_json_if_needed(
          results)
    except Exception as e:
      presentation.status = api.step.EXCEPTION
      presentation.step_text += api.test_utils.format_step_text([
          ("Exception while processing test results: %s" % str(e),),
      ])
      presentation.logs['no_results_exc'] = [
          str(e), '\n', api.traceback.format_exc()]
      return

    if not results.valid:
      # TODO(tansell): Change this to api.step.EXCEPTION after discussion.
      presentation.status = failure_status
      presentation.step_text = api.test_utils.INVALID_RESULTS_MAGIC
      return

    step_text = []

    if results.total_test_runs == 0:
      step_text += [
          ('Total tests: n/a',),
      ]

    # TODO(tansell): https://crbug.com/704066 - Kill simplified JSON format.
    elif results.version == 'simplified':
      if results.unexpected_failures:
        presentation.status = failure_status

      step_text += [
          ('%s passed, %s failed (%s total)' % (
              len(results.passes.keys()),
              len(results.unexpected_failures.keys()),
              len(results.tests)),),
      ]

    else:
      if results.unexpected_flakes:
        presentation.status = api.step.WARNING
      if results.unexpected_failures or results.unexpected_skipped:
        presentation.status = (
            api.step.WARNING if self._ignore_task_failure else api.step.FAILURE)

      step_text += [
          ('Total tests: %s' % len(results.tests), [
              self._format_counts(
                  'Passed',
                  len(results.passes.keys()),
                  len(results.unexpected_passes.keys())),
              self._format_counts(
                  'Skipped',
                  len(results.skipped.keys()),
                  len(results.unexpected_skipped.keys())),
              self._format_counts(
                  'Failed',
                  len(results.failures.keys()),
                  len(results.unexpected_failures.keys()),
                  highlight=True),
              self._format_counts(
                  'Flaky',
                  len(results.flakes.keys()),
                  len(results.unexpected_flakes.keys()),
                  highlight=True),
              ]
          ),
      ]

    # format_step_text will automatically trim these if the list is empty.
    step_text += [
        self._format_failures(
            'Unexpected Failures', results.unexpected_failures.keys()),
    ]
    step_text += [
        self._format_failures(
            'Unexpected Flakes', results.unexpected_flakes.keys()),
    ]
    step_text += [
        self._format_failures(
            'Unexpected Skips', results.unexpected_skipped.keys()),
    ]

    # Unknown test results mean something has probably gone wrong, mark as an
    # exception.
    if results.unknown:
      presentation.status = api.step.EXCEPTION
    step_text += [
        self._format_failures(
            'Unknown test result', results.unknown.keys()),
    ]

    presentation.step_text += api.test_utils.format_step_text(step_text)

  def validate_results(self, api, results):
    try:
      results = api.test_utils.create_results_from_json_if_needed(
          results)
    except Exception as e:
      return False, [str(e), '\n', api.traceback.format_exc()]
    # If results were interrupted, we can't trust they have all the tests in
    # them. For this reason we mark them as invalid.
    return (results.valid and not results.interrupted,
            results.unexpected_failures)


class FakeCustomResultsHandler(ResultsHandler):
  """Result handler just used for testing."""

  def validate_results(self, api, results):
    return True, []

  def render_results(self, api, results, presentation):
    presentation.step_text += api.test_utils.format_step_text([
        ['Fake results data',[]],
    ])
    presentation.links['uploaded'] = 'fake://'

  def upload_results(self, api, results, step_name, step_suffix=None):
    test_results = api.test_utils.create_results_from_json(results)


class LayoutTestResultsHandler(JSONResultsHandler):
  """Uploads layout test results to Google storage."""

  # Step name suffixes that we will archive results for.
  archive_results_suffixes = (
      None,
      '',
      'with patch',
      'experimental',
  )

  def upload_results(self, api, results, step_name, step_suffix=None):
    # Don't archive the results unless the step_suffix matches
    if step_suffix not in self.archive_results_suffixes:
        return

    # Also upload to standard JSON results handler
    JSONResultsHandler.upload_results(
        self, api, results, step_name, step_suffix)

    # LayoutTest's special archive and upload results
    results_dir = api.path['start_dir'].join('layout-test-results')

    buildername = api.properties['buildername']
    buildnumber = api.properties['buildnumber']

    archive_layout_test_results = api.chromium.package_repo_resource(
        'scripts', 'slave', 'chromium', 'archive_layout_test_results.py')

    archive_layout_test_args = [
      '--results-dir', results_dir,
      '--build-dir', api.chromium.c.build_dir,
      '--build-number', buildnumber,
      '--builder-name', buildername,
      '--gs-bucket', 'gs://chromium-layout-test-archives',
      '--staging-dir', api.path['cache'].join('chrome_staging'),
    ]
    if not api.tryserver.is_tryserver:
      archive_layout_test_args.append('--store-latest')

    # TODO: The naming of the archive step is clunky, but the step should
    # really be triggered src-side as part of the post-collect merge and
    # upload, and so this should go away when we make that change.
    custom_step_name = not (step_name.startswith('webkit_tests') or
                            step_name.startswith('webkit_layout_tests'))
    archive_step_name = 'archive_webkit_tests_results'
    if custom_step_name:
      archive_layout_test_args += ['--step-name', step_name]
      archive_step_name = 'archive results for ' + step_name

    archive_layout_test_args += api.build.slave_utils_args
    # TODO(phajdan.jr): Pass gs_acl as a parameter, not build property.
    if api.properties.get('gs_acl'):
      archive_layout_test_args.extend(['--gs-acl', api.properties['gs_acl']])
    archive_result = api.build.python(
      archive_step_name,
      archive_layout_test_results,
      archive_layout_test_args)

    # TODO(tansell): Move this to render_results function
    sanitized_buildername = re.sub('[ .()]', '_', buildername)
    base = (
      "https://test-results.appspot.com/data/layout_results/%s/%s"
      % (sanitized_buildername, buildnumber))
    if custom_step_name:
      base += '/' + step_name

    archive_result.presentation.links['layout_test_results'] = (
        base + '/layout-test-results/results.html')
    archive_result.presentation.links['(zip)'] = (
        base + '/layout-test-results.zip')


class SwarmingTest(Test):
  PRIORITY_ADJUSTMENTS = {
    'higher': -10,
    'normal': 0,
    'lower': +10,
  }

  def __init__(self, name, dimensions=None, tags=None, target_name=None,
               extra_suffix=None, priority=None, expiration=None,
               hard_timeout=None, io_timeout=None,
               waterfall_mastername=None, waterfall_buildername=None,
               set_up=None, tear_down=None):
    super(SwarmingTest, self).__init__(
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._name = name
    self._tasks = {}
    self._results = {}
    self._target_name = target_name
    self._dimensions = dimensions
    self._tags = tags
    self._extra_suffix = extra_suffix
    self._priority = priority
    self._expiration = expiration
    self._hard_timeout = hard_timeout
    self._io_timeout = io_timeout
    self._set_up = set_up
    self._tear_down = tear_down
    if dimensions and not extra_suffix:
      if dimensions.get('gpu'):
        self._extra_suffix = self._get_gpu_suffix(dimensions)
      elif 'Android' == dimensions.get('os') and dimensions.get('device_type'):
        self._extra_suffix = self._get_android_suffix(dimensions)

  @staticmethod
  def _get_gpu_suffix(dimensions):
    gpu_vendor_id = dimensions.get('gpu', '').split(':')[0].lower()
    vendor_ids = {
      '8086': 'Intel',
      '10de': 'NVIDIA',
      '1002': 'ATI',
    }
    gpu_vendor = vendor_ids.get(gpu_vendor_id) or '(%s)' % gpu_vendor_id

    os = dimensions.get('os', '')
    if os.startswith('Mac'):
      if dimensions.get('hidpi', '') == '1':
        os_name = 'Mac Retina'
      else:
        os_name = 'Mac'
    elif os.startswith('Windows'):
      os_name = 'Windows'
    else:
      os_name = 'Linux'

    return 'on %s GPU on %s' % (gpu_vendor, os_name)

  @staticmethod
  def _get_android_suffix(dimensions):
    device_codenames = {
      'angler': 'Nexus 6P',
      'athene': 'Moto G4',
      'bullhead': 'Nexus 5X',
      'dragon': 'Pixel C',
      'flo': 'Nexus 7 [2013]',
      'flounder': 'Nexus 9',
      'foster': 'NVIDIA Shield',
      'fugu': 'Nexus Player',
      'goyawifi': 'Galaxy Tab 3',
      'grouper': 'Nexus 7 [2012]',
      'hammerhead': 'Nexus 5',
      'herolte': 'Galaxy S7 [Global]',
      'heroqlteatt': 'Galaxy S7 [AT&T]',
      'j5xnlte': 'Galaxy J5',
      'm0': 'Galaxy S3',
      'mako': 'Nexus 4',
      'manta': 'Nexus 10',
      'marlin': 'Pixel 1 XL',
      'sailfish': 'Pixel 1',
      'shamu': 'Nexus 6',
      'sprout': 'Android One',
      'taimen': 'Pixel 2 XL',
      'walleye': 'Pixel 2',
      'zerofltetmo': 'Galaxy S6',
    }
    targetted_device = dimensions['device_type']
    product_name = device_codenames.get(targetted_device, targetted_device)
    return 'on Android device %s' % product_name

  @property
  def set_up(self):
    return self._set_up

  @property
  def tear_down(self):
    return self._tear_down

  @property
  def name(self):
    if self._extra_suffix:
      return '%s %s' % (self._name, self._extra_suffix)
    else:
      return self._name

  @property
  def canonical_name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  def isolate_target(self, _api):
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
    raise NotImplementedError()  # pragma: no cover

  def pre_run(self, api, suffix):
    """Launches the test on Swarming."""
    assert suffix not in self._tasks, (
        'Test %s was already triggered' % self._step_name(suffix))

    # *.isolated may be missing if *_run target is misconfigured. It's a error
    # in gyp, not a recipe failure. So carry on with recipe execution.
    isolated_hash = api.isolate.isolated_tests.get(self.isolate_target(api))
    if not isolated_hash:
      return api.python.inline(
          '[error] %s' % self._step_name(suffix),
          r"""
          import sys
          print '*.isolated file for target %s is missing' % sys.argv[1]
          sys.exit(1)
          """,
          args=[self.isolate_target(api)])

    # Create task.
    self._tasks[suffix] = self.create_task(api, suffix, isolated_hash)

    if self._priority in self.PRIORITY_ADJUSTMENTS:
      self._tasks[suffix].priority += self.PRIORITY_ADJUSTMENTS[self._priority]

    if self._expiration:
      self._tasks[suffix].expiration = self._expiration

    if self._hard_timeout:
      self._tasks[suffix].hard_timeout = self._hard_timeout

    if self._io_timeout:
      self._tasks[suffix].io_timeout = self._io_timeout

    # Add custom dimensions.
    if self._dimensions:  # pragma: no cover
      #TODO(stip): concoct a test case that will trigger this codepath
      for k, v in self._dimensions.iteritems():
         if v is None:
           # Remove key if it exists. This allows one to use None to remove
           # default dimensions.
           self._tasks[suffix].dimensions.pop(k, None)
         else:
           self._tasks[suffix].dimensions[k] = v

    # Add config-specific tags.
    self._tasks[suffix].tags.update(api.chromium.c.runtests.swarming_tags)

    # Add custom tags.
    if self._tags:
      # TODO(kbr): figure out how to cover this line of code with
      # tests after the removal of the GPU recipe. crbug.com/584469
      self._tasks[suffix].tags.update(self._tags)  # pragma: no cover

    # Set default value.
    if 'os' not in self._tasks[suffix].dimensions:
      self._tasks[suffix].dimensions['os'] = api.swarming.prefered_os_dimension(
          api.platform.name)

    return api.swarming.trigger_task(self._tasks[suffix])

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
    raise NotImplementedError()  # pragma: no cover

  def run(self, api, suffix):
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

      if api.step.active_result:
        api.step.active_result.presentation.logs['step_metadata'] = (
            json.dumps(self.step_metadata(api, suffix), sort_keys=True, indent=2)
        ).splitlines()

  def has_valid_results(self, api, suffix):
    # Test wasn't triggered or wasn't collected.
    if suffix not in self._tasks or not suffix in self._results:
      # TODO(kbr): figure out how to cover this line of code with
      # tests after the removal of the GPU recipe. crbug.com/584469
      return False  # pragma: no cover
    return self._results[suffix]['valid']

  def failures(self, api, suffix):
    assert self.has_valid_results(api, suffix)
    return self._results[suffix]['failures']

  @property
  def uses_isolate(self):
    return True

  def step_metadata(self, api, suffix=None):
    data = super(SwarmingTest, self).step_metadata(api, suffix)
    if suffix is not None:
      data['full_step_name'] = api.swarming.get_step_name(
          prefix=None, task=self._tasks[suffix])
      data['patched'] = (suffix == 'with patch')
      data['dimensions'] = self._tasks[suffix].dimensions
      data['swarm_task_ids'] = self._tasks[suffix].get_task_ids()
    return data


class SwarmingGTestTest(SwarmingTest):
  def __init__(self, name, args=None, target_name=None, shards=1,
               dimensions=None, tags=None, extra_suffix=None, priority=None,
               expiration=None, hard_timeout=None, io_timeout=None,
               upload_test_results=True, override_compile_targets=None,
               override_isolate_target=None,
               cipd_packages=None, waterfall_mastername=None,
               waterfall_buildername=None, merge=None, trigger_script=None,
               set_up=None, tear_down=None):
    super(SwarmingGTestTest, self).__init__(
        name, dimensions, tags, target_name, extra_suffix, priority, expiration,
        hard_timeout, io_timeout, waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername,
        set_up=set_up, tear_down=tear_down)
    self._args = args or []
    self._shards = shards
    self._upload_test_results = upload_test_results
    self._override_compile_targets = override_compile_targets
    self._override_isolate_target = override_isolate_target
    self._cipd_packages = cipd_packages
    self._gtest_results = {}
    self._merge = merge
    self._trigger_script = trigger_script

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  def compile_targets(self, api):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  def isolate_target(self, api):
    # TODO(agrieve,jbudorick): Remove override_isolate_target once clients
    #     have stopped using it.
    if self._override_isolate_target:
      return self._override_isolate_target
    return self.target_name

  def create_task(self, api, suffix, isolated_hash):
    # For local tests test_args are added inside api.chromium.runtest.
    args = self._args + api.chromium.c.runtests.test_args

    args = _merge_args_and_test_options(self, args)
    args = _merge_failures_for_retry(args, self, api, suffix)
    args.extend(api.chromium.c.runtests.swarming_extra_args)

    return api.swarming.gtest_task(
        title=self._step_name(suffix),
        isolated_hash=isolated_hash,
        shards=self._shards,
        test_launcher_summary_output=api.test_utils.gtest_results(
            add_json_log=False),
        cipd_packages=self._cipd_packages, extra_args=args,
        merge=self._merge, trigger_script=self._trigger_script,
        build_properties=api.chromium.build_properties)

  def validate_task_results(self, api, step_result):
    if not hasattr(step_result, 'test_utils'):
      return False, None  # pragma: no cover

    gtest_results = step_result.test_utils.gtest_results
    if not gtest_results:
      return False, None  # pragma: no cover

    global_tags = gtest_results.raw.get('global_tags', [])
    if 'UNRELIABLE_RESULTS' in global_tags:
      return False, None  # pragma: no cover

    return gtest_results.valid, gtest_results.failures

  def pass_fail_counts(self, suffix):
    if self._gtest_results.get(suffix):
      # test_result exists and is not None.
      return self._gtest_results[suffix].pass_fail_counts
    return {}

  def run(self, api, suffix):
    """Waits for launched test to finish and collects the results."""
    try:
      super(SwarmingGTestTest, self).run(api, suffix)
    finally:
      step_result = api.step.active_result
      if (hasattr(step_result, 'test_utils') and
          hasattr(step_result.test_utils, 'gtest_results')):
        gtest_results = getattr(step_result.test_utils, 'gtest_results', None)
        self._gtest_results[suffix] = gtest_results
        # Only upload test results if we have gtest results.
        if self._upload_test_results and gtest_results and gtest_results.raw:
          parsed_gtest_data = gtest_results.raw
          chrome_revision_cp = api.bot_update.last_returned_properties.get(
              'got_revision_cp', 'x@{#0}')
          chrome_revision = str(api.commit_position.parse_revision(
              chrome_revision_cp))
          api.test_results.upload(
              api.json.input(parsed_gtest_data),
              chrome_revision=chrome_revision,
              test_type=step_result.step['name'])


class LocalIsolatedScriptTest(Test):
  def __init__(self, name, args=None, target_name=None,
               override_compile_targets=None, results_handler=None,
               set_up=None, tear_down=None,
               **runtest_kwargs):
    """Constructs an instance of LocalIsolatedScriptTest.

    An LocalIsolatedScriptTest knows how to invoke an isolate which obeys a
    certain contract. The isolate's main target must be a wrapper script which
    must interpret certain command line arguments as follows:

      --isolated-script-test-output [FILENAME]

    The wrapper script must write the simplified json output that the recipes
    consume (similar to GTestTest and ScriptTest) into |FILENAME|.

    The contract may be expanded later to support functionality like sharding
    and retries of specific failed tests. Currently the examples of such wrapper
    scripts live in src/testing/scripts/ in the Chromium workspace.

    Args:
      name: Displayed name of the test. May be modified by suffixes.
      args: Arguments to be passed to the test.
      target_name: Actual name of the test. Defaults to name.
      runtest_kwargs: Additional keyword args forwarded to the runtest.
      override_compile_targets: The list of compile targets to use. If not
        specified this is the same as target_name.
      set_up: Optional set up scripts.
      tear_down: Optional tear_down scripts.
    """
    super(LocalIsolatedScriptTest, self).__init__()
    self._name = name
    self._args = args or []
    self._target_name = target_name
    self._runtest_kwargs = runtest_kwargs
    self._override_compile_targets = override_compile_targets
    self._set_up = set_up
    self._tear_down = tear_down
    self.results_handler = results_handler or JSONResultsHandler()
    self._test_results = {}

  @property
  def set_up(self):
    return self._set_up

  @property
  def tear_down(self):
    return self._tear_down

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  def isolate_target(self, _api):
    return self.target_name

  @property
  def uses_isolate(self):
    return True

  def compile_targets(self, _):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  def pass_fail_counts(self, suffix):
    if self._test_results.get(suffix):
      # test_result exists and is not None.
      return self._test_results[suffix].pass_fail_counts
    return {}

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  # TODO(nednguyen, kbr): figure out what to do with Android.
  # (crbug.com/533480)
  def run(self, api, suffix):
    args = _merge_args_and_test_options(self, self._args)

    # TODO(nednguyen, kbr): define contract with the wrapper script to rerun
    # a subset of the tests. (crbug.com/533481)

    json_results_file = api.json.output()
    args.extend(
        ['--isolated-script-test-output', json_results_file])

    step_test_data = lambda: api.json.test_api.output(
        {'valid': True, 'failures': []})

    try:
      api.isolate.run_isolated(
          self.name,
          api.isolate.isolated_tests[self.target_name],
          args,
          step_test_data=step_test_data)
    finally:
      # TODO(kbr, nedn): the logic of processing the output here is very similar
      # to that of SwarmingIsolatedScriptTest. They probably should be shared
      # between the two.
      self._test_runs[suffix] = api.step.active_result
      results = self._test_runs[suffix].json.output
      presentation = self._test_runs[suffix].presentation
      valid, failures = self.results_handler.validate_results(api, results)
      self._test_results[suffix] = (
          api.test_utils.create_results_from_json_if_needed(
              results) if valid else None)

      self.results_handler.render_results(api, results, presentation)

      if api.step.active_result.retcode == 0 and not valid:
        # This failure won't be caught automatically. Need to manually
        # raise it as a step failure.
        raise api.step.StepFailure(api.test_utils.INVALID_RESULTS_MAGIC)

    return self._test_runs[suffix]


class SwarmingIsolatedScriptTest(SwarmingTest):

  def __init__(self, name, args=None, target_name=None, shards=1,
               dimensions=None, tags=None, extra_suffix=None,
               ignore_task_failure=False, priority=None, expiration=None,
               hard_timeout=None, upload_test_results=True,
               override_compile_targets=None, perf_id=None, results_url=None,
               perf_dashboard_id=None, io_timeout=None,
               waterfall_mastername=None, waterfall_buildername=None,
               merge=None, trigger_script=None, results_handler=None,
               set_up=None, tear_down=None, idempotent=True):
    super(SwarmingIsolatedScriptTest, self).__init__(
        name, dimensions, tags, target_name, extra_suffix, priority, expiration,
        hard_timeout, io_timeout, waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername,
        set_up=set_up, tear_down=tear_down)
    self._args = args or []
    self._shards = shards
    self._upload_test_results = upload_test_results
    self._override_compile_targets = override_compile_targets
    self._perf_id=perf_id
    self._results_url = results_url
    self._perf_dashboard_id = perf_dashboard_id
    self._isolated_script_results = {}
    self._merge = merge
    self._trigger_script = trigger_script
    self._ignore_task_failure = ignore_task_failure
    self.results_handler = results_handler or JSONResultsHandler(
        ignore_task_failure=ignore_task_failure)
    self._test_results = {}
    self._idempotent = idempotent

  @property
  def target_name(self):
    return self._target_name or self._name

  def compile_targets(self, _):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  @property
  def uses_isolate(self):
    return True

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  def create_task(self, api, suffix, isolated_hash):

    args = _merge_args_and_test_options(self, self._args)

    shards = self._shards

    # We've run into issues in the past with command lines hitting a character
    # limit on windows. Do a sanity check, and only pass this list if we failed
    # less than 100 tests.
    if suffix == 'without patch' and len(
        self.failures(api, 'with patch')) < 100:
      test_list = "::".join(self.failures(api, 'with patch'))
      args.extend(['--isolated-script-test-filter', test_list])

      # Only run the tests on one shard; we don't need more, and layout tests
      # complain if you run a shard which doesn't run tests.
      shards = 1

    # For the time being, we assume all isolated_script_test are not idempotent
    # TODO(crbug.com/549140): remove the self._idempotent parameter once Telemetry
    # tests are idempotent, since that will make all isolated_script_tests
    # idempotent.
    return api.swarming.isolated_script_task(
        title=self._step_name(suffix),
        ignore_task_failure=self._ignore_task_failure,
        isolated_hash=isolated_hash, shards=shards, idempotent=self._idempotent,
        merge=self._merge, trigger_script=self._trigger_script,
        build_properties=api.chromium.build_properties, extra_args=args)

  def pass_fail_counts(self, suffix):
    if self._test_results.get(suffix):
      # test_result exists and is not None.
      return self._test_results[suffix].pass_fail_counts
    return {}

  def validate_task_results(self, api, step_result):
    # If we didn't get a step_result object at all, we can safely
    # assume that something definitely went wrong.
    if step_result is None:  # pragma: no cover
      return False, None

    results = getattr(step_result, 'isolated_script_results', None) or {}

    valid, failures = self.results_handler.validate_results(api, results)
    presentation = step_result.presentation
    self.results_handler.render_results(api, results, presentation)

    self._isolated_script_results = results

    # If we got no results and a nonzero exit code, the test probably
    # did not run correctly.
    if step_result.retcode != 0 and not results:
      return False, failures

    # Even if the output is valid, if the return code is greater than
    # MAX_FAILURES_EXIT_STATUS then the test did not complete correctly and the
    # results can't be trusted. It probably exited early due to a large number
    # of failures or an environment setup issue.
    if step_result.retcode > api.test_utils.MAX_FAILURES_EXIT_STATUS:
      return False, failures

    if step_result.retcode == 0 and not valid:
      # This failure won't be caught automatically. Need to manually
      # raise it as a step failure.
      raise api.step.StepFailure(api.test_utils.INVALID_RESULTS_MAGIC)

    # Check for perf results and upload to results dashboard if present.
    self._output_perf_results_if_present(api, step_result)

    return valid, failures

  def run(self, api, suffix):
    try:
      super(SwarmingIsolatedScriptTest, self).run(api, suffix)
    finally:
      results = self._isolated_script_results

      valid = self._results.get(suffix, {}).get('valid')
      self._test_results[suffix] = (
          api.test_utils.create_results_from_json_if_needed(
              results) if valid else None)

      if results and self._upload_test_results:
        self.results_handler.upload_results(
            api, results, self._step_name(suffix), suffix)

  def _output_perf_results_if_present(self, api, step_result):
    # webrtc overrides this method in recipe_modules/webrtc/steps.py
    pass


def generate_isolated_script(api, chromium_tests_api, mastername, buildername,
                             test_spec, bot_update_step,
                             swarming_dimensions=None,
                             scripts_compile_targets=None):
  def isolated_script_delegate_common(test, name=None, **kwargs):

    common_kwargs = {}

    # The variable substitution and precommit/non-precommit arguments
    # could be supported for the other test types too, but that wasn't
    # desired at the time of this writing.
    common_kwargs['args'] = get_args_for_test(
        api, chromium_tests_api, test, bot_update_step)
    # This features is only needed for the cases in which the *_run compile
    # target is needed to generate isolate files that contains dynamically libs.
    # TODO(nednguyen, kbr): Remove this once all the GYP builds are converted
    # to GN.
    common_kwargs['override_compile_targets'] = test.get(
        'override_compile_targets', None)

    # TODO(tansell): Remove this once custom handling of results is no longer
    # needed.
    results_handler_name = spec.get('results_handler', 'default')
    try:
        common_kwargs['results_handler'] = {
            'default': lambda: None,
            'fake': FakeCustomResultsHandler,
            'layout tests': LayoutTestResultsHandler,
        }[results_handler_name]()
    except KeyError:
      api.python.failing_step(
          'isolated_scripts spec format error',
          textwrap.wrap(textwrap.dedent("""\
              The isolated_scripts target "%s" contains a custom results_handler
              "%s" but that result handler was not found.
              """ % (name, results_handler_name))),
          as_log='details')

    return common_kwargs

  def isolated_script_swarming_delegate(spec, **kwargs):
    kwargs.update(isolated_script_delegate_common(spec, **kwargs))

    swarming_spec = spec.get('swarming', {})

    kwargs['ignore_task_failure'] = swarming_spec.get(
        'ignore_task_failure', False)
    kwargs['waterfall_buildername'] = buildername
    kwargs['waterfall_mastername'] = mastername
    kwargs['idempotent'] = swarming_spec.get('idempotent', True)

    return SwarmingIsolatedScriptTest(**kwargs)

  def isolated_script_local_delegate(spec, **kwargs):
    kwargs.update(isolated_script_delegate_common(spec, **kwargs))
    return LocalIsolatedScriptTest(**kwargs)

  for spec in test_spec.get(buildername, {}).get('isolated_scripts', []):
    for t in generator_common(
        api, spec, isolated_script_swarming_delegate,
        isolated_script_local_delegate, swarming_dimensions):
      yield t


class PythonBasedTest(Test):
  def compile_targets(self, _):
    return []  # pragma: no cover

  def run_step(self, api, suffix, cmd_args, **kwargs):
    raise NotImplementedError()  # pragma: no cover

  def run(self, api, suffix):
    cmd_args = ['--write-full-results-to',
                api.test_utils.test_results(add_json_log=False)]
    if suffix == 'without patch':
      cmd_args.extend(self.failures(api, 'with patch'))  # pragma: no cover

    try:
      self.run_step(
          api,
          suffix,
          cmd_args,
          step_test_data=lambda: api.test_utils.test_api.canned_test_output(True))
    finally:
      step_result = api.step.active_result
      self._test_runs[suffix] = step_result

      if hasattr(step_result, 'test_utils'):
        r = step_result.test_utils.test_results
        p = step_result.presentation
        _, failures = api.test_utils.limit_failures(
            r.unexpected_failures.keys(), MAX_FAILS)
        p.step_text += api.test_utils.format_step_text([
            ['unexpected_failures:', failures],
        ])

    return step_result

  def has_valid_results(self, api, suffix):
    # TODO(dpranke): we should just return zero/nonzero for success/fail.
    # crbug.com/357866
    step = self._test_runs[suffix]
    if not hasattr(step, 'test_utils'):
      return False  # pragma: no cover
    return (step.test_utils.test_results.valid and
            step.retcode <= api.test_utils.MAX_FAILURES_EXIT_STATUS and
            (step.retcode == 0) or self.failures(api, suffix))

  def failures(self, api, suffix):
    return self._test_runs[suffix].test_utils.test_results.unexpected_failures


class PrintPreviewTests(PythonBasedTest):  # pylint: disable=W032
  name = 'print_preview_tests'

  def run_step(self, api, suffix, cmd_args, **kwargs):
    platform_arg = '.'.join(['browser_test',
        api.platform.normalize_platform_name(api.platform.name)])
    args = cmd_args
    path = api.path['checkout'].join(
        'third_party', 'blink', 'tools', 'run_web_tests.py')
    args.extend(['--platform', platform_arg])

    env = {}
    if api.platform.is_linux:
      env['CHROME_DEVEL_SANDBOX'] = api.path.join(
          '/opt', 'chromium', 'chrome_sandbox')

    with api.context(env=env):
      return api.chromium.runtest(
          test=path,
          args=args,
          xvfb=True,
          name=self._step_name(suffix),
          python_mode=True,
          **kwargs)

  def compile_targets(self, api):
    return ['browser_tests', 'blink_tests']


class BisectTest(Test):  # pylint: disable=W0232
  name = 'bisect_test'

  def __init__(self, test_parameters={}, **kwargs):
    super(BisectTest, self).__init__()
    self._test_parameters = test_parameters
    self.run_results = {}
    self.kwargs = kwargs

  @property
  def abort_on_failure(self):
    return True  # pragma: no cover

  @property
  def uses_local_devices(self):
    return False

  def compile_targets(self, _):  # pragma: no cover
    return ['chrome'] # Bisect always uses a separate bot for building.

  def pre_run(self, api, _):
    self.test_config = api.bisect_tester.load_config_from_dict(
        self._test_parameters.get('bisect_config',
                                  api.properties.get('bisect_config')))

  def run(self, api, _):
    self.run_results = api.bisect_tester.run_test(
        self.test_config, **self.kwargs)

  def has_valid_results(self, *_):
    return bool(self.run_results.get('retcodes')) # pragma: no cover

  def failures(self, *_):
    return self._failures  # pragma: no cover


class BisectTestStaging(Test):  # pylint: disable=W0232
  name = 'bisect_test_staging'

  def __init__(self, test_parameters={}, **kwargs):
    super(BisectTestStaging, self).__init__()
    self._test_parameters = test_parameters
    self.run_results = {}
    self.kwargs = kwargs

  @property
  def abort_on_failure(self):
    return True  # pragma: no cover

  @property
  def uses_local_devices(self):
    return False

  def compile_targets(self, _):  # pragma: no cover
    return ['chrome'] # Bisect always uses a separate bot for building.

  def pre_run(self, api, _):
    self.test_config = api.bisect_tester_staging.load_config_from_dict(
        self._test_parameters.get('bisect_config',
                                  api.properties.get('bisect_config')))

  def run(self, api, _):
    self.run_results = api.bisect_tester_staging.run_test(
        self.test_config, **self.kwargs)

  def has_valid_results(self, *_):
    return bool(self.run_results.get('retcodes')) # pragma: no cover

  def failures(self, *_):
    return self._failures  # pragma: no cover


class AndroidTest(Test):
  def __init__(self, name, compile_targets, waterfall_mastername=None,
               waterfall_buildername=None):
    super(AndroidTest, self).__init__(
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)

    self._name = name
    self._compile_targets = compile_targets

  @property
  def name(self):
    return self._name

  def run_tests(self, api, suffix, json_results_file):
    """Runs the Android test suite and outputs the json results to a file.

    Args:
      api: Caller's API.
      suffix: Suffix added to the test name.
      json_results_file: File to output the test results.
    """
    raise NotImplementedError()  # pragma: no cover

  def run(self, api, suffix):
    assert api.chromium.c.TARGET_PLATFORM == 'android'

    nested_step_name = '%s%s' % (self._name, ' (%s)' % suffix if suffix else '')
    with api.step.nest(nested_step_name) as nested_step:
      json_results_file = api.test_utils.gtest_results(add_json_log=False)
      try:
        step_result = self.run_tests(api, suffix, json_results_file)
      except api.step.StepFailure as f:
        step_result = f.result
        raise
      finally:
        nested_step.presentation.status = step_result.presentation.status
        self._test_runs[suffix] = {'valid': False}
        gtest_results = api.test_utils.present_gtest_failures(
            step_result, nested_step.presentation)
        if gtest_results:
          failures = gtest_results.failures
          self._test_runs[suffix] = {'valid': True, 'failures': failures}

          api.test_results.upload(
              api.json.input(gtest_results.raw),
              test_type=self.name,
              chrome_revision=api.bot_update.last_returned_properties.get(
                  'got_revision_cp', 'x@{#0}'))

  def compile_targets(self, _):
    return self._compile_targets

  def has_valid_results(self, api, suffix):
    if suffix not in self._test_runs:
      return False  # pragma: no cover
    return self._test_runs[suffix]['valid']

  def failures(self, api, suffix):
    assert self.has_valid_results(api, suffix)
    return self._test_runs[suffix]['failures']


class AndroidJunitTest(AndroidTest):
  def __init__(
      self, name, waterfall_mastername=None, waterfall_buildername=None):
    super(AndroidJunitTest, self).__init__(
        name, compile_targets=[name], waterfall_mastername=None,
        waterfall_buildername=None)

  @property
  def uses_local_devices(self):
    return False

  #override
  def run_tests(self, api, suffix, json_results_file):
    return api.chromium_android.run_java_unit_test_suite(
        self.name, verbose=True, suffix=suffix,
        json_results_file=json_results_file,
        step_test_data=lambda: api.test_utils.test_api.canned_gtest_output(False))


class AndroidInstrumentationTest(AndroidTest):
  _DEFAULT_SUITES = {
    'ChromePublicTest': {
      'compile_target': 'chrome_public_test_apk',
    },
    'ChromeSyncShellTest': {
      'compile_target': 'chrome_sync_shell_test_apk',
    },
    'ChromotingTest': {
      'compile_target': 'remoting_test_apk',
    },
    'ContentShellTest': {
      'compile_target': 'content_shell_test_apk',
    },
    'MojoTest': {
      'compile_target': 'mojo_test_apk',
    },
    'SystemWebViewShellLayoutTest': {
      'compile_target': 'system_webview_shell_layout_test_apk',
    },
    'WebViewInstrumentationTest': {
      'compile_target': 'webview_instrumentation_test_apk',
    },
    'WebViewUiTest': {
      'compile_target': 'webview_ui_test_app_test_apk',
      # TODO(yolandyan): These should be removed once crbug/643660 is resolved
      'additional_compile_targets': [
        'system_webview_apk',
      ],
      'additional_apks': [
        'SystemWebView.apk',
      ],
    }
  }

  _DEFAULT_SUITES_BY_TARGET = {
    'chrome_public_test_apk': _DEFAULT_SUITES['ChromePublicTest'],
    'chrome_sync_shell_test_apk': _DEFAULT_SUITES['ChromeSyncShellTest'],
    'content_shell_test_apk': _DEFAULT_SUITES['ContentShellTest'],
    'mojo_test_apk': _DEFAULT_SUITES['MojoTest'],
    'remoting_test_apk': _DEFAULT_SUITES['ChromotingTest'],
    'system_webview_shell_layout_test_apk':
        _DEFAULT_SUITES['SystemWebViewShellLayoutTest'],
    'webview_instrumentation_test_apk':
        _DEFAULT_SUITES['WebViewInstrumentationTest'],
    'webview_ui_test_app_test_apk': _DEFAULT_SUITES['WebViewUiTest'],
  }

  def __init__(self, name, compile_targets=None, apk_under_test=None,
               test_apk=None, timeout_scale=None, annotation=None,
               except_annotation=None, screenshot=False, verbose=True,
               tool=None, additional_apks=None, store_tombstones=False,
               trace_output=False, result_details=False, args=None,
               waterfall_mastername=None, waterfall_buildername=None,
               target_name=None, set_up=None, tear_down=None):
    suite_defaults = (
        AndroidInstrumentationTest._DEFAULT_SUITES.get(name)
        or AndroidInstrumentationTest._DEFAULT_SUITES_BY_TARGET.get(name)
        or {})
    if not compile_targets:
      compile_targets = [suite_defaults.get('compile_target', target_name or name)]
      compile_targets.extend(
          suite_defaults.get('additional_compile_targets', []))

    super(AndroidInstrumentationTest, self).__init__(
        name,
        compile_targets,
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._additional_apks = (
        additional_apks or suite_defaults.get('additional_apks'))
    self._annotation = annotation
    self._apk_under_test = (
        apk_under_test or suite_defaults.get('apk_under_test'))
    self._except_annotation = except_annotation
    self._screenshot = screenshot
    self._test_apk = test_apk or suite_defaults.get('test_apk')
    self._timeout_scale = timeout_scale
    self._tool = tool
    self._verbose = verbose
    self._wrapper_script_suite_name = compile_targets[0]
    self._trace_output = trace_output
    self._store_tombstones = store_tombstones
    self._result_details = result_details
    self._args = args
    self._set_up = set_up
    self._tear_down = tear_down

  @property
  def set_up(self):
    return self._set_up

  @property
  def tear_down(self):
    return self._tear_down

  @property
  def uses_local_devices(self):
    return True

  #override
  def run_tests(self, api, suffix, json_results_file):
    return api.chromium_android.run_instrumentation_suite(
        self.name,
        test_apk=api.chromium_android.apk_path(self._test_apk),
        apk_under_test=api.chromium_android.apk_path(self._apk_under_test),
        additional_apks=[
            api.chromium_android.apk_path(a)
            for a in self._additional_apks or []],
        suffix=suffix,
        annotation=self._annotation, except_annotation=self._except_annotation,
        screenshot=self._screenshot, verbose=self._verbose, tool=self._tool,
        json_results_file=json_results_file,
        timeout_scale=self._timeout_scale,
        result_details=self._result_details,
        store_tombstones=self._store_tombstones,
        wrapper_script_suite_name=self._wrapper_script_suite_name,
        trace_output=self._trace_output,
        step_test_data=lambda: api.test_utils.test_api.canned_gtest_output(False),
        args=self._args)


class BlinkTest(Test):
  # TODO(dpranke): This should be converted to a PythonBasedTest, although it
  # will need custom behavior because we archive the results as well.
  def __init__(self, extra_args=None):
    super(BlinkTest, self).__init__()
    self._extra_args = extra_args
    self.results_handler = LayoutTestResultsHandler()

  name = 'webkit_tests'

  def compile_targets(self, api):
    return ['blink_tests']

  @property
  def uses_local_devices(self):
    return True

  def run(self, api, suffix):
    results_dir = api.path['start_dir'].join('layout-test-results')

    step_name = self._step_name(suffix)
    args = [
        '--target', api.chromium.c.BUILD_CONFIG,
        '--results-directory', results_dir,
        '--build-dir', api.chromium.c.build_dir,
        '--json-test-results', api.test_utils.test_results(add_json_log=False),
        '--master-name', api.properties['mastername'],
        '--build-number', str(api.properties['buildnumber']),
        '--builder-name', api.properties['buildername'],
        '--step-name', step_name,
        '--no-show-results',
        '--clobber-old-results',  # Clobber test results before each run.
        '--exit-after-n-failures', '5000',
        '--exit-after-n-crashes-or-timeouts', '100',
        '--debug-rwt-logging',
    ]

    if api.chromium.c.TARGET_PLATFORM == 'android':
      args.extend(['--platform', 'android'])

    if self._extra_args:
      args.extend(self._extra_args)

    if suffix == 'without patch':
      test_list = "\n".join(self.failures(api, 'with patch'))
      args.extend(['--test-list', api.raw_io.input_text(test_list),
                   '--skipped', 'always'])

    try:
      step_result = api.python(
        step_name,
        api.path['checkout'].join('third_party', 'blink', 'tools',
                                  'run_web_tests.py'),
        args,
        step_test_data=lambda: api.test_utils.test_api.canned_test_output(
            passing=True, minimal=True))

      # Mark steps with unexpected flakes as warnings. Do this here instead of
      # "finally" blocks because we only want to do this if step was successful.
      # We don't want to possibly change failing steps to warnings.
      if step_result and step_result.test_utils.test_results.unexpected_flakes:
        step_result.presentation.status = api.step.WARNING
    finally:
      step_result = api.step.active_result
      self._test_runs[suffix] = step_result

      if step_result:
        results = step_result.test_utils.test_results

        self.results_handler.render_results(
            api, results, step_result.presentation)

        self.results_handler.upload_results(api, results, step_name, suffix)

  def has_valid_results(self, api, suffix):  # pragma: no cover
    if suffix not in self._test_runs:
      return False
    step = self._test_runs[suffix]
    # TODO(dpranke): crbug.com/357866 - note that all comparing against
    # MAX_FAILURES_EXIT_STATUS tells us is that we did not exit early
    # or abnormally; it does not tell us how many failures there actually
    # were, which might be much higher (up to 5000 diffs, where we
    # would bail out early with --exit-after-n-failures) or lower
    # if we bailed out after 100 crashes w/ -exit-after-n-crashes, in
    # which case the retcode is actually 130
    return (step.test_utils.test_results.valid and
            step.retcode <= api.test_utils.MAX_FAILURES_EXIT_STATUS)

  def failures(self, api, suffix):
    return self._test_runs[suffix].test_utils.test_results.unexpected_failures


class MiniInstallerTest(PythonBasedTest):  # pylint: disable=W0232
  name = 'test_installer'

  def compile_targets(self, _):
    return ['mini_installer_tests']

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


class WebViewCTSTest(AndroidTest):

  def __init__(self, platform, arch, command_line_args=None,
               waterfall_mastername=None, waterfall_buildername=None):
    super(WebViewCTSTest, self).__init__(
        'WebView CTS: %s' % platform,
        ['system_webview_apk'],
        waterfall_mastername,
        waterfall_buildername)
    self._arch = arch
    self._command_line_args = command_line_args
    self._platform = platform

  @property
  def uses_local_devices(self):
    return True

  def run_tests(self, api, suffix, json_results_file):
    api.chromium_android.adb_install_apk(
        api.chromium_android.apk_path('SystemWebView.apk'))
    return api.chromium_android.run_webview_cts(
        android_platform=self._platform,
        suffix=suffix,
        command_line_args=self._command_line_args,
        arch=self._arch,
        json_results_file=json_results_file,
        result_details=True)


class IncrementalCoverageTest(Test):
  _name = 'incremental_coverage'

  @property
  def uses_local_devices(self):
    return True

  def has_valid_results(self, api, suffix):
    return True

  def failures(self, api, suffix):
    return []

  @property
  def name(self):  # pragma: no cover
    """Name of the test."""
    return IncrementalCoverageTest._name

  def compile_targets(self, api):
    """List of compile targets needed by this test."""
    return []

  def run(self, api, suffix):
    api.chromium_android.coverage_report(upload=False)
    api.chromium_android.get_changed_lines_for_revision()
    api.chromium_android.incremental_coverage_report()

class FindAnnotatedTest(Test):
  _TEST_APKS = {
      'chrome_public_test_apk': 'ChromePublicTest',
      'chrome_sync_shell_test_apk': 'ChromeSyncShellTest',
      'content_shell_test_apk': 'ContentShellTest',
      'system_webview_shell_layout_test_apk': 'SystemWebViewShellLayoutTest',
      'webview_instrumentation_test_apk': 'WebViewInstrumentationTest',
  }

  def compile_targets(self, api):
    return FindAnnotatedTest._TEST_APKS.keys()

  def run(self, api, suffix):
    with api.tempfile.temp_dir('annotated_tests_json') as temp_output_dir:
      timestamp_string = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')
      if api.properties.get('buildername') is not None:
        timestamp_string = api.properties.get('current_time', timestamp_string)

      args = [
          '--apk-output-dir', api.chromium.output_dir,
          '--json-output-dir', temp_output_dir,
          '--timestamp-string', timestamp_string,
          '-v']
      args.extend(
          ['--test-apks'] + [i for i in FindAnnotatedTest._TEST_APKS.values()])
      with api.context(cwd=api.path['checkout']):
        api.python(
            'run find_annotated_tests.py',
            api.path['checkout'].join(
                'tools', 'android', 'find_annotated_tests.py'),
            args=args)
      api.gsutil.upload(
          temp_output_dir.join(
              '%s-android-chrome.json' % timestamp_string),
          'chromium-annotated-tests', 'android')


class WebRTCPerfTest(LocalGTestTest):
  """A LocalGTestTest reporting perf metrics.

  WebRTC is the only project that runs correctness tests with perf reporting
  enabled at the same time, which differs from the chromium.perf bots.
  """
  def __init__(self, name, args, perf_id, perf_config_mappings,
               commit_position_property, upload_wav_files_from_test,
               **runtest_kwargs):
    """Construct a WebRTC Perf test.

    Args:
      name: Name of the test.
      args: Command line argument list.
      perf_id: String identifier (preferably unique per machine).
      perf_config_mappings: A dict that maps revision keys to be put in the perf
        config to revision properties coming from the bot_update step.
      commit_position_property: Commit position property for the Chromium
        checkout. It's needed because for chromium.webrtc.fyi 'got_revision_cp'
        refers to WebRTC's commit position instead of Chromium's, so we have to
        use 'got_cr_revision_cp' instead.
      upload_wav_files_from_test: If true, will upload all .wav files output by
         the test. The test must obey the --webrtc_save_audio_recordings_in
         flag. This is used by webrtc_audio_quality_browsertest.
    """
    assert perf_id
    self._perf_config_mappings = perf_config_mappings or {}
    # TODO(kjellander): See if it's possible to rely on the build spec
    # properties 'perf-id' and 'results-url' as set in the
    # chromium_tests/chromium_perf.py. For now, set these to get an exact
    # match of our current expectations.
    runtest_kwargs['perf_id'] = perf_id
    runtest_kwargs['results_url'] = RESULTS_URL

    # TODO(kjellander): See if perf_dashboard_id is still needed.
    runtest_kwargs['perf_dashboard_id'] = name
    runtest_kwargs['annotate'] = 'graphing'

    self.upload_wav_files_from_test = upload_wav_files_from_test

    super(WebRTCPerfTest, self).__init__(
        name, args, commit_position_property=commit_position_property,
        **runtest_kwargs)

  def run(self, api, suffix):
    self._wire_up_perf_config(api)
    if self.upload_wav_files_from_test:
      recordings_dir = self._prepare_gathering_wav_files(api)

    try:
      super(WebRTCPerfTest, self).run(api, suffix)
    finally:
      if self.upload_wav_files_from_test:
        self._upload_wav_files(api, recordings_dir)
        api.file.rmtree('Remove recordings_dir', recordings_dir)

  def _prepare_gathering_wav_files(self, api):
    # Pass an arg to the test so it knows where to write the .wav files.
    # This arg is implemented by the WebRTC audio quality browser test.
    recordings_dir = api.path.mkdtemp(prefix='recordings_dir')
    self._args.append(
        '--webrtc_save_audio_recordings_in=%s' % recordings_dir)
    return recordings_dir

  def _wire_up_perf_config(self, api):
    props = api.bot_update.last_returned_properties
    perf_config = { 'a_default_rev': 'r_webrtc_git' }

    for revision_key, revision_prop in self._perf_config_mappings.iteritems():
      perf_config[revision_key] = props[revision_prop]

    # 'got_webrtc_revision' property is present for bots in both chromium.webrtc
    # and chromium.webrtc.fyi in reality, but due to crbug.com/713356, the
    # latter don't get properly simulated. Fallback to got_revision then.
    webrtc_rev = props.get('got_webrtc_revision', props['got_revision'])

    perf_config['r_webrtc_git'] = webrtc_rev

    self._runtest_kwargs['perf_config'] = perf_config

  def _upload_wav_files(self, api, recordings_dir):
    wav_files = api.file.listdir('look for wav files', recordings_dir)
    if not wav_files:
      # The test can elect to not write any files, if it succeeds.
      return

    zip_path = api.path['cleanup'].join('webrtc_wav_files.zip')
    api.zip.directory('zip wav files from test', recordings_dir, zip_path)

    props = api.properties
    dest = 'test_artifacts/%s/%s/%s/wav_files.zip' % (props['mastername'],
                                                      props['buildername'],
                                                      props['buildnumber'])

    api.gsutil.upload(source=zip_path, bucket='chromium-webrtc',
        dest=dest, args=['-a', 'public-read'], unauthenticated_url=True,
        link_name='Recordings from test')


class MockTest(Test):
  """A Test solely intended to be used in recipe tests."""

  class ExitCodes(object):
    FAILURE = 1
    INFRA_FAILURE = 2

  def __init__(self, name='MockTest',
               waterfall_mastername=None, waterfall_buildername=None,
               abort_on_failure=False, has_valid_results=True, failures=None):
    super(MockTest, self).__init__(waterfall_mastername, waterfall_buildername)
    self._abort_on_failure = abort_on_failure
    self._failures = failures or []
    self._has_valid_results = has_valid_results
    self._name = name

  @property
  def name(self):
    return self._name

  @contextlib.contextmanager
  def _mock_exit_codes(self, api):
    try:
      yield
    except api.step.StepFailure as f:
      if f.result.retcode == self.ExitCodes.INFRA_FAILURE:
        i = api.step.InfraFailure(f.name, result=f.result)
        i.result.presentation.status = api.step.EXCEPTION
        raise i
      raise

  def _mock_suffix(self, suffix):
    return ' (%s)' % suffix if suffix else ''

  def pre_run(self, api, suffix):
    with self._mock_exit_codes(api):
      api.step('pre_run %s%s' % (self.name, self._mock_suffix(suffix)), None)

  def run(self, api, suffix):
    with self._mock_exit_codes(api):
      api.step('%s%s' % (self.name, self._mock_suffix(suffix)), None)

  def has_valid_results(self, api, suffix):
    api.step('has_valid_results %s%s' % (self.name, self._mock_suffix(suffix)), None)
    return self._has_valid_results

  def failures(self, api, suffix):
    api.step('failures %s%s' % (self.name, self._mock_suffix(suffix)), None)
    return self._failures

  @property
  def abort_on_failure(self):
    return self._abort_on_failure
