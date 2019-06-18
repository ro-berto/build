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

from chromium_tests.steps import SwarmingGTestTest
from chromium_tests.steps import (
    SwarmingIsolatedScriptTest as SwarmingIsolatedTest)
from chromium_tests.steps import SwarmingTest

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
        SwarmingIsolatedTest('audio_decoder_unittests'),
        SwarmingIsolatedTest('common_audio_unittests'),
        SwarmingIsolatedTest('common_video_unittests'),
        SwarmingIsolatedTest('low_bandwidth_audio_test'),
        SwarmingIsolatedTest('modules_tests', shards=2),
        SwarmingIsolatedTest('modules_unittests', shards=6),
        SwarmingIsolatedTest('peerconnection_unittests', shards=4),
        SwarmingIsolatedTest('rtc_media_unittests'),
        SwarmingIsolatedTest('rtc_pc_unittests'),
        SwarmingIsolatedTest('rtc_stats_unittests'),
        SwarmingIsolatedTest('rtc_unittests', shards=6),
        SwarmingIsolatedTest('slow_tests'),
        SwarmingIsolatedTest('system_wrappers_unittests'),
        SwarmingIsolatedTest('test_support_unittests'),
        SwarmingIsolatedTest('tools_unittests'),
        SwarmingIsolatedTest('video_engine_tests', shards=4),
        SwarmingIsolatedTest('webrtc_nonparallel_tests'),
    ]

  if test_suite == 'webrtc_and_baremetal':
    baremetal_test = functools.partial(
        SwarmingIsolatedTest,
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
            '--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/'
        ]))

  if test_suite == 'desktop_perf_swarming':
    tests += [
        SwarmingPerfTest('isac_fix_test'),
        SwarmingPerfTest('low_bandwidth_audio_perf_test'),
        SwarmingPerfTest('webrtc_perf_tests', args=[
            '--test-artifacts-dir', '${ISOLATED_OUTDIR}',
            '--save_worst_frame',
        ]),
    ]

  if test_suite == 'android_perf_swarming':
    tests.append(SwarmingAndroidPerfTest('low_bandwidth_audio_perf_test', args=[
        '--android',
        '--adb-path', ADB_PATH,
    ]))
    tests.append(SwarmingAndroidPerfTest('webrtc_perf_tests', args=[
        '--save_worst_frame',
    ]))

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

        AndroidJunitTest('android_junit_tests'),
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
          '--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/'
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
        IosTest('webrtc_perf_tests', args=['--save_chartjson_result']),
    ]

  if test_suite == 'more_configs':
    if 'no_sctp' in phase:
      tests.append(SwarmingIsolatedTest('peerconnection_unittests'))

  return tests


def _MergeFiles(output_dir, suffix):
  result = ""
  for file_name, contents in output_dir.iteritems():
    if file_name.endswith(suffix): # pragma: no cover
      result += contents
  return result


# TODO(kjellander): Continue refactoring an integrate the classes in the
# chromium_tests recipe module instead (if possible).
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


class AndroidTest(SwarmingGTestTest):
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


class SwarmingAndroidPerfTest(SwarmingTest):
  def __init__(self, test, args=None, shards=1, cipd_packages=None,
               idempotent=False, **kwargs):
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
    super(SwarmingAndroidPerfTest, self).__init__(test, **kwargs)

  def create_task(self, api, suffix, isolated_hash):
    return api.chromium_swarming.task(
        title=self.step_name(suffix),
        isolated_hash=isolated_hash,
        shards=self._shards,
        cipd_packages=self._cipd_packages,
        idempotent=self._idempotent,
        extra_args=self._args,
        build_properties=api.chromium.build_properties)

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


class SwarmingPerfTest(SwarmingIsolatedTest):
  def __init__(self, *args, **kwargs):
    # Perf tests are not idempotent, because for almost all tests the binary
    # will not return the exact same perf result each time. We want to get those
    # results so the dashboard can properly determine the variance of the test.
    kwargs.setdefault('idempotent', False)
    super(SwarmingPerfTest, self).__init__(*args, **kwargs)

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
