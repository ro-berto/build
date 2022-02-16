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

QUICK_PERF_TEST = '--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/'

NUMBER_OF_SHARDS = {
    'modules_tests': 2,
    'modules_unittests': 6,
    'peerconnection_unittests': 4,
    'rtc_unittests': 6,
    'video_engine_tests': 4,
}


def generate_tests(phase, bot, is_tryserver, chromium_tests_api):
  """Generate a list of tests to run on a bot.

  Args:
    phase: string to distinguish the phase of a builder (used only for
      more_configs builders).
    bot: string with the name of the bot (e.g. 'linux_compile_rel').
    is_tryserver: True if the tests needs to be generated for a tryserver.
    chromium_tests_api: The chromium_tests recipe module API object.

  Returns:
    A list of steps.WebRtcIsolatedGtest to compile and run on a bot.
  """
  tests = []
  test_suite = bot.test_suite

  desktop_tests = [
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
  ]
  android_tests = [
      'AppRTCMobile_test_apk',
      'android_instrumentation_test_apk',
      'audio_decoder_unittests',
      'common_audio_unittests',
      'common_video_unittests',
      'dcsctp_unittests',
      'modules_tests',
      'modules_unittests',
      'peerconnection_unittests',
      'rtc_pc_unittests',
      'rtc_media_unittests',
      'rtc_stats_unittests',
      'rtc_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_engine_tests',
      'voip_unittests',
      'webrtc_nonparallel_tests',
  ]
  ios_tests = [
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
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_capture_tests',
      'video_engine_tests',
      'voip_unittests',
      'webrtc_nonparallel_tests',
  ]
  ios_device_tests = [
      'common_audio_unittests',
      'common_video_unittests',
      'modules_tests',
      'modules_unittests',
      'rtc_pc_unittests',
      'rtc_stats_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_capture_tests',
      'video_engine_tests',
  ]

  if test_suite == 'webrtc':
    tests = [SwarmingDesktopTest(t, chromium_tests_api) for t in desktop_tests]

  if test_suite == 'webrtc_and_baremetal':
    dimensions = bot.config['baremetal_swarming_dimensions']
    tests = [SwarmingDesktopTest(t, chromium_tests_api) for t in desktop_tests]
    tests.append(
        SwarmingDesktopTest(
            'video_capture_tests', chromium_tests_api, dimensions=dimensions))
    # Cover tests only running on perf tests on our trybots:
    if is_tryserver:
      tests.append(
          SwarmingPerfTest(
              'webrtc_perf_tests',
              chromium_tests_api,
              args=[QUICK_PERF_TEST, '--nologs'],
              dimensions=dimensions))

  if test_suite == 'desktop_perf_swarming':
    tests = [
        # Perf tests are marked as not idempotent, which means they're re-run
        # if they did not change this build. This will give the dashboard some
        # more variance data to work with.
        SwarmingPerfTest(
            'low_bandwidth_audio_perf_test',
            chromium_tests_api,
            idempotent=False),
        SwarmingPerfTest(
            'webrtc_perf_tests',
            chromium_tests_api,
            idempotent=False,
            args=[
                '--test_artifacts_dir=${ISOLATED_OUTDIR}',
                '--save_worst_frame',
                '--nologs',
            ])
    ]

  if test_suite == 'android_perf_swarming':
    perftest_output = ('--isolated-script-test-perf-output='
                       '${ISOLATED_OUTDIR}/perftest-output.json')
    tests = [
        SwarmingAndroidTest(
            'low_bandwidth_audio_perf_test',
            chromium_tests_api,
            idempotent=False,
            args=['--android', '--adb-path', ADB_PATH, perftest_output]),
        SwarmingAndroidTest(
            'webrtc_perf_tests',
            chromium_tests_api,
            idempotent=False,
            args=['--save_worst_frame', '--nologs', perftest_output])
    ]

  if test_suite == 'android':
    tests = [SwarmingAndroidTest(t, chromium_tests_api) for t in android_tests]
    tests += [
        AndroidJunitTest('android_examples_junit_tests', chromium_tests_api),
        AndroidJunitTest('android_sdk_junit_tests', chromium_tests_api)
    ]
    if is_tryserver:
      tests.append(
          SwarmingAndroidTest(
              'webrtc_perf_tests',
              chromium_tests_api,
              args=[QUICK_PERF_TEST, '--nologs']))

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
    ]:  # pragma: no cover
      tests += [
          IosTest(
              'apprtcmobile_tests', xctest=True, xcode_parallelization=True),
          IosTest('sdk_unittests', xctest=True, xcode_parallelization=True)
      ]

    tests.append(
        IosTest(
            'sdk_framework_unittests', xctest=True, xcode_parallelization=True))
    tests += [IosTest(t, xctest=True) for t in ios_tests]

  if test_suite == 'ios_device':
    tests = [IosTest(t) for t in ios_device_tests]

  if test_suite == 'ios_perf':
    tests = [
        IosTest(
            'webrtc_perf_tests',
            args=['--write_perf_output_on_ios', '--nologs'])
    ]

  if test_suite == 'more_configs':
    if 'no_sctp' in phase:
      tests = [
          SwarmingDesktopTest('peerconnection_unittests', chromium_tests_api)
      ]

  return tests


def SwarmingDesktopTest(name, chromium_tests_api, **kwargs):
  return steps.SwarmingIsolatedScriptTest(
      steps.SwarmingIsolatedScriptTestSpec.create(
          name,
          resultdb=ResultDB(result_format='json'),
          shards=NUMBER_OF_SHARDS.get(name, 1),
          **kwargs), chromium_tests_api)


def SwarmingPerfTest(name, chromium_test_api, **kwargs):
  merge = chromium_swarming.MergeScript(
      script=chromium_test_api.m.chromium_swarming.resource('noop_merge.py'))
  return steps.SwarmingIsolatedScriptTest(
      steps.SwarmingIsolatedScriptTestSpec.create(
          name,
          merge=merge,
          resultdb=ResultDB(result_format='gtest_json'),
          **kwargs), chromium_test_api)


def SwarmingAndroidTest(name, chromium_tests_api, **kwargs):
  return steps.SwarmingGTestTest(
      steps.SwarmingGTestTestSpec.create(
          name,
          cipd_packages=ANDROID_CIPD_PACKAGES,
          shards=NUMBER_OF_SHARDS.get(name, 1),
          **kwargs), chromium_tests_api)


def AndroidJunitTest(name, chromium_tests_api):
  return steps.AndroidJunitTest(
      steps.AndroidJunitTestSpec.create(name), chromium_tests_api)


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
