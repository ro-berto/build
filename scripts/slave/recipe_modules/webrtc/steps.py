# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools
import json
import os
import re
import sys

from recipe_engine.types import freeze
from recipe_engine import recipe_api

THIS_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(THIS_DIR)))

from RECIPE_MODULES.build.chromium_tests import steps


# adb path relative to out dir (e.g. out/Release)
ADB_PATH = '../../third_party/android_sdk/public/platform-tools/adb'

ANDROID_CIPD_PACKAGES = [
    ("bin",
     "infra/tools/luci/logdog/butler/${platform}",
     "git_revision:ff387eadf445b24c935f1cf7d6ddd279f8a6b04c",
    )
]


def _create_test_run_results_dictionary(valid):
  """Returns the dictionary for an invalid test run.

  Args:
    valid: A boolean.
  """
  return {
    'valid': valid,
    'failures': [],
    'total_tests_ran': 0,
    'pass_fail_counts': {},
    'findit_notrun': set()
  }

def generate_tests(api, phase, bot):
  tests = []
  build_out_dir = api.path['checkout'].join(
      'out', api.chromium.c.build_config_fs)
  test_suite = bot.test_suite

  if test_suite in ('webrtc', 'webrtc_and_baremetal'):
    tests += [
        WebRtcIsolatedGtest('audio_decoder_unittests'),
        WebRtcIsolatedGtest('common_audio_unittests'),
        WebRtcIsolatedGtest('common_video_unittests'),
        WebRtcIsolatedGtest('low_bandwidth_audio_test'),
        WebRtcIsolatedGtest('modules_tests', shards=2),
        WebRtcIsolatedGtest('modules_unittests', shards=6),
        WebRtcIsolatedGtest('peerconnection_unittests', shards=4),
        WebRtcIsolatedGtest('rtc_media_unittests'),
        WebRtcIsolatedGtest('rtc_pc_unittests'),
        WebRtcIsolatedGtest('rtc_stats_unittests'),
        WebRtcIsolatedGtest('rtc_unittests', shards=6),
        WebRtcIsolatedGtest('slow_tests'),
        WebRtcIsolatedGtest('system_wrappers_unittests'),
        WebRtcIsolatedGtest('test_support_unittests'),
        WebRtcIsolatedGtest('tools_unittests'),
        WebRtcIsolatedGtest('video_engine_tests', shards=4),
        WebRtcIsolatedGtest('webrtc_nonparallel_tests'),
    ]

  if test_suite == 'webrtc_and_baremetal':
    baremetal_test = functools.partial(
        WebRtcIsolatedGtest,
        dimensions=bot.config['baremetal_swarming_dimensions'])

    tests.append(baremetal_test('video_capture_tests'))

    # Cover tests only running on perf tests on our trybots:
    if api.tryserver.is_tryserver:
      if api.platform.is_linux:
        tests.append(baremetal_test('isac_fix_test'))

      is_win_clang = (api.platform.is_win and
                      'clang' in bot.recipe_config['chromium_config'])

      # TODO(kjellander): Enable on Mac when bugs.webrtc.org/7322 is fixed.
      # TODO(oprypin): Enable on MSVC when bugs.webrtc.org/9290 is fixed.
      if api.platform.is_linux or is_win_clang:
        tests.append(baremetal_test('webrtc_perf_tests', args=[
            '--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/',
            '--nologs',
        ]))

  if test_suite == 'desktop_perf_swarming':
    tests += [
        SwarmingPerfTest('isac_fix_test'),
        SwarmingPerfTest('low_bandwidth_audio_perf_test'),
        SwarmingPerfTest(
            'webrtc_perf_tests',
            args=[
                '--test_artifacts_dir',
                '${ISOLATED_OUTDIR}',
                '--save_worst_frame',
                '--nologs',
            ]),
    ]

  if test_suite == 'android_perf_swarming':
    tests.append(
        SwarmingAndroidPerfTest(
            'low_bandwidth_audio_perf_test',
            args=[
                '--android',
                '--adb-path',
                ADB_PATH,
            ]))
    tests.append(
        SwarmingAndroidPerfTest(
            'webrtc_perf_tests', args=[
                '--save_worst_frame',
                '--nologs',
            ]))
    assert all([
        isinstance(t, SwarmingAndroidPerfTest) for t in tests
    ]), ('Watch out. Android perf tasks are very picky about flags, so you '
         'need Android-specific tasks here.')

  if test_suite == 'android':
    tests += [
        AndroidTest('AppRTCMobile_test_apk'),
        AndroidTest('android_instrumentation_test_apk'),
        AndroidTest('audio_decoder_unittests'),
        AndroidTest('common_audio_unittests'),
        AndroidTest('common_video_unittests'),
        AndroidTest('modules_tests', shards=2),
        AndroidTest('modules_unittests', shards=6),
        AndroidTest('peerconnection_unittests', shards=4),
        AndroidTest('rtc_stats_unittests'),
        AndroidTest('rtc_unittests', shards=6),
        AndroidTest('system_wrappers_unittests'),
        AndroidTest('test_support_unittests'),
        AndroidTest('tools_unittests'),
        AndroidTest('video_engine_tests', shards=4),
        AndroidTest('webrtc_nonparallel_tests'),
        AndroidJunitTest('android_examples_junit_tests'),
        AndroidJunitTest('android_sdk_junit_tests'),
    ]

    if bot.should_test_android_studio_project_generation:
      tests.append(PythonTest(
          test='gradle_project_test',
          script=str(api.path['checkout'].join('examples',  'androidtests',
                                               'gradle_project_test.py')),
          args=[build_out_dir],
          env={'GOMA_DISABLED': True}))

    if api.tryserver.is_tryserver:
      tests.append(AndroidTest('webrtc_perf_tests', args=[
          '--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/',
          '--nologs',
      ]))

  if test_suite == 'ios':
    tests += [
        IosTest('apprtcmobile_tests', xctest=True),
        IosTest('sdk_unittests', xctest=True),
        IosTest('sdk_framework_unittests', xctest=True),
        IosTest('audio_decoder_unittests'),
        IosTest('common_audio_unittests'),
        IosTest('common_video_unittests'),
        IosTest('modules_tests'),
        IosTest('modules_unittests'),
        IosTest('rtc_media_unittests'),
        IosTest('rtc_pc_unittests'),
        IosTest('rtc_stats_unittests'),
        IosTest('rtc_unittests'),
        IosTest('system_wrappers_unittests'),
        IosTest('test_support_unittests'),
        IosTest('tools_unittests'),
        IosTest('video_capture_tests'),
        IosTest('video_engine_tests'),
        IosTest('webrtc_nonparallel_tests'),
    ]

  if test_suite == 'ios_device':
    tests += [
        IosTest('common_audio_unittests'),
        IosTest('common_video_unittests'),
        IosTest('modules_tests'),
        IosTest('modules_unittests'),
        IosTest('rtc_pc_unittests'),
        IosTest('rtc_stats_unittests'),
        IosTest('system_wrappers_unittests'),
        IosTest('test_support_unittests'),
        IosTest('tools_unittests'),
        IosTest('video_capture_tests'),
        IosTest('video_engine_tests'),
    ]

  if test_suite == 'ios_perf':
    tests += [
        IosTest('webrtc_perf_tests', args=[
            '--save_chartjson_result',
            '--nologs',
        ]),
    ]

  if test_suite == 'more_configs':
    if 'no_sctp' in phase:
      tests.append(WebRtcIsolatedGtest('peerconnection_unittests'))

  return tests


class WebRtcIsolatedGtest(object):
  """Triggers an isolated task to run a GTest binary, and collects the results.

  This class is based off Chromium's SwarmingIsolatedScriptTest, but strips out
  the parts we don't need.
  """

  def __init__(self, name, args=None, shards=1, dimensions=None):
    self._name = name
    self._args = args or []
    self._shards = shards
    self._task = None
    self._has_collected = False
    self._dimensions = dimensions

  @property
  def isolate_target(self):
    return self._name

  @property
  def name(self):
    return self._name

  @property
  def step_name(self):
    return self._name

  def pre_run(self, api, suffix):
    """Launches the test on Swarming."""
    del suffix
    assert self._task is None, (
        'Test %s was already triggered' % self.step_name)  # pragma no cover

    # *.isolated may be missing if *_run target is misconfigured.
    isolated = api.isolate.isolated_tests.get(self.isolate_target)
    if not isolated:  # pragma no cover
      return api.python.failing_step(
          '[error] %s' % self.step_name,
          '*.isolated file for target %s is missing' % self.isolate_target)

    self._task = self.create_task(api, isolated)

    return api.chromium_swarming.trigger_task(self._task)

  @recipe_api.composite_step
  def run(self, api, suffix):
    """Waits for launched test to finish and collects the results."""
    del suffix
    assert not self._has_collected, (  # pragma no cover
        'Results of %s were already collected' % self.step_name)

    self._has_collected = True

    step_result, has_valid_results = api.chromium_swarming.collect_task(
        self._task, allow_missing_json=True)

    if (api.step.active_result.retcode == 0 and not has_valid_results):
      # This failure won't be caught automatically. Need to manually
      # raise it as a step failure.
      raise api.step.StepFailure(
          api.test_utils.INVALID_RESULTS_MAGIC)  # pragma no cover

    return step_result

  def create_task(self, api, isolated):
    task = api.chromium_swarming.task(name=self.step_name)

    task_slice = task.request[0]
    task.request = task.request.with_slice(0, task_slice)

    self._apply_swarming_task_config(task, api, isolated)
    return task

  def _apply_swarming_task_config(self, task, api, isolated):
    """Applies shared configuration for swarming tasks.
    """
    task.shards = self._shards
    task.shard_indices = range(task.shards)
    task.build_properties = api.chromium.build_properties

    task_slice = task.request[0]
    ensure_file = task_slice.cipd_ensure_file

    task_slice = (
        task_slice.with_cipd_ensure_file(ensure_file).with_isolated(isolated))

    task_dimensions = task_slice.dimensions
    # Add custom dimensions.
    if self._dimensions:
      for k, v in self._dimensions.iteritems():
        task_dimensions[k] = v

    # Set default value.
    if 'os' not in task_dimensions:
      task_dimensions['os'] = api.chromium_swarming.prefered_os_dimension(
          api.platform.name)  # pragma no cover

    task_slice = task_slice.with_dimensions(**task_dimensions)

    task.extra_args.extend(self._args)

    task.request = (
        task.request.with_slice(0, task_slice).with_name(self.step_name))
    return task


def _MergeFiles(output_dir, suffix):
  result = ""
  for file_name, contents in output_dir.iteritems():
    if file_name.endswith(suffix): # pragma: no cover
      result += contents
  return result


class Test(object):
  def __init__(self, test, name=None):
    self._test = test
    self._name = name or test

  def pre_run(self, api, suffix): # pylint: disable=unused-argument
    return []

  def run(self, api, suffix): # pragma: no cover pylint: disable=unused-argument
    return []


class PythonTest(Test):
  def __init__(self, test, script, args, env):
    super(PythonTest, self).__init__(test)
    self._script = script
    self._args = args
    self._env = env or {}

  def run(self, api, suffix):
    with api.depot_tools.on_path():
      with api.context(env=self._env):
        return api.python(self._test, self._script, self._args)


class AndroidTest(steps.SwarmingGTestTest):

  def __init__(self, test, **kwargs):
    super(AndroidTest, self).__init__(test,
                                      cipd_packages=ANDROID_CIPD_PACKAGES,
                                      **kwargs)

  def validate_task_results(self, api, step_result):
    valid = super(AndroidTest, self).validate_task_results(api, step_result)

    task_output_dir = api.step.active_result.raw_io.output_dir
    logcats = _MergeFiles(task_output_dir, 'logcats')
    step_result.presentation.logs['logcats'] = logcats.splitlines()

    return _create_test_run_results_dictionary(valid)



class SwarmingAndroidPerfTest(steps.SwarmingTest):
  """Custom Android perf test runner for WebRTC.

  We don't want to use Chromium's process_perf_results.py or merge scripts, so
  we use this class to hook in our own code.

  This class isn't a GTest-based runner like for the normal tests. This is
  because WebRTC is the only team doing C++ perf tests on Android. We need this
  to be a basic swarming test because android_test_runner.py can't handle the
  --isolated-script-test-output flag that is passed to swarmed isolated tests
  (note, this is NOT the same as isolated-script-test-perf-output!), and the
  swarmed GTest class does not have the capability to do perf uploads.
  """

  def __init__(self, test, args=None, shards=1, cipd_packages=None,
               idempotent=False, **kwargs):
    super(SwarmingAndroidPerfTest, self).__init__(test, **kwargs)
    args = list(args or [])
    args.extend([
        '--isolated-script-test-perf-output',
        '${ISOLATED_OUTDIR}/perftest-output.json',
    ])
    self._args = args
    self._shards = shards
    self._idempotent = idempotent
    if cipd_packages is None:
      cipd_packages = ANDROID_CIPD_PACKAGES
    self._cipd_packages = cipd_packages

  def create_task(self, api, suffix, isolated_hash):
    return api.chromium_swarming.task(
        name=self.step_name(suffix),
        isolated=isolated_hash,
        shards=self._shards,
        cipd_packages=self._cipd_packages,
        idempotent=self._idempotent,
        extra_args=self._args,
        build_properties=api.chromium.build_properties)

  @recipe_api.composite_step
  def run(self, api, suffix):
    """Waits for launched test to finish and collects the results."""
    # TODO(phoglund); upstream allow_missing_json; that's the only thing we
    # change from the base algorithm. Or, simplify this class to reduce
    # duplication.
    assert suffix not in self._test_runs, (
        'Results of %s were already collected' % self.step_name(suffix))

    # Emit error if test wasn't triggered. This happens if *.isolated is not
    # found. (The build is already red by this moment anyway).
    if suffix not in self._tasks:  # pragma: no cover
      return api.python.failing_step(
          '[collect error] %s' % self.step_name(suffix),
          '%s wasn\'t triggered' % self.target_name)

    step_result, has_valid_results = api.chromium_swarming.collect_task(
        self._tasks[suffix], allow_missing_json=True)
    self._suffix_step_name_map[suffix] = step_result.step['name']

    step_result.presentation.logs['step_metadata'] = (json.dumps(
        self.step_metadata(suffix), sort_keys=True, indent=2)).splitlines()

    # TODO(martiniss): Consider moving this into some sort of base
    # validate_task_results implementation.
    results = self.validate_task_results(api, step_result)
    if not has_valid_results:
      results['valid'] = False  # pragma: no cover

    self.update_test_run(api, suffix, results)
    return step_result

  def validate_task_results(self, api, step_result):
    task_output_dir = step_result.raw_io.output_dir
    logcats = _MergeFiles(task_output_dir, 'logcats')
    step_result.presentation.logs['logcats'] = logcats.splitlines()

    api.webrtc.upload_to_perf_dashboard(self.name, step_result)

    # There currently exists no validation logic for the results generated by
    # swarming android perf tests. This should be fixed.
    return _create_test_run_results_dictionary(True)

  def compile_targets(self): # pragma: no cover
    return []


class SwarmingPerfTest(steps.SwarmingIsolatedScriptTest):
  """Custom swarmed test runner for WebRTC.

  We don't want to use Chromium's process_perf_results.py or merge scripts, so
  we use this class to hook in our own code.
  """

  def __init__(self, name, *args, **kwargs):
    # Perf tests are not idempotent, because for almost all tests the binary
    # will not return the exact same perf result each time. We want to get those
    # results so the dashboard can properly determine the variance of the test.
    kwargs.setdefault('idempotent', False)
    super(SwarmingPerfTest, self).__init__(name, *args, **kwargs)

  def validate_task_results(self, api, step_result):
    valid = super(SwarmingPerfTest, self).validate_task_results(
        api, step_result)

    api.webrtc.upload_to_perf_dashboard(self.name, step_result)

    return _create_test_run_results_dictionary(valid)


class AndroidJunitTest(Test):
  """Runs an Android Junit test."""

  def run(self, api, suffix):
    return api.chromium_android.run_java_unit_test_suite(self._name)


class IosTest(object):
  """A fake shell of an iOS test. It is only read by apply_ios_config."""
  def __init__(self, name, args=None, xctest=False):
    self._name = name
    self.config = {'app': name}
    if args:
      self.config['test args'] = args
    if xctest:
      self.config['xctest'] = True

  @property
  def name(self):
    return self._name
