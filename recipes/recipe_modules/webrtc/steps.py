# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

from recipe_engine.engine_types import freeze
from RECIPE_MODULES.build import chromium_swarming
from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB


# adb path relative to out dir (e.g. out/Release)
_ADB_PATH = '../../third_party/android_sdk/public/platform-tools/adb'

_ANDROID_CIPD_PACKAGE = chromium_swarming.CipdPackage.create(
    name='infra/tools/luci/logdog/butler/${platform}',
    version='git_revision:ff387eadf445b24c935f1cf7d6ddd279f8a6b04c',
    root='bin',
)

_MAC_TOOLCHAIN_CIPD_PACKAGE = chromium_swarming.CipdPackage.create(
    name=steps.MAC_TOOLCHAIN_PACKAGE,
    version=steps.MAC_TOOLCHAIN_VERSION,
    root=steps.MAC_TOOLCHAIN_ROOT,
)

_QUICK_PERF_TEST = '--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/'

_PERF_TESTS = (
    'low_bandwidth_audio_perf_test',
    'webrtc_perf_tests',
)

# Tests written with the XCTest framework.
# The "fake" xctests are gtests using a XCTest wrapper when running on iOS.
_REAL_XCTEST_TESTS = (
    'apprtcmobile_tests',
    'sdk_unittests',
    'sdk_framework_unittests',
)

_NUMBER_OF_SHARDS = freeze({
    'modules_tests': 2,
    'modules_unittests': 6,
    'peerconnection_unittests': 4,
    'rtc_unittests': 6,
    'video_engine_tests': 4,
})


def generate_tests(phase, bot, is_tryserver, chromium_tests_api, ios_config):
  """Generate a list of tests to run on a bot.

  Args:
    phase: string to distinguish the phase of a builder (used only for
      more_configs builders).
    bot: string with the name of the bot (e.g. 'linux_compile_rel').
    is_tryserver: True if the tests needs to be generated for a tryserver.
    chromium_tests_api: The chromium_tests recipe module API object.
    ios_config: iOS configuration such as the xcode version.

  Returns:
    A list of steps.WebRtcIsolatedGtest to compile and run on a bot.
  """
  desktop_tests = (
      'audio_decoder_unittests',
      'common_audio_unittests',
      'common_video_unittests',
      'dcsctp_unittests',
      'low_bandwidth_audio_test',
      'modules_tests',
      'modules_unittests',
      'peerconnection_unittests',
      'rtc_media_unittests',
      'rtc_pc_unittests',
      'rtc_stats_unittests',
      'rtc_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_engine_tests',
      'voip_unittests',
      'webrtc_nonparallel_tests',
  )
  android_tests = (
      'AppRTCMobile_test_apk',
      'android_instrumentation_test_apk',
      'audio_decoder_unittests',
      'common_audio_unittests',
      'common_video_unittests',
      'dcsctp_unittests',
      'modules_tests',
      'modules_unittests',
      'peerconnection_unittests',
      'rtc_media_unittests',
      'rtc_pc_unittests',
      'rtc_stats_unittests',
      'rtc_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_engine_tests',
      'voip_unittests',
      'webrtc_nonparallel_tests',
  )
  ios_tests = (
      # TODO(bugs.webrtc.org/12244): Some tests are skipped on iOS simulator
      # platforms because they fail or they are flaky.
      #'apprtcmobile_tests',
      'audio_decoder_unittests',
      'common_audio_unittests',
      'common_video_unittests',
      'dcsctp_unittests',
      'modules_tests',
      'modules_unittests',
      'rtc_media_unittests',
      'rtc_pc_unittests',
      'rtc_stats_unittests',
      'rtc_unittests',
      'sdk_framework_unittests',
      # TODO(bugs.webrtc.org/12244): Some tests are skipped on iOS simulator
      # platforms because they fail or they are flaky.
      #'sdk_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_capture_tests',
      'video_engine_tests',
      'voip_unittests',
      'webrtc_nonparallel_tests',
  )
  ios_device_tests = (
      # TODO(bugs.webrtc.org/11362): Real XCTests fail to start on devices.
      #'apprtcmobile_tests',
      'common_audio_unittests',
      'common_video_unittests',
      'modules_tests',
      'modules_unittests',
      'rtc_pc_unittests',
      'rtc_stats_unittests',
      # TODO(bugs.webrtc.org/11362): Real XCTests fail to start on devices.
      #'sdk_framework_unittests',
      #'sdk_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_capture_tests',
      'video_engine_tests',
  )
  tests = []
  test_suite = bot.test_suite
  generator = TestGenerator(chromium_tests_api, ios_config)

  if test_suite == 'webrtc':
    tests = [generator.swarming_desktop_test(t) for t in desktop_tests]

  if test_suite == 'webrtc_and_baremetal':
    dimensions = bot.config['baremetal_swarming_dimensions']
    tests = [generator.swarming_desktop_test(t) for t in desktop_tests]
    tests.append(
        generator.swarming_desktop_test(
            'video_capture_tests', dimensions=dimensions))
    # Cover tests only running on perf tests on our trybots:
    if is_tryserver:
      args = [_QUICK_PERF_TEST, '--nologs']
      tests.append(
          generator.swarming_desktop_test('webrtc_perf_tests', args,
                                          dimensions))

  if test_suite == 'desktop_perf_swarming':
    tests = [
        generator.swarming_desktop_test('low_bandwidth_audio_perf_test'),
        generator.swarming_desktop_test(
            'webrtc_perf_tests',
            args=[
                '--test_artifacts_dir=${ISOLATED_OUTDIR}',
                '--save_worst_frame',
                '--nologs',
            ])
    ]

  if test_suite == 'android':
    tests = [generator.swarming_android_test(t) for t in android_tests]
    tests += [
        generator.android_junit_test('android_examples_junit_tests'),
        generator.android_junit_test('android_sdk_junit_tests')
    ]
    if is_tryserver:
      args = [_QUICK_PERF_TEST, '--nologs']
      tests.append(generator.swarming_android_test('webrtc_perf_tests', args))

  if test_suite == 'android_perf_swarming':
    tests = [
        generator.swarming_android_test(
            'low_bandwidth_audio_perf_test',
            args=['--android', '--adb-path', _ADB_PATH]),
        generator.swarming_android_test(
            'webrtc_perf_tests', args=['--save_worst_frame', '--nologs'])
    ]

  if test_suite == 'ios':
    tests += [generator.swarming_ios_test(t) for t in ios_tests]

  if test_suite == 'ios_device':
    args = ['--xctest', '--undefok=enable-run-ios-unittests-with-xctest']
    tests = [generator.swarming_ios_test(t, args) for t in ios_device_tests]

  if test_suite == 'ios_perf':
    tests = [generator.swarming_ios_test('webrtc_perf_tests')]

  if test_suite == 'more_configs':
    if 'no_sctp' in phase:
      tests = [generator.swarming_desktop_test('peerconnection_unittests')]

  return tests


class TestGenerator:

  def __init__(self, chromium_tests_api, ios_config):
    self._chromium_tests_api = chromium_tests_api
    self._ios_config = ios_config

  def swarming_desktop_test(self, name, args=None, dimensions=None):
    args = args or []
    resultdb = ResultDB(result_format='json')
    if name in _PERF_TESTS:
      args.append('--gtest_output=json:${ISOLATED_OUTDIR}/gtest_output.json')
      resultdb = ResultDB(
          result_format='gtest_json',
          result_file='${ISOLATED_OUTDIR}/gtest_output.json')
    return steps.SwarmingIsolatedScriptTest(
        steps.SwarmingIsolatedScriptTestSpec.create(
            name,
            args=args,
            resultdb=resultdb,
            shards=_NUMBER_OF_SHARDS.get(name, 1),
            dimensions=dimensions or {}), self._chromium_tests_api)

  def swarming_ios_test(self, name, args=None):
    args = args or []
    args = args + self._ios_config['args']
    if name in _PERF_TESTS:
      args += ['--write_perf_output_on_ios', '--nologs']
    if name in _REAL_XCTEST_TESTS:
      args.append('--xcode-parallelization' if '--version' in
                  args else '--xcodebuild-device-runner')
    return steps.SwarmingIsolatedScriptTest(
        steps.SwarmingIsolatedScriptTestSpec.create(
            name,
            cipd_packages=[_MAC_TOOLCHAIN_CIPD_PACKAGE],
            named_caches=self._ios_config['named_caches'],
            service_account=self._ios_config['service_account'],
            args=args), self._chromium_tests_api)

  def swarming_android_test(self, name, args=None):
    args = args or []
    if name in _PERF_TESTS:
      args.append('--isolated-script-test-perf-output='
                  '${ISOLATED_OUTDIR}/perftest-output.pb')
    return steps.SwarmingGTestTest(
        steps.SwarmingGTestTestSpec.create(
            name,
            cipd_packages=[_ANDROID_CIPD_PACKAGE],
            shards=_NUMBER_OF_SHARDS.get(name, 1),
            args=args), self._chromium_tests_api)

  def android_junit_test(self, name):
    return steps.AndroidJunitTest(
        steps.AndroidJunitTestSpec.create(name), self._chromium_tests_api)
