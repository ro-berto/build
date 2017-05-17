# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import json
import re
import string
import textwrap
import traceback

from recipe_engine.types import freeze


RESULTS_URL = 'https://chromeperf.appspot.com'


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

  def isolate_target(self, _api):
    """Returns isolate target name. Defaults to name.

    The _api is here in case classes want to use api information to alter the
    isolation target.
    """
    return self.name  # pragma: no cover

  @staticmethod
  def compile_targets(api):
    """List of compile targets needed by this test."""
    raise NotImplementedError()  # pragma: no cover

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

  @property
  def uses_local_devices(self):
    return False # pragma: no cover

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


class SizesStep(Test):
  def __init__(self, results_url, perf_id):
    self.results_url = results_url
    self.perf_id = perf_id

  def run(self, api, suffix):
    return api.chromium.sizes(self.results_url, self.perf_id)

  @staticmethod
  def compile_targets(_):
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
      name += ' (%s)' % suffix

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
        self._test_runs[suffix].presentation.step_text += (
            api.test_utils.format_step_text([
              ['failures:', self.failures(api, suffix)]
            ]))

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    try:
      # Make sure the JSON includes all necessary data.
      self.failures(api, suffix)

      return self._test_runs[suffix].json.output['valid']
    except Exception:  # pragma: no cover
      return False

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.output['failures']


class LocalGTestTest(Test):
  def __init__(self, name, args=None, target_name=None, use_isolate=False,
               revision=None, webkit_revision=None,
               android_shard_timeout=None, android_tool=None,
               override_compile_targets=None, override_isolate_target=None,
               use_xvfb=True, waterfall_mastername=None,
               waterfall_buildername=None, **runtest_kwargs):
    """Constructs an instance of LocalGTestTest.

    Args:
      name: Displayed name of the test. May be modified by suffixes.
      args: Arguments to be passed to the test.
      target_name: Actual name of the test. Defaults to name.
      use_isolate: When set, uses api.isolate.runtest to invoke the test.
          Calling recipe should have isolate in their DEPS.
      revision: Revision of the Chrome checkout.
      webkit_revision: Revision of the WebKit checkout.
      override_compile_targets: List of compile targets for this test
          (for tests that don't follow target naming conventions).
      override_isolate_target: List of isolate targets for this test
          (for tests that don't follow target naming conventions).
      use_xvfb: whether to use the X virtual frame buffer. Only has an
          effect on Linux. Defaults to True. Mostly harmless to
          specify this, except on GPU bots.
      runtest_kwargs: Additional keyword args forwarded to the runtest.

    """
    super(LocalGTestTest, self).__init__(
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._name = name
    self._args = args or []
    self._target_name = target_name
    self._use_isolate = use_isolate
    self._revision = revision
    self._webkit_revision = webkit_revision
    self._android_shard_timeout = android_shard_timeout
    self._android_tool = android_tool
    self._override_compile_targets = override_compile_targets
    self._override_isolate_target = override_isolate_target
    self._use_xvfb = use_xvfb
    self._runtest_kwargs = runtest_kwargs
    self._gtest_results = {}

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def uses_local_devices(self):
    return True # pragma: no cover

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
    # Copy the list because run can be invoked multiple times and we modify
    # the local copy.
    args = self._args[:]
    is_android = api.chromium.c.TARGET_PLATFORM == 'android'
    options = self.test_options
    test_filter = options.test_filter

    if suffix == 'without patch':
      test_filter = self.failures(api, 'with patch')

    kwargs = {}
    if test_filter and is_android:  # pragma: no cover
      kwargs['gtest_filter'] = ':'.join(test_filter)
      test_filter = None

    # We pass a local test_filter variable to override the immutable
    # options.test_filter, in case test_filter was modified in the suffix ==
    # without patch clause above.
    args = GTestTest.args_from_options(api, args, self,
                                       override_test_filter=test_filter)

    gtest_results_file = api.test_utils.gtest_results(add_json_log=False)
    step_test_data = lambda: api.test_utils.test_api.canned_gtest_output(True)

    kwargs['name'] = self._step_name(suffix)
    kwargs['args'] = args
    kwargs['step_test_data'] = step_test_data

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
      else:
        api.chromium.runtest(self.target_name, revision=self._revision,
                             webkit_revision=self._webkit_revision, **kwargs)
      # TODO(kbr): add functionality to generate_gtest to be able to
      # force running these local gtests via isolate from the src-side
      # JSON files. crbug.com/584469
    finally:
      step_result = api.step.active_result
      self._test_runs[suffix] = step_result

      if hasattr(step_result, 'test_utils'):
        r = step_result.test_utils.gtest_results
        p = step_result.presentation
        self._gtest_results[suffix] = r

        if r.valid:
          p.step_text += api.test_utils.format_step_text([
            ['failures:', r.failures]
          ])

        if api.test_results.c.test_results_server:
          api.test_results.upload(
              api.json.input(r.raw),
              test_type=self.name,
              chrome_revision=api.bot_update.last_returned_properties.get(
                  'got_revision_cp', 'x@{#0}'))


    return step_result

  def pass_fail_counts(self, suffix):
    if suffix in self._gtest_results:
      return self._gtest_results[suffix].pass_fail_counts

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

  def step_metadata(self, api, suffix):
    return {
        'waterfall_mastername': self._waterfall_mastername,
        'waterfall_buildername': self._waterfall_buildername,
        'canonical_step_name': self._name,
        'patched': suffix == 'with patch',
    }


def get_args_for_test(api, chromium_tests_api, test_spec, bot_update_step):
  """Gets the argument list for a dynamically generated test, as
  provided by the JSON files in src/testing/buildbot/ in the Chromium
  workspace. This function provides the following build properties in
  the form of variable substitutions in the tests' argument lists:

      buildername
      got_revision

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
  if chromium_tests_api.is_precommit_mode():
    args = args + test_spec.get('precommit_args', [])
  else:
    args = args + test_spec.get('non_precommit_args', [])
  # Perform substitution of known variables.
  substitutions = {
    'buildername': api.properties.get('buildername'),
    'got_revision': bot_update_step.presentation.properties['got_revision']
  }
  return [string.Template(arg).safe_substitute(substitutions) for arg in args]


def generate_gtest(api, chromium_tests_api, mastername, buildername, test_spec,
                   bot_update_step, enable_swarming=False,
                   swarming_dimensions=None, scripts_compile_targets=None):
  def canonicalize_test(test):
    if isinstance(test, basestring):
      canonical_test = {'test': test}
    else:
      canonical_test = dict(test)

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
    swarming_dimension_sets = None
    swarming_priority = None
    swarming_expiration = None
    swarming_hard_timeout = None
    cipd_packages = None
    if enable_swarming:
      swarming_spec = test.get('swarming', {})
      if swarming_spec.get('can_use_on_swarming_builders'):
        use_swarming = True
        swarming_shards = swarming_spec.get('shards', 1)
        swarming_dimension_sets = swarming_spec.get('dimension_sets')
        swarming_priority = swarming_spec.get('priority_adjustment')
        swarming_expiration = swarming_spec.get('expiration')
        swarming_hard_timeout = swarming_spec.get('hard_timeout')
        packages = swarming_spec.get('cipd_packages')
        if packages:
          cipd_packages = [(p['location'],
                            p['cipd_package'],
                            p['revision'])
                           for p in packages]
    override_compile_targets = test.get('override_compile_targets', None)
    override_isolate_target = test.get('override_isolate_target', None)
    target_name = str(test['test'])
    name = str(test.get('name', target_name))
    swarming_dimensions = swarming_dimensions or {}
    use_xvfb = test.get('use_xvfb', True)
    merge = dict(test.get('merge', {}))
    if merge:
      merge_script = merge.get('script')
      if merge_script:
        if merge_script.startswith('//'):
          merge['script'] = api.path['checkout'].join(
              merge_script[2:].replace('/', api.path.sep))
        else:
          api.python.failing_step(
              'gtest spec format error',
              textwrap.wrap(textwrap.dedent("""\
                  The gtest target "%s" contains a custom merge_script "%s"
                  that doesn't match the expected format. Custom merge_script entries
                  should be a path relative to the top-level chromium src directory and
                  should start with "//".
                  """ % (name, merge_script))),
              as_log='details')

    if use_swarming and swarming_dimension_sets:
      for dimensions in swarming_dimension_sets:
        # Yield potentially multiple invocations of the same test, on
        # different machine configurations.
        new_dimensions = dict(swarming_dimensions)
        new_dimensions.update(dimensions)
        yield GTestTest(name, args=args, target_name=target_name,
                        flakiness_dash=True,
                        enable_swarming=True,
                        swarming_shards=swarming_shards,
                        swarming_dimensions=new_dimensions,
                        swarming_priority=swarming_priority,
                        swarming_expiration=swarming_expiration,
                        swarming_hard_timeout=swarming_hard_timeout,
                        override_compile_targets=override_compile_targets,
                        override_isolate_target=override_isolate_target,
                        use_xvfb=use_xvfb, cipd_packages=cipd_packages,
                        waterfall_mastername=mastername,
                        waterfall_buildername=buildername,
                        merge=merge)
    else:
      yield GTestTest(name, args=args, target_name=target_name,
                      flakiness_dash=True,
                      enable_swarming=use_swarming,
                      swarming_dimensions=swarming_dimensions,
                      swarming_shards=swarming_shards,
                      swarming_priority=swarming_priority,
                      swarming_expiration=swarming_expiration,
                      swarming_hard_timeout=swarming_hard_timeout,
                      override_compile_targets=override_compile_targets,
                      override_isolate_target=override_isolate_target,
                      use_xvfb=use_xvfb, cipd_packages=cipd_packages,
                      waterfall_mastername=mastername,
                      waterfall_buildername=buildername,
                      merge=merge)


def generate_instrumentation_test(api, chromium_tests_api, mastername,
                                  buildername, test_spec, bot_update_step,
                                  enable_swarming=False,
                                  swarming_dimensions=None,
                                  scripts_compile_targets=None):
  for test in test_spec.get(buildername, {}).get('instrumentation_tests', []):
    test_name = str(test.get('test'))
    use_swarming = False
    if enable_swarming:
      swarming_spec = test.get('swarming', {})
      if swarming_spec.get('can_use_on_swarming_builders'):
        use_swarming = True
        swarming_shards = swarming_spec.get('shards', 1)
        swarming_dimension_sets = swarming_spec.get('dimension_sets')
        swarming_priority = swarming_spec.get('priority_adjustment')
        swarming_expiration = swarming_spec.get('expiration')
    args = get_args_for_test(api, chromium_tests_api, test,
                             bot_update_step)
    if use_swarming and swarming_dimension_sets:
      for dimensions in swarming_dimension_sets:
        # TODO(stip): Swarmify instrumentation tests
        pass
    else:
      yield AndroidInstrumentationTest(
          test_name,
          compile_targets=test.get('override_compile_targets'),
          render_results_dir=test.get('render_results_dir'),
          timeout_scale=test.get('timeout_scale'),
          result_details=True,
          store_tombstones=True,
          args=args,
          waterfall_mastername=mastername, waterfall_buildername=buildername)


def generate_junit_test(api, chromium_tests_api, mastername, buildername,
                        test_spec, bot_update_step, enable_swarming=False,
                        swarming_dimensions=None,
                        scripts_compile_targets=None):
  for test in test_spec.get(buildername, {}).get('junit_tests', []):
    yield AndroidJunitTest(
        str(test['test']),
        waterfall_mastername=mastername, waterfall_buildername=buildername)


def generate_script(api, chromium_tests_api, mastername, buildername, test_spec,
                    bot_update_step, enable_swarming=False,
                    swarming_dimensions=None, scripts_compile_targets=None):
  for script_spec in test_spec.get(buildername, {}).get('scripts', []):
    yield ScriptTest(
        str(script_spec['name']),
        script_spec['script'],
        scripts_compile_targets,
        script_spec.get('args', []),
        script_spec.get('override_compile_targets', []),
        waterfall_mastername=mastername, waterfall_buildername=buildername)


class DynamicPerfTests(Test):
  # Note: SystemWebViewShell.apk may not be required. Might be able to remove.
  WEBVIEW_REQUIRED_APKS = ['SystemWebView.apk', 'SystemWebViewShell.apk']

  def __init__(self, perf_id, platform, target_bits, max_battery_temp=350,
               num_device_shards=1, num_host_shards=1, shard_index=0,
               override_browser_name=None, enable_platform_mode=False,
               pass_adb_path=True, num_retries=0, replace_webview=False):
    """

    Args:
      replace_webview: If this test replaces (and tests) the system webview,
      rather than chrome itself.
    """
    self._perf_id = perf_id
    self._platform = platform
    self._target_bits = target_bits

    self._enable_platform_mode = enable_platform_mode
    self._max_battery_temp = max_battery_temp
    self._num_host_shards = num_host_shards
    self._num_device_shards = num_device_shards
    self._num_retries = num_retries
    self._pass_adb_path = pass_adb_path
    self._shard_index = shard_index
    self._replace_webview = replace_webview

    if override_browser_name:
      # TODO(phajdan.jr): restore coverage after moving to chromium/src .
      self._browser_name = override_browser_name  # pragma: no cover
    else:
      if platform == 'android':
        if self._replace_webview:
          self._browser_name = 'android-webview'
        else:
          self._browser_name = 'android-chromium'
      elif platform == 'win' and target_bits == 64:
        self._browser_name = 'release_x64'
      else:
        self._browser_name ='release'

  @property
  def name(self):
    return 'dynamic_perf_tests'   # pragma: no cover

  @property
  def uses_local_devices(self):
    return True

  def run(self, api, suffix):
    if self._replace_webview:
      for apk in self.WEBVIEW_REQUIRED_APKS:
        api.chromium_android.adb_install_apk(
            api.chromium.output_dir.join('apks', apk))

    tests = self._test_list(api)

    if self._num_device_shards == 1:
      self._run_serially(api, tests)
    else:
      self._run_sharded(api, tests)

  def _test_list(self, api):
    if self._platform == 'android':
      # Must have already called device_status_check().
      device = api.chromium_android.devices[0]
    else:
      device = None

    tests = api.chromium.list_perf_tests(
        browser=self._browser_name,
        num_shards=self._num_host_shards * self._num_device_shards,
        device=device).json.output

    tests['steps'] = {k: v for k, v in tests['steps'].iteritems()
        if v['device_affinity'] / self._num_device_shards == self._shard_index}
    for test_info in tests['steps'].itervalues():
      test_info['device_affinity'] %= self._num_device_shards

    return tests

  def _run_sharded(self, api, tests):
    api.chromium_android.run_sharded_perf_tests(
      config=api.json.input(data=tests),
      perf_id=self._perf_id,
      chartjson_file=True,
      max_battery_temp=self._max_battery_temp,
      known_devices_file=api.chromium_android.known_devices_file,
      enable_platform_mode=self._enable_platform_mode,
      pass_adb_path=self._pass_adb_path,
      num_retries=self._num_retries)

  def _run_serially(self, api, tests):
    failure = None
    for test_name, test in sorted(tests['steps'].iteritems()):
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
            perf_id=self._perf_id,
            test_type=test.get('perf_dashboard_id', test_name),
            xvfb=True,
            chartjson_file=True)
      except api.step.StepFailure as f: # pragma: no cover
        failure = f

    if failure: # pragma: no cover
      raise failure

  @staticmethod
  def compile_targets(_):
    return []


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

  @classmethod
  def _format_failures(cls, state, failures):
    failures.sort()
    num_failures = len(failures)
    if num_failures > cls.MAX_FAILS:
      failures = failures[:cls.MAX_FAILS]
      failures.append('... %s more ...' % (num_failures - cls.MAX_FAILS))
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
      test_type=step_name, test_results_server='test-results.appspot.com')

  def render_results(self, api, results, presentation):
    try:
      results = api.test_utils.create_results_from_json_if_needed(
          results)
    except Exception as e:
      presentation.status = api.step.EXCEPTION
      presentation.step_text += api.test_utils.format_step_text([
          ("Exception while processing test results: %s" % str(e),),
      ])
      return

    if not results.valid:
      # TODO(tansell): Change this to api.step.EXCEPTION after discussion.
      presentation.status = api.step.FAILURE
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
        presentation.status = api.step.FAILURE

      step_text += [
          ('%s passed, %s failed (%s total)' % (
              len(results.passes.keys()),
              len(results.unexpected_failures.keys()),
              len(results.tests)),),
      ]

    else:
      if results.unexpected_flakes:
        presentation.status = api.step.WARNING
      if results.unexpected_failures:
        presentation.status = api.step.FAILURE

      step_text += [
          ('Total tests: %s' % len(results.tests), [
              self._format_counts(
                  'Passed',
                  len(results.passes.keys()),
                  len(results.unexpected_passes.keys())),
              self._format_counts(
                  'Skipped',
                  len(results.skipped.keys()),
                  0),
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
      return False, [str(e)]

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
    archive_layout_test_args += api.build.slave_utils_args
    # TODO(phajdan.jr): Pass gs_acl as a parameter, not build property.
    if api.properties.get('gs_acl'):
      archive_layout_test_args.extend(['--gs-acl', api.properties['gs_acl']])
    archive_result = api.python(
      'archive_webkit_tests_results',
      archive_layout_test_results,
      archive_layout_test_args)

    # TODO(tansell): Move this to render_results function
    sanitized_buildername = re.sub('[ .()]', '_', buildername)
    base = (
      "https://storage.googleapis.com/chromium-layout-test-archives/%s/%s"
      % (sanitized_buildername, buildnumber))

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
               waterfall_mastername=None, waterfall_buildername=None):
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
    if dimensions and not extra_suffix:
      self._extra_suffix = self._get_gpu_suffix(dimensions)

  @staticmethod
  def _get_gpu_suffix(dimensions):
    if not dimensions.get('gpu'):
      return None
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

  @property
  def name(self):
    if self._extra_suffix:
      return '%s %s' % (self._name, self._extra_suffix)
    else:
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
    raise NotImplementedError()  # pragma: no cover

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
    masked_exception = None
    masked_exception_text = None
    try:
      try:
        api.swarming.collect_task(self._tasks[suffix])
      except Exception as e:
        masked_exception = e
        masked_exception_text = traceback.format_exc()
        raise
      finally:
        valid, failures = self.validate_task_results(api, api.step.active_result)
        self._results[suffix] = {'valid': valid, 'failures': failures}

        api.step.active_result.presentation.logs['step_metadata'] = (
            json.dumps(self.step_metadata(api, suffix), sort_keys=True, indent=2)
        ).splitlines()
    except Exception as e:  # pragma: no cover
      if (masked_exception and e != masked_exception and
          api.properties.get('builder') == 'linux_chromium_rel_ng'):
        print 'DEBUG_DEBUG_DEBUG marker\n' + masked_exception_text
      raise

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
  def uses_swarming(self):
    return True

  def step_metadata(self, api, suffix):
    return {
      'waterfall_mastername': self._waterfall_mastername,
      'waterfall_buildername': self._waterfall_buildername,
      'canonical_step_name': self._name,
      'full_step_name': api.swarming.get_step_name(
          prefix=None, task=self._tasks[suffix]),
      'dimensions': self._tasks[suffix].dimensions,
      'patched': suffix == 'with patch',
      'swarm_task_ids': self._tasks[suffix].get_task_ids(),
    }


class SwarmingGTestTest(SwarmingTest):
  def __init__(self, name, args=None, target_name=None, shards=1,
               dimensions=None, tags=None, extra_suffix=None, priority=None,
               expiration=None, hard_timeout=None, upload_test_results=True,
               override_compile_targets=None, override_isolate_target=None,
               cipd_packages=None, waterfall_mastername=None,
               waterfall_buildername=None, merge=None):
    super(SwarmingGTestTest, self).__init__(
        name, dimensions, tags, target_name, extra_suffix, priority, expiration,
        hard_timeout, waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._args = args or []
    self._shards = shards
    self._upload_test_results = upload_test_results
    self._override_compile_targets = override_compile_targets
    self._override_isolate_target = override_isolate_target
    self._cipd_packages = cipd_packages
    self._gtest_results = {}
    self._merge = merge

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
    args = self._args[:]
    args.extend(api.chromium.c.runtests.test_args)

    options = self.test_options
    test_filter = options.test_filter

    if suffix == 'without patch':
      # If rerunning without a patch, run only tests that failed.
      test_filter = sorted(self.failures(api, 'with patch'))

    args = GTestTest.args_from_options(api, args, self,
                                       override_test_filter=test_filter)
    args.extend(api.chromium.c.runtests.swarming_extra_args)

    return api.swarming.gtest_task(
        title=self._step_name(suffix),
        isolated_hash=isolated_hash,
        shards=self._shards,
        test_launcher_summary_output=api.test_utils.gtest_results(
            add_json_log=False),
        cipd_packages=self._cipd_packages, extra_args=args,
        merge=self._merge, build_properties=api.chromium.build_properties)

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
    if suffix in self._gtest_results:
      return self._gtest_results[suffix].pass_fail_counts

  def post_run(self, api, suffix):
    """Waits for launched test to finish and collects the results."""
    try:
      super(SwarmingGTestTest, self).post_run(api, suffix)
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
              test_type=step_result.step['name'],
              test_results_server='test-results.appspot.com')


class LocalIsolatedScriptTest(Test):
  def __init__(self, name, args=None, target_name=None,
               override_compile_targets=None, results_handler=None,
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
    """
    super(LocalIsolatedScriptTest, self).__init__()
    self._name = name
    self._args = args or []
    self._target_name = target_name
    self._runtest_kwargs = runtest_kwargs
    self._override_compile_targets = override_compile_targets
    self.results_handler = results_handler or JSONResultsHandler()

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  def isolate_target(self, _api):
    return self.target_name

  @property
  def uses_swarming(self):
    return True

  def compile_targets(self, _):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  # TODO(nednguyen, kbr): figure out what to do with Android.
  # (crbug.com/533480)
  def run(self, api, suffix):
    # Copy the list because run can be invoked multiple times and we modify
    # the local copy.
    args = self._args[:]

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
               merge=None, results_handler=None):
    super(SwarmingIsolatedScriptTest, self).__init__(
        name, dimensions, tags, target_name, extra_suffix, priority, expiration,
        hard_timeout, io_timeout, waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._args = args or []
    self._shards = shards
    self._upload_test_results = upload_test_results
    self._override_compile_targets = override_compile_targets
    self._perf_id=perf_id
    self._results_url = results_url
    self._perf_dashboard_id = perf_dashboard_id
    self._isolated_script_results = {}
    self._merge = merge
    self._ignore_task_failure = ignore_task_failure
    self.results_handler = results_handler or JSONResultsHandler()

  @property
  def target_name(self):
    return self._target_name or self._name

  def compile_targets(self, _):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  @property
  def uses_swarming(self):
    return True

  def create_task(self, api, suffix, isolated_hash):
    browser_config = api.chromium.c.build_config_fs.lower()
    args = self._args[:]

    # TODO(nednguyen): only rerun the tests that failed for the "without patch"
    # suffix.

    # For the time being, we assume all isolated_script_test are not idempotent
    # TODO(nednguyen): make this configurable in isolated_scripts's spec.
    return api.swarming.isolated_script_task(
        title=self._step_name(suffix),
        ignore_task_failure=self._ignore_task_failure,
        isolated_hash=isolated_hash, shards=self._shards, idempotent=False,
        merge=self._merge, build_properties=api.chromium.build_properties,
        extra_args=args)

  def validate_task_results(self, api, step_result):
    results = getattr(step_result, 'isolated_script_results', None) or {}

    valid, failures = self.results_handler.validate_results(api, results)
    presentation = step_result.presentation
    self.results_handler.render_results(api, results, presentation)
    if (self._ignore_task_failure and valid and
        presentation.status == api.step.FAILURE):
      presentation.status = api.step.WARNING

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

    # Check for chartjson results and upload to results dashboard if present.
    self._output_chartjson_results_if_present(api, step_result)

    return valid, failures

  def post_run(self, api, suffix):
    try:
      super(SwarmingIsolatedScriptTest, self).post_run(api, suffix)
    finally:
      results = self._isolated_script_results
      if results and self._upload_test_results:
        self.results_handler.upload_results(
            api, results, self._step_name(suffix), suffix)

  def _output_chartjson_results_if_present(self, api, step_result):
    results = \
      getattr(step_result, 'isolated_script_chartjson_results', None) or {}

    if not self._perf_id or not self._results_url:
      # We aren't correctly configured to send data.
      if results:
        # warn if we have results and aren't uploading them
        step_result.presentation.logs['NOT_UPLOADING_CHART_JSON'] = [
            'Info: Bot is missing perf_id and/or results_url configuration, so'
            ' not uploading chart json']
      return

    if not results:
      # No data was generated
      return

    if not results.get('enabled', True):
      step_result.presentation.logs['DISABLED_BENCHMARK'] = \
         ['Info: Benchmark disabled, not sending results to dashboard']
      return

    # TODO(eyaich): Remove logging once we debug uploading chartjson
    # to perf dashboard
    step_result.presentation.logs['chartjson_info'] = \
        ['Info: Setting up arguments for perf dashboard']

    results_file = api.raw_io.input_text(data=json.dumps(results))
    # Produces a step that uploads results to dashboard
    args = [
        '--results-file', results_file,
        # We are passing this in solely to have the output show up as a link
        # in the step log, it will not be used after the upload is complete.
        '--output-json-file', api.json.output(),
        '--perf-id', self._perf_id,
        '--results-url', self._results_url,
        '--name', self._perf_dashboard_id,
        '--buildername', api.properties['buildername'],
        '--buildnumber', api.properties['buildnumber'],
    ]
    if api.chromium.c.build_dir:
      args.extend(['--build-dir', api.chromium.c.build_dir])
    if 'got_revision_cp' in api.properties:
      args.extend(['--got-revision-cp', api.properties['got_revision_cp']])
    if 'version' in api.properties:
      args.extend(['--version', api.properties['version']])
    if 'git_revision' in api.properties:
      args.extend(['--git-revision', api.properties['git_revision']])

    # Chromium build properties
    if 'got_webrtc_revision' in api.chromium.build_properties:
      args.extend(['--got-webrtc-revision',
          api.chromium.build_properties['got_webrtc_revision']])
    if 'got_v8_revision' in api.chromium.build_properties:
      args.extend(['--got-v8-revision',
          api.chromium.build_properties['got_v8_revision']])

    step_name = '%s Dashboard Upload' % self._perf_dashboard_id
    return api.build.python(
      step_name,
      api.chromium.package_repo_resource(
          'scripts', 'slave', 'upload_perf_dashboard_results.py'),
      args)


def generate_isolated_script(api, chromium_tests_api, mastername, buildername,
                             test_spec, bot_update_step, enable_swarming=False,
                             swarming_dimensions=None,
                             scripts_compile_targets=None):
  # Get the perf id and results url if present.
  bot_config = (chromium_tests_api.builders.get(mastername, {})
      .get('builders', {}).get(buildername, {}))
  perf_id = bot_config.get('perf-id')
  results_url = bot_config.get('results-url')
  for spec in test_spec.get(buildername, {}).get('isolated_scripts', []):
    perf_dashboard_id = spec.get('name', '')
    use_swarming = False
    swarming_ignore_task_failure = False
    swarming_shards = 1
    swarming_dimension_sets = None
    swarming_priority = None
    swarming_expiration = None
    swarming_hard_timeout = None
    swarming_io_timeout = None
    if enable_swarming:
      swarming_spec = spec.get('swarming', {})
      if swarming_spec.get('can_use_on_swarming_builders', False):
        use_swarming = True
        swarming_ignore_task_failure = (
            swarming_spec.get('ignore_task_failure', False))
        swarming_shards = swarming_spec.get('shards', 1)
        swarming_dimension_sets = swarming_spec.get('dimension_sets')
        swarming_priority = swarming_spec.get('priority_adjustment')
        swarming_expiration = swarming_spec.get('expiration')
        swarming_hard_timeout = swarming_spec.get('hard_timeout')
        swarming_io_timeout = swarming_spec.get('io_timeout')
    name = str(spec['name'])
    # The variable substitution and precommit/non-precommit arguments
    # could be supported for the other test types too, but that wasn't
    # desired at the time of this writing.
    args = get_args_for_test(api, chromium_tests_api, spec, bot_update_step)
    target_name = spec['isolate_name']
    # This features is only needed for the cases in which the *_run compile
    # target is needed to generate isolate files that contains dynamically libs.
    # TODO(nednguyen, kbr): Remove this once all the GYP builds are converted
    # to GN.
    override_compile_targets = spec.get('override_compile_targets', None)
    merge = dict(spec.get('merge', {}))
    if merge:
      merge_script = merge.get('script')
      if merge_script:
        if merge_script.startswith('//'):
          merge['script'] = api.path['checkout'].join(
              merge_script[2:].replace('/', api.path.sep))
        else:
          api.python.failing_step(
              'isolated_scripts spec format error',
              textwrap.wrap(textwrap.dedent("""\
                  The isolated_scripts target "%s" contains a custom merge_script "%s"
                  that doesn't match the expected format. Custom merge_script entries
                  should be a path relative to the top-level chromium src directory and
                  should start with "//".
                  """ % (name, merge_script))),
              as_log='details')

    # TODO(tansell): Remove this once custom handling of results is no longer
    # needed.
    results_handler_name = spec.get('results_handler', 'default')
    try:
        results_handler = {
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

    swarming_dimensions = swarming_dimensions or {}
    if use_swarming:
      if swarming_dimension_sets:
        for dimensions in swarming_dimension_sets:
          # Yield potentially multiple invocations of the same test,
          # on different machine configurations.
          new_dimensions = dict(swarming_dimensions)
          new_dimensions.update(dimensions)
          yield SwarmingIsolatedScriptTest(
              name=name, args=args, target_name=target_name,
              shards=swarming_shards, dimensions=new_dimensions,
              override_compile_targets=override_compile_targets,
              ignore_task_failure=swarming_ignore_task_failure,
              priority=swarming_priority, expiration=swarming_expiration,
              hard_timeout=swarming_hard_timeout, perf_id=perf_id,
              results_url=results_url, perf_dashboard_id=perf_dashboard_id,
              io_timeout=swarming_io_timeout,
              waterfall_mastername=mastername,
              waterfall_buildername=buildername,
              merge=merge, results_handler=results_handler)
      else:
        yield SwarmingIsolatedScriptTest(
            name=name, args=args, target_name=target_name,
            shards=swarming_shards, dimensions=swarming_dimensions,
            override_compile_targets=override_compile_targets,
            ignore_task_failure=swarming_ignore_task_failure,
            priority=swarming_priority, expiration=swarming_expiration,
            hard_timeout=swarming_hard_timeout, perf_id=perf_id,
            results_url=results_url, perf_dashboard_id=perf_dashboard_id,
            io_timeout=swarming_io_timeout,
            waterfall_mastername=mastername, waterfall_buildername=buildername,
            merge=merge, results_handler=results_handler)
    else:
      yield LocalIsolatedScriptTest(
          name=name, args=args, target_name=target_name,
          override_compile_targets=override_compile_targets,
          results_handler=results_handler)


class GTestTest(Test):
  def __init__(self, name, args=None, target_name=None, enable_swarming=False,
               swarming_shards=1, swarming_dimensions=None, swarming_tags=None,
               swarming_extra_suffix=None, swarming_priority=None,
               swarming_expiration=None, swarming_hard_timeout=None,
               cipd_packages=None, waterfall_mastername=None,
               waterfall_buildername=None, merge=None,
               **runtest_kwargs):
    super(GTestTest, self).__init__(
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    if enable_swarming:
      self._test = SwarmingGTestTest(
          name, args, target_name, swarming_shards, swarming_dimensions,
          swarming_tags, swarming_extra_suffix, swarming_priority,
          swarming_expiration, swarming_hard_timeout,
          cipd_packages=cipd_packages,
          override_compile_targets=runtest_kwargs.get(
              'override_compile_targets'),
          override_isolate_target=runtest_kwargs.get(
              'override_isolate_target'),
          waterfall_mastername=waterfall_mastername,
          waterfall_buildername=waterfall_buildername,
          merge=merge)
    else:
      self._test = LocalGTestTest(
          name, args, target_name, waterfall_mastername=waterfall_mastername,
          waterfall_buildername=waterfall_buildername,
          **runtest_kwargs)

    self.enable_swarming = enable_swarming

  @Test.test_options.setter
  def test_options(self, value):
    self._test.test_options = value

  @property
  def name(self):
    return self._test.name

  @property
  def uses_local_devices(self):
    # Return True unless this test has swarming enabled.
    return not self.enable_swarming

  def isolate_target(self, api):
    return self._test.isolate_target(api)

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

  def step_metadata(self, api, suffix):
    return self._test.step_metadata(api, suffix)

  @property
  def uses_swarming(self):
    return self._test.uses_swarming

  def pass_fail_counts(self, suffix):
    return self._test.pass_fail_counts(suffix)

  @staticmethod
  def args_from_options(api, original_args, test, **kwargs):
    """Returns a list of command line options for gtest from a test's
    .test_options property

    Args:
      api - The caller api.
      original_args - Any args previously defined.
      test - The test object.
      kwargs - A dictionary to override fields from options.
    Returns:
      a list of command line options for gtest.
    """
    args = []
    options = test.test_options
    test_filter = kwargs.get('override_test_filter', options.test_filter)
    if options.repeat_count and options.repeat_count > 1:
      args.append('--gtest_repeat=%d' % options.repeat_count)
    if test_filter:
      if test.uses_swarming:
        args.append('--gtest_filter=%s' % ':'.join(test_filter))
      else:
        args.append(api.chromium.test_launcher_filter(test_filter))
      # TODO(robertocn): Remove this code, because test launcher supports both
      # flags now.
      for a in original_args:  # pragma: no cover
        if a.startswith('--test-launcher-filter-file'):
          original_args.remove(a)

    if options.retry_limit is not None:
      args.append('--test-launcher-retry-limit=%d' % options.retry_limit)
    if options.run_disabled:
      args.append('--gtest_also_run_disabled_tests')

    return original_args + args


class PythonBasedTest(Test):
  @staticmethod
  def compile_targets(_):
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
        p.step_text += api.test_utils.format_step_text([
          ['unexpected_failures:', r.unexpected_failures.keys()],
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
        'third_party', 'WebKit', 'Tools', 'Scripts', 'run-webkit-tests')
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

  @staticmethod
  def compile_targets(api):
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

  @staticmethod
  def compile_targets(_):  # pragma: no cover
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

  @staticmethod
  def compile_targets(_):  # pragma: no cover
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
        if (hasattr(step_result, 'test_utils') and
            hasattr(step_result.test_utils, 'gtest_results')):
          gtest_results = step_result.test_utils.gtest_results

          failures = gtest_results.failures
          self._test_runs[suffix] = {'valid': True, 'failures': failures}
          nested_step.presentation.step_text += (
              api.test_utils.format_step_text([['failures:', failures]]))

          api.test_results.upload(
              api.json.input(gtest_results.raw),
              test_type=self.name,
              chrome_revision=api.bot_update.last_returned_properties.get(
                  'got_revision_cp', 'x@{#0}'),
              test_results_server='test-results.appspot.com')

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
      # TODO(agrieve): These should be listed as deps for
      #     system_webview_shell_layout_test_apk.
      'additional_compile_targets': [
        'system_webview_apk',
        'android_tools'
      ],
      # TODO(jbudorick): Remove this once it's handled by the generated script.
      'additional_apks': [
        'SystemWebView.apk',
      ],
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
               result_details=False, render_results_dir=None,
               args=None, waterfall_mastername=None,
               waterfall_buildername=None):
    suite_defaults = (
        AndroidInstrumentationTest._DEFAULT_SUITES.get(name)
        or AndroidInstrumentationTest._DEFAULT_SUITES_BY_TARGET.get(name)
        or {})
    if not compile_targets:
      compile_targets = [suite_defaults.get('compile_target', name)]
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
    self._store_tombstones = store_tombstones
    self._result_details = result_details
    self._render_results_dir = render_results_dir
    self._args = args

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
        render_results_dir=self._render_results_dir,
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

  @staticmethod
  def compile_targets(api):
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
        '--full-results-html',    # For the dashboards.
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
      if api.platform.is_win:
        step_result = api.python(
          step_name,
          api.path['checkout'].join('third_party', 'WebKit', 'Tools',
                                    'Scripts', 'run-webkit-tests'),
          args,
          step_test_data=lambda: api.test_utils.test_api.canned_test_output(
              passing=True, minimal=True))
      else:
        step_result = api.chromium.runtest(
          api.path['checkout'].join('third_party', 'WebKit', 'Tools',
                                    'Scripts', 'run-webkit-tests'),
          args,
          name=step_name,
          python_mode=True,
          # TODO(phajdan.jr): Clean up the runtest.py mess.
          disable_src_side_runtest_py=True,
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

  def has_valid_results(self, api, suffix):
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

  @staticmethod
  def compile_targets(_):
    return ['mini_installer', 'next_version_mini_installer']

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


class WebViewCTSTest(Test):

  # TODO(yolandyan): create a generator and move specifications to src/
  def __init__(self, platform='L'):
    super(WebViewCTSTest, self).__init__()
    self._platform = platform

  @property
  def name(self):  # pragma: no cover
    return 'WebView CTS: %s' % self._platform

  @property
  def uses_local_devices(self):
    return True

  @staticmethod
  def compile_targets(api):
    return ['system_webview_apk']

  def run(self, api, suffix):
    api.chromium_android.adb_install_apk(
        api.chromium_android.apk_path('SystemWebView.apk'))
    api.chromium_android.run_webview_cts(android_platform=self._platform)


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

  @staticmethod
  def compile_targets(api):
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

  @staticmethod
  def compile_targets(api):
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
  def __init__(self, name, args, perf_id, **runtest_kwargs):
    assert perf_id
    # TODO(kjellander): See if it's possible to rely on the build spec
    # properties 'perf-id' and 'results-url' as set in the
    # chromium_tests/chromium_perf.py. For now, set these to get an exact
    # match of our current expectations.
    runtest_kwargs['perf_id'] = perf_id
    runtest_kwargs['results_url'] = RESULTS_URL

    # TODO(kjellander): See if perf_dashboard_id is still needed.
    runtest_kwargs['perf_dashboard_id'] = name
    runtest_kwargs['annotate'] = 'graphing'
    super(WebRTCPerfTest, self).__init__(name, args, **runtest_kwargs)

  def run(self, api, suffix):
    webrtc_subtree_git_hash = api.bot_update.last_returned_properties.get(
        'got_webrtc_revision', 'deadbeef')
    self._runtest_kwargs['perf_config'] = {
        # TODO(kjellander: Change to r_webrtc_git after crbug.com/611808.
        'r_webrtc_subtree_git': webrtc_subtree_git_hash,
        'a_default_rev': 'r_webrtc_subtree_git',
    }
    LocalGTestTest.run(self, api, suffix)


GOMA_TESTS = [
  GTestTest('base_unittests'),
  GTestTest('content_unittests'),
]
