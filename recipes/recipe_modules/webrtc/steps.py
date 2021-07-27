# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools
import json
import os
import re
import sys

from recipe_engine import recipe_api
from recipe_engine.engine_types import freeze

THIS_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(THIS_DIR)))


# adb path relative to out dir (e.g. out/Release)
ADB_PATH = '../../third_party/android_sdk/public/platform-tools/adb'

ANDROID_CIPD_PACKAGES = [
    ("bin",
     "infra/tools/luci/logdog/butler/${platform}",
     "git_revision:ff387eadf445b24c935f1cf7d6ddd279f8a6b04c",
    )
]


def generate_tests(phase, bot, platform_name, build_out_dir, checkout_path,
                   is_tryserver):
  """Generate a list of tests to run on a bot.

  Args:
    phase: string to distinguish the phase of a builder (used only for
      more_configs builders).
    bot: string with the name of the bot (e.g. 'linux_compile_rel').
    platform: String representing the platform on which tests
      will run. Possible values are: "linux", "mac", "win".
    build_out_dir: the out/ dir of the builder.
    checkout_path: the path to the checkout on the builder.
    is_tryserver: True if the tests needs to be generated for a tryserver.

  Returns:
    A list of steps.WebRtcIsolatedGtest to compile and run on a bot.
  """
  assert platform_name in ('linux', 'mac', 'win')
  tests = []
  test_suite = bot.test_suite

  if test_suite in ('webrtc', 'webrtc_and_baremetal'):
    tests += [
        SwarmingDesktopTest('audio_decoder_unittests'),
        SwarmingDesktopTest('common_audio_unittests'),
        SwarmingDesktopTest('common_video_unittests'),
        SwarmingDesktopTest('dcsctp_unittests'),
        SwarmingDesktopTest('low_bandwidth_audio_test'),
        SwarmingDesktopTest('modules_tests', shards=2),
        SwarmingDesktopTest('modules_unittests', shards=6),
        SwarmingDesktopTest('peerconnection_unittests', shards=4),
        SwarmingDesktopTest('rtc_media_unittests'),
        SwarmingDesktopTest('rtc_pc_unittests'),
        SwarmingDesktopTest('rtc_stats_unittests'),
        SwarmingDesktopTest('rtc_unittests', shards=6),
        SwarmingDesktopTest('slow_tests'),
        SwarmingDesktopTest('system_wrappers_unittests'),
        SwarmingDesktopTest('test_support_unittests'),
        SwarmingDesktopTest('tools_unittests'),
        SwarmingDesktopTest('video_engine_tests', shards=4),
        SwarmingDesktopTest('voip_unittests'),
        SwarmingDesktopTest('webrtc_nonparallel_tests'),
    ]

  if test_suite == 'webrtc_and_baremetal':
    baremetal_test = functools.partial(
        SwarmingDesktopTest,
        dimensions=bot.config['baremetal_swarming_dimensions'])

    tests.append(baremetal_test('video_capture_tests'))

    # Cover tests only running on perf tests on our trybots:
    if is_tryserver:
      if platform_name == 'linux':
        tests.append(baremetal_test('isac_fix_test'))

      is_win_clang = (
          platform_name == 'win' and
          'clang' in bot.recipe_config['chromium_config'])

      # TODO(kjellander): Enable on Mac when bugs.webrtc.org/7322 is fixed.
      # TODO(oprypin): Enable on MSVC when bugs.webrtc.org/9290 is fixed.
      if platform_name == 'linux' or is_win_clang:
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
                '--test_artifacts_dir=${ISOLATED_OUTDIR}',
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
            'webrtc_perf_tests',
            args=[
                '--save_worst_frame',
                '--nologs',
            ]))

  if test_suite == 'android':
    tests += [
        SwarmingAndroidTest('AppRTCMobile_test_apk'),
        SwarmingAndroidTest('android_instrumentation_test_apk'),
        SwarmingAndroidTest('audio_decoder_unittests'),
        SwarmingAndroidTest('common_audio_unittests'),
        SwarmingAndroidTest('common_video_unittests'),
        SwarmingAndroidTest('dcsctp_unittests'),
        SwarmingAndroidTest('modules_tests', shards=2),
        SwarmingAndroidTest('modules_unittests', shards=6),
        SwarmingAndroidTest('peerconnection_unittests', shards=4),
        SwarmingAndroidTest('rtc_stats_unittests'),
        SwarmingAndroidTest('rtc_unittests', shards=6),
        SwarmingAndroidTest('system_wrappers_unittests'),
        SwarmingAndroidTest('test_support_unittests'),
        SwarmingAndroidTest('tools_unittests'),
        SwarmingAndroidTest('video_engine_tests', shards=4),
        SwarmingAndroidTest('voip_unittests'),
        SwarmingAndroidTest('webrtc_nonparallel_tests'),
        AndroidJunitTest('android_examples_junit_tests'),
        AndroidJunitTest('android_sdk_junit_tests'),
    ]

    if bot.should_test_android_studio_project_generation:
      tests.append(
          PythonTest(
              test='gradle_project_test',
              script=checkout_path.join('examples', 'androidtests',
                                        'gradle_project_test.py'),
              args=[build_out_dir],
              env={'GOMA_DISABLED': True}))

    if is_tryserver:
      tests.append(
          SwarmingAndroidTest(
              'webrtc_perf_tests',
              args=[
                  '--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/',
                  '--nologs',
              ]))

  if test_suite == 'ios':
    # TODO(bugs.webrtc.org/12244): Some tests are skipped on iOS simulator
    # platforms because they fail or they are flaky.
    if bot.builder not in [
        'iOS64 Sim Debug (iOS 14.0)',
        'ios_sim_x64_dbg_ios14',
        'iOS64 Sim Debug (iOS 13)',
        'ios_sim_x64_dbg_ios13',
        'iOS64 Sim Debug (iOS 12)',
        'ios_sim_x64_dbg_ios12',
    ]:
      tests += [
          IosTest(
              'apprtcmobile_tests', xctest=True, xcode_parallelization=True),
          IosTest('sdk_unittests', xctest=True, xcode_parallelization=True)
      ]

    tests += [
        IosTest(
            'sdk_framework_unittests', xctest=True, xcode_parallelization=True),
        IosTest('audio_decoder_unittests', xctest=True),
        IosTest('common_audio_unittests', xctest=True),
        IosTest('common_video_unittests', xctest=True),
        IosTest('dcsctp_unittests', xctest=True),
        IosTest('modules_tests', xctest=True),
        IosTest('modules_unittests', xctest=True),
        IosTest('rtc_media_unittests', xctest=True),
        IosTest('rtc_pc_unittests', xctest=True),
        IosTest('rtc_stats_unittests', xctest=True),
        IosTest('rtc_unittests', xctest=True),
        IosTest('system_wrappers_unittests', xctest=True),
        IosTest('test_support_unittests', xctest=True),
        IosTest('tools_unittests', xctest=True),
        IosTest('video_capture_tests', xctest=True),
        IosTest('video_engine_tests', xctest=True),
        IosTest('voip_unittests', xctest=True),
        IosTest('webrtc_nonparallel_tests', xctest=True),
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
        IosTest(
            'webrtc_perf_tests',
            args=[
                '--write_perf_output_on_ios',
                '--nologs',
            ]),
    ]

  if test_suite == 'more_configs':
    if 'no_sctp' in phase:
      tests.append(SwarmingDesktopTest('peerconnection_unittests'))

  return tests


class WebRtcIsolatedGtest(object):
  """Triggers an isolated task to run a GTest binary, and collects the results.

  This class is based off Chromium's SwarmingIsolatedScriptTest, but strips out
  the parts we don't need.
  """

  def __init__(self,
               name,
               dimensions=None,
               args=None,
               shards=1,
               cipd_packages=None,
               idempotent=None,
               result_handlers=None):
    """Constructs an instance of WebRtcIsolatedGtest.

    Args:
      name: Displayed name of the test.
      dimensions (dict of str: str): Requested dimensions of the test.
      args: List of arguments to pass as "Extra Args" to the swarming task.
          These are passed to whatever runs first in the swarming job, like
          build/android/test_runner.py on Android or gtest-parallel on Desktop.
          (these often pass through args to the test binary).
      shards: Number of shards to trigger.
      cipd_packages: [(str, str, str)] list of 3-tuples containing cipd
          package root, package name, and package version.
      idempotent: Whether to mark the task as idempotent. A value of None will
          cause chromium_swarming/api.py to apply its default_idempotent val.
      result_handlers: a list of callbacks that take (api, step_result,
          has_valid_results) and take some action to it (typically writing
          something into the step result).
    """
    self._name = name
    self._dimensions = dimensions or {}
    self._args = args or []
    self._shards = shards
    self._cipd_packages = cipd_packages
    self._idempotent = idempotent
    self._result_handlers = result_handlers or []
    self._raw_cmd = []
    self._relative_cwd = None

    self._task = None
    self._has_collected = False

  @property
  def isolate_target(self):
    return self._name

  @property
  def name(self):
    return self._name

  @property
  def step_name(self):
    return self._name

  @property
  def raw_cmd(self):  # pragma: no cover
    return self._raw_cmd

  @raw_cmd.setter
  def raw_cmd(self, value):
    self._raw_cmd = value

  @property
  def relative_cwd(self):  # pragma: no cover
    return self._relative_cwd

  @relative_cwd.setter
  def relative_cwd(self, value):
    self._relative_cwd = value

  @property
  def runs_on_swarming(self):
    return True

  def pre_run(self, api):
    """Launches the test on Swarming."""
    assert self._task is None, (
        'Test %s was already triggered' % self.step_name)  # pragma no cover

    # *.isolated may be missing if *_run target is misconfigured.
    task_input = api.isolate.isolated_tests.get(self.isolate_target)
    if not task_input:  # pragma no cover
      return api.python.failing_step(
          '[error] %s' % self.step_name,
          '*.isolated file for target %s is missing' % self.isolate_target)

    self._task = self.create_task(api, task_input)

    return api.chromium_swarming.trigger_task(self._task)

  @recipe_api.composite_step
  def run(self, api):
    """Waits for launched test to finish and collects the results."""
    assert not self._has_collected, (  # pragma no cover
        'Results of %s were already collected' % self.step_name)
    self._has_collected = True

    step_result, has_valid_results = api.chromium_swarming.collect_task(
        self._task, allow_missing_json=True)

    for handler in self._result_handlers:
      handler(api, step_result, has_valid_results)

    return step_result

  def create_task(self, api, task_input):
    task = api.chromium_swarming.task(
        name=self.step_name,
        raw_cmd=self._raw_cmd,
        relative_cwd=self._relative_cwd,
        cas_input_root=task_input)

    task_slice = task.request[0]
    task.request = task.request.with_slice(0, task_slice)

    self._apply_swarming_task_config(task, api)
    return task


  def _apply_swarming_task_config(self, task, api):
    """Applies shared configuration for swarming tasks.
    """
    task.shards = self._shards
    task.shard_indices = range(task.shards)
    task.build_properties = api.chromium.build_properties

    task_slice = task.request[0]

    if self._idempotent is not None:
      task_slice = task_slice.with_idempotent(self._idempotent)

    ensure_file = task_slice.cipd_ensure_file
    if self._cipd_packages:
      for package in self._cipd_packages:
        ensure_file.add_package(package[1], package[2], package[0])
    task_slice = task_slice.with_cipd_ensure_file(ensure_file)

    task_dimensions = task_slice.dimensions
    for k, v in self._dimensions.iteritems():
      task_dimensions[k] = v

    # Set default value for os.
    if 'os' not in task_dimensions:
      task_dimensions['os'] = api.chromium_swarming.prefered_os_dimension(
          api.platform.name)  # pragma no cover

    task_slice = task_slice.with_dimensions(**task_dimensions)

    task.extra_args.extend(self._args)

    task.request = (
        task.request.with_slice(0, task_slice).with_name(self.step_name))
    return task


def InvalidResultsHandler(api, step_result, has_valid_results):
  if (api.step.active_result.retcode == 0 and not has_valid_results):
    # This failure won't be caught automatically. Need to manually
    # raise it as a step failure.
    raise api.step.StepFailure(
        api.test_utils.INVALID_RESULTS_MAGIC)  # pragma no cover


def LogcatHandler(api, step_result, has_valid_results):
  del has_valid_results
  task_output_dir = api.step.active_result.raw_io.output_dir
  result = ""
  for file_name, contents in task_output_dir.iteritems():
    if file_name.endswith('logcats'):  # pragma: no cover
      result += contents

  step_result.presentation.logs['logcats'] = result.splitlines()


def SwarmingDesktopTest(name, **kwargs):
  return WebRtcIsolatedGtest(
      name, result_handlers=[InvalidResultsHandler], **kwargs)


def SwarmingPerfTest(name, args=None, **kwargs):
  def UploadToPerfDashboardHandler(api, step_result, has_valid_results):
    del has_valid_results

    api.webrtc.upload_to_perf_dashboard(name, step_result)

  handlers = [InvalidResultsHandler, UploadToPerfDashboardHandler]

  args = list(args or [])
  # This flag is translated to --isolated_script_test_perf_output in
  # gtest-parallel_wrapper.py and flags_compatibility.py. Why not pass the right
  # flag right away? Unfortunately Chromium's android/test_runner.py does
  # magical treatment of the dashed version of the flag, and we need that to
  # get a writable out dir on Android, so we must have this translation step.
  args.extend([
      ('--isolated-script-test-perf-output='
       '${ISOLATED_OUTDIR}/perftest-output.pb'),
  ])

  # Perf tests are marked as not idempotent, which means they're re-run if they
  # did not change this build. This will give the dashboard some more variance
  # data to work with."""
  return WebRtcIsolatedGtest(
      name,
      args=args,
      cipd_packages=ANDROID_CIPD_PACKAGES,
      shards=1,
      idempotent=False,
      result_handlers=handlers,
      **kwargs)


def SwarmingAndroidTest(name, **kwargs):
  return WebRtcIsolatedGtest(
      name,
      cipd_packages=ANDROID_CIPD_PACKAGES,
      result_handlers=[InvalidResultsHandler, LogcatHandler],
      **kwargs)


def SwarmingAndroidPerfTest(name, args=None, **kwargs):
  def UploadToPerfDashboardHandler(api, step_result, has_valid_results):
    del has_valid_results

    api.webrtc.upload_to_perf_dashboard(name, step_result)

  handlers = [
      InvalidResultsHandler, LogcatHandler, UploadToPerfDashboardHandler
  ]

  args = list(args or [])

  # See SwarmingDesktopPerfTest for more details why we pass this rather than
  # --isolated_script_test_perf_output.
  args.extend([
      ('--isolated-script-test-perf-output='
       '${ISOLATED_OUTDIR}/perftest-output.pb'),
  ])

  return WebRtcIsolatedGtest(
      name,
      args=args,
      shards=1,
      idempotent=False,
      result_handlers=handlers,
      **kwargs)


class Test(object):

  def __init__(self, test, name=None):
    self._test = test
    self._name = name or test

  def pre_run(self, api):
    del api
    return []

  def run(self, api):  # pragma: no cover
    del api
    return []

  @property
  def runs_on_swarming(self):  # pragma: no cover
    return False


class PythonTest(Test):

  def __init__(self, test, script, args, env):
    super(PythonTest, self).__init__(test)
    self._script = script
    self._args = args
    self._env = env or {}
    self._name = test

  @property
  def name(self):
    return self._name

  def run(self, api):
    with api.depot_tools.on_path():
      with api.context(env=self._env):
        return api.python(self._test, self._script, self._args)

  @property
  def runs_on_swarming(self):
    return False


class AndroidJunitTest(Test):
  """Runs an Android Junit test."""

  @property
  def name(self):
    return self._name

  def run(self, api):
    return api.chromium_android.run_java_unit_test_suite(self._name)

  @property
  def runs_on_swarming(self):
    return False


class IosTest(object):
  """A fake shell of an iOS test. It is only read by apply_ios_config."""

  def __init__(self, name, args=None, xctest=False,
               xcode_parallelization=False):
    self._name = name
    self.config = {'app': name}
    if args:
      self.config['test args'] = args
    if xctest:
      self.config['xctest'] = True
      # WebRTC iOS tests are in the process of being migrated to XCTest so
      # there is no need to have a flag to handle how they run.
      if 'test args' not in self.config:
        self.config['test args'] = []
      self.config['test args'].append(
          '--undefok="enable-run-ios-unittests-with-xctest"')
    if xcode_parallelization:
      # TODO(crbug.com/1006881): "xctest" indicates how to run the targets but
      # not how to parse test outputs since recent iOS test runner changes.
      # This arg is needed for outputs to be parsed correctly.
      self.config['xcode parallelization'] = True

  @property
  def name(self):
    return self._name

  @property
  def runs_on_swarming(self):  # pragma: no cover
    # Even if this sounds unrelated from Swarming, this is just a shell for an
    # iOS test, the real test that will run is an instance of Chromium's
    # SwarmingIosTest.
    return True
