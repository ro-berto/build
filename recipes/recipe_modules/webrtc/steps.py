# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import attr
import functools
import json
import os
import re
import sys

from recipe_engine import recipe_api
from recipe_engine.engine_types import freeze
from RECIPE_MODULES.build import chromium_swarming
from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB

THIS_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(THIS_DIR)))


# adb path relative to out dir (e.g. out/Release)
ADB_PATH = '../../third_party/android_sdk/public/platform-tools/adb'

ANDROID_CIPD_PACKAGES = [
    chromium_swarming.CipdPackage.create(
        name='infra/tools/luci/logdog/butler/${platform}',
        version='git_revision:ff387eadf445b24c935f1cf7d6ddd279f8a6b04c',
        root='bin',
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
    tests.append(SwarmingDesktopTest('audio_decoder_unittests'))
    tests.append(SwarmingDesktopTest('common_audio_unittests'))
    tests.append(SwarmingDesktopTest('common_video_unittests'))
    tests.append(SwarmingDesktopTest('dcsctp_unittests'))
    tests.append(SwarmingDesktopTest('low_bandwidth_audio_test'))
    tests.append(SwarmingDesktopTest('modules_tests', shards=2))
    tests.append(SwarmingDesktopTest('modules_unittests', shards=6))
    tests.append(SwarmingDesktopTest('peerconnection_unittests', shards=4))
    tests.append(SwarmingDesktopTest('rtc_media_unittests'))
    tests.append(SwarmingDesktopTest('rtc_pc_unittests'))
    tests.append(SwarmingDesktopTest('rtc_stats_unittests'))
    tests.append(SwarmingDesktopTest('rtc_unittests', shards=6))
    tests.append(SwarmingDesktopTest('system_wrappers_unittests'))
    tests.append(SwarmingDesktopTest('test_support_unittests'))
    tests.append(SwarmingDesktopTest('tools_unittests'))
    tests.append(SwarmingDesktopTest('video_engine_tests', shards=4))
    tests.append(SwarmingDesktopTest('voip_unittests'))
    tests.append(SwarmingDesktopTest('webrtc_nonparallel_tests'))

  if test_suite == 'webrtc_and_baremetal':
    baremetal_test = functools.partial(
        SwarmingDesktopTest,
        dimensions=bot.config['baremetal_swarming_dimensions'])

    tests.append(baremetal_test('video_capture_tests'))

    # Cover tests only running on perf tests on our trybots:
    if is_tryserver:
      tests.append(
          baremetal_test(
              'webrtc_perf_tests',
              args=[
                  '--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/',
                  '--nologs'
              ]))

  if test_suite == 'desktop_perf_swarming':
    tests.append(SwarmingPerfTest('low_bandwidth_audio_perf_test'))
    tests.append(
        SwarmingPerfTest(
            'webrtc_perf_tests',
            args=[
                '--test_artifacts_dir=${ISOLATED_OUTDIR}',
                '--save_worst_frame',
                '--nologs',
            ]))

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
    tests.append(SwarmingAndroidTest('AppRTCMobile_test_apk'))
    tests.append(SwarmingAndroidTest('android_instrumentation_test_apk'))
    tests.append(SwarmingAndroidTest('audio_decoder_unittests'))
    tests.append(SwarmingAndroidTest('common_audio_unittests'))
    tests.append(SwarmingAndroidTest('common_video_unittests'))
    tests.append(SwarmingAndroidTest('dcsctp_unittests'))
    tests.append(SwarmingAndroidTest('modules_tests', shards=2))
    tests.append(SwarmingAndroidTest('modules_unittests', shards=6))
    tests.append(SwarmingAndroidTest('peerconnection_unittests', shards=4))
    tests.append(SwarmingAndroidTest('rtc_media_unittests'))
    tests.append(SwarmingAndroidTest('rtc_stats_unittests'))
    tests.append(SwarmingAndroidTest('rtc_unittests', shards=6))
    tests.append(SwarmingAndroidTest('system_wrappers_unittests'))
    tests.append(SwarmingAndroidTest('test_support_unittests'))
    tests.append(SwarmingAndroidTest('tools_unittests'))
    tests.append(SwarmingAndroidTest('video_engine_tests', shards=4))
    tests.append(SwarmingAndroidTest('voip_unittests'))
    tests.append(SwarmingAndroidTest('webrtc_nonparallel_tests'))
    tests.append(AndroidJunitTest('android_examples_junit_tests'))
    tests.append(AndroidJunitTest('android_sdk_junit_tests'))

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
      tests.append(
          IosTest(
              'apprtcmobile_tests', xctest=True, xcode_parallelization=True))
      tests.append(
          IosTest('sdk_unittests', xctest=True, xcode_parallelization=True))

    tests.append(
        IosTest(
            'sdk_framework_unittests', xctest=True, xcode_parallelization=True))
    tests.append(IosTest('audio_decoder_unittests', xctest=True))
    tests.append(IosTest('common_audio_unittests', xctest=True))
    tests.append(IosTest('common_video_unittests', xctest=True))
    tests.append(IosTest('dcsctp_unittests', xctest=True))
    tests.append(IosTest('modules_tests', xctest=True))
    tests.append(IosTest('modules_unittests', xctest=True))
    tests.append(IosTest('rtc_media_unittests', xctest=True))
    tests.append(IosTest('rtc_pc_unittests', xctest=True))
    tests.append(IosTest('rtc_stats_unittests', xctest=True))
    tests.append(IosTest('rtc_unittests', xctest=True))
    tests.append(IosTest('system_wrappers_unittests', xctest=True))
    tests.append(IosTest('test_support_unittests', xctest=True))
    tests.append(IosTest('tools_unittests', xctest=True))
    tests.append(IosTest('video_capture_tests', xctest=True))
    tests.append(IosTest('video_engine_tests', xctest=True))
    tests.append(IosTest('voip_unittests', xctest=True))
    tests.append(IosTest('webrtc_nonparallel_tests', xctest=True))

  if test_suite == 'ios_device':
    tests.append(IosTest('common_audio_unittests'))
    tests.append(IosTest('common_video_unittests'))
    tests.append(IosTest('modules_tests'))
    tests.append(IosTest('modules_unittests'))
    tests.append(IosTest('rtc_pc_unittests'))
    tests.append(IosTest('rtc_stats_unittests'))
    tests.append(IosTest('system_wrappers_unittests'))
    tests.append(IosTest('test_support_unittests'))
    tests.append(IosTest('tools_unittests'))
    tests.append(IosTest('video_capture_tests'))
    tests.append(IosTest('video_engine_tests'))

  if test_suite == 'ios_perf':
    tests.append(
        IosTest(
            'webrtc_perf_tests',
            args=[
                '--write_perf_output_on_ios',
                '--nologs',
            ]))

  if test_suite == 'more_configs':
    if 'no_sctp' in phase:
      tests.append(SwarmingDesktopTest('peerconnection_unittests'))

  return tests


class WebRtcIsolatedGtest(steps.SwarmingIsolatedScriptTest):
  """Triggers an isolated task to run a GTest binary, and collects the results.

  This class is based off Chromium's SwarmingIsolatedScriptTest, but strips out
  the parts we don't need.
  """

  def __init__(self, name, result_handlers=None, **kwargs):
    """Constructs an instance of WebRtcIsolatedGtest.

    Args:
      name: Displayed name of the test.
      result_handlers: a list of callbacks that take (api, step_result,
          has_valid_results) and take some action to it (typically writing
          something into the step result).
    """
    super(WebRtcIsolatedGtest, self).__init__(
        steps.SwarmingIsolatedScriptTestSpec.create(name, **kwargs))
    self._result_handlers = result_handlers or []
    self._task = None
    self._has_collected = False

  def pre_run(self, api):
    """Launches the test on Swarming."""
    assert self._task is None, ('Test %s was already triggered' % self.name
                               )  # pragma no cover

    # *.isolated may be missing if *_run target is misconfigured.
    task_input = api.isolate.isolated_tests.get(self.isolate_target)
    if not task_input:  # pragma no cover
      return api.step.empty(
          '[error] %s' % self.name,
          status=api.step.FAILURE,
          step_text=('*.isolated file for target %s is missing' %
                     self.isolate_target))

    self._task = self.create_task(api, task_input)

    resultdb = ResultDB.create()
    for s in self._task.request[0].command:
      if '--dump_json_test_results=' in s:
        resultdb = attr.evolve(
            resultdb,
            result_format='json',
            result_file=s[len('--dump_json_test_results='):],
        )
    api.chromium_swarming.trigger_task(self._task, resultdb)
    # Remove 'invocations/' because it is added again in include_invocations.
    api.resultdb.include_invocations(
        [i[len('invocations/'):] for i in self._task.get_invocation_names()])

  @recipe_api.composite_step
  def run(self, api):
    """Waits for launched test to finish and collects the results."""
    assert not self._has_collected, (  # pragma no cover
        'Results of %s were already collected' % self.name)
    self._has_collected = True

    step_result, has_valid_results = api.chromium_swarming.collect_task(
        self._task, allow_missing_json=True)

    for handler in self._result_handlers:
      handler(api, step_result, has_valid_results)

    return step_result

  def create_task(self, api, task_input):
    task = api.chromium_swarming.task(
        name=self.name,
        raw_cmd=self._raw_cmd,
        relative_cwd=self._relative_cwd,
        cas_input_root=task_input)

    self._apply_swarming_task_config(
        task, api, suffix='', filter_flag=None, filter_delimiter=None)
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
  for file_name, contents in task_output_dir.items():
    if file_name.endswith('logcats'):  # pragma: no cover
      result += contents.decode()

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
      result_handlers=handlers,
      args=args,
      cipd_packages=ANDROID_CIPD_PACKAGES,
      shards=1,
      idempotent=False,
      **kwargs)


def SwarmingAndroidTest(name, **kwargs):
  return WebRtcIsolatedGtest(
      name,
      result_handlers=[InvalidResultsHandler, LogcatHandler],
      cipd_packages=ANDROID_CIPD_PACKAGES,
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
      result_handlers=handlers,
      args=args,
      shards=1,
      idempotent=False,
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
