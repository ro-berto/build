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
from chromium_tests.steps import SwarmingIsolatedScriptTest
from chromium_tests.steps import SwarmingTest

PERF_CONFIG = {'a_default_rev': 'r_webrtc_git'}
DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'
# adb path relative to out dir (e.g. out/Release)
ADB_PATH = '../../third_party/android_tools/sdk/platform-tools/adb'

NORMAL_TESTS = freeze({
  'audio_decoder_unittests': {},
  'common_audio_unittests': {},
  'common_video_unittests': {},
  'low_bandwidth_audio_test': {},
  'modules_tests': {
    'shards': 2,
  },
  'modules_unittests': {
    'shards': 6,
  },
  'peerconnection_unittests': {
    'shards': 4,
  },
  'rtc_media_unittests': {},
  'rtc_pc_unittests': {},
  'rtc_stats_unittests': {},
  'rtc_unittests': {
    'shards': 6,
  },
  'slow_tests': {},
  'system_wrappers_unittests': {},
  'test_support_unittests': {},
  'tools_unittests': {},
  'video_engine_tests': {
    'shards': 4,
  },
  'webrtc_nonparallel_tests': {},
})

ANDROID_DEVICE_TESTS = freeze({
  'audio_decoder_unittests': {},
  'common_audio_unittests': {},
  'common_video_unittests': {},
  'modules_tests': {
    'shards': 2,
  },
  'modules_unittests': {
    'shards': 6,
  },
  'peerconnection_unittests': {
    'shards': 4,
  },
  'rtc_stats_unittests': {},
  'rtc_unittests': {
    'shards': 6,
  },
  'system_wrappers_unittests': {},
  'test_support_unittests': {},
  'tools_unittests': {},
  'video_engine_tests': {
    'shards': 4,
  },
  'webrtc_nonparallel_tests': {},
})

BAREMETAL_TESTS = freeze({
  'isac_fix_test': {},
  'video_capture_tests': {},
  'webrtc_perf_tests': {
      'args': ['--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/'],
  },
})

ANDROID_INSTRUMENTATION_TESTS = freeze({
  'AppRTCMobile_test_apk': {},
  'android_instrumentation_test_apk': {},
})

ANDROID_JUNIT_TESTS = freeze({
  'android_junit_tests': {
    'shards': 1,
  },
})

ANDROID_CIPD_PACKAGES = [
    ("bin",
     "infra/tools/luci/logdog/butler/${platform}",
     "git_revision:ff387eadf445b24c935f1cf7d6ddd279f8a6b04c",
    )
]

PERF_TESTS = freeze({
    'isac_fix_test': {},
    'low_bandwidth_audio_perf_test': {},
    'webrtc_perf_tests': {
        'args': [
            '--test-artifacts-dir', '${ISOLATED_OUTDIR}',
            '--save_worst_frame',
        ],
    },
})

ANDROID_PERF_TESTS = freeze({
    'webrtc_perf_tests': {
        'args': [
            '--save_worst_frame',
        ],
    },
    'low_bandwidth_audio_perf_test': {
        'args': [
            '--android',
            '--adb-path', ADB_PATH,
        ],
    },
    'video_quality_loopback_test': {
        'args': [
            '--adb-path', ADB_PATH,
        ],
    },
})


def generate_tests(api, phase, revision, revision_number, bot):
  tests = []
  build_out_dir = api.path['checkout'].join(
      'out', api.chromium.c.build_config_fs)
  test_suite = bot.test_suite

  if test_suite in ('webrtc', 'webrtc_and_baremetal'):
    for test, extra_args in sorted(NORMAL_TESTS.items()):
      tests.append(SwarmingIsolatedScriptTest(test, **extra_args))

  if test_suite == 'webrtc_and_baremetal':
    def add_test(name):
      tests.append(SwarmingIsolatedScriptTest(
          name,
          dimensions=bot.config['baremetal_swarming_dimensions'],
          **BAREMETAL_TESTS[name]))


    add_test('video_capture_tests')

    # Cover tests only running on perf tests on our trybots:
    if api.tryserver.is_tryserver:
      if api.platform.is_linux:
        add_test('isac_fix_test')

      is_win_clang = (api.platform.is_win and
                      'clang' in bot.recipe_config['chromium_config'])

      # TODO(kjellander): Enable on Mac when bugs.webrtc.org/7322 is fixed.
      # TODO(oprypin): Enable on MSVC when bugs.webrtc.org/9290 is fixed.
      if api.platform.is_linux or is_win_clang:
        add_test('webrtc_perf_tests')

  if test_suite == 'desktop_perf_swarming':
    for test, extra_args in sorted(PERF_TESTS.items()):
      tests.append(SwarmingPerfTest(test, **extra_args))

  if test_suite == 'android_perf_swarming':
    def add_test(name):
      tests.append(SwarmingAndroidPerfTest(name, **ANDROID_PERF_TESTS[name]))

    add_test('low_bandwidth_audio_perf_test')
    # Skip video_quality_loopback_test on Android K bot (not supported).
    if not re.search(r'Android.+\bK\b', bot.builder):
      add_test('video_quality_loopback_test')
    add_test('webrtc_perf_tests')

  if test_suite == 'android':
    for test, extra_args in sorted(ANDROID_DEVICE_TESTS.items() +
                                   ANDROID_INSTRUMENTATION_TESTS.items()):
      tests.append(AndroidTest(test, **extra_args))
    for test, extra_args in sorted(ANDROID_JUNIT_TESTS.items()):
      tests.append(AndroidJunitTest(test))

    if bot.should_test_android_studio_project_generation:
       tests.append(PythonTest(
          test='gradle_project_test',
          script=str(api.path['checkout'].join('examples',  'androidtests',
                                               'gradle_project_test.py')),
          args=[build_out_dir],
          env={'GOMA_DISABLED': True}))
    if api.tryserver.is_tryserver:
      tests.append(AndroidTest(
          'webrtc_perf_tests',
          args=['--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/']))

  if test_suite == 'more_configs':
    if 'bwe_test_logging' in phase:
      tests.append(SwarmingIsolatedScriptTest(
          'bwe_simulations_tests',
          args=['--gtest_filter=VideoSendersTest/'
                'BweSimulation.Choke1000kbps500kbps1000kbps/1']))
    if 'no_sctp' in phase:
      tests.append(SwarmingIsolatedScriptTest('peerconnection_unittests'))

  return tests


def _MergeFiles(output_dir, suffix):
  result = ""
  for file_name, contents in output_dir.iteritems():
    if file_name.endswith(suffix): # pragma: no cover
      result += contents
  return result


def _UploadToPerfDashboard(name, api, step_result):
  test_succeeded = (step_result.presentation.status == api.step.SUCCESS)

  if api.webrtc._test_data.enabled and test_succeeded:
    step_result.raw_io.output_dir = {
      '0/perftest-output.json': api.webrtc.test_api.example_chartjson(),
      'logcats': 'foo',
    }
  task_output_dir = step_result.raw_io.output_dir

  results_to_upload = []
  for filepath in sorted(task_output_dir):
    # File names are 'perftest-output.json', 'perftest-output_1.json', ...
    if re.search(r'perftest-output.*\.json$', filepath):
      perf_results = api.json.loads(task_output_dir[filepath])
      if perf_results:
        results_to_upload.append(perf_results)

  if not results_to_upload and test_succeeded: # pragma: no cover
    raise api.step.InfraFailure(
        'Cannot find JSON performance data for a test that succeeded.')

  perf_bot_group = 'WebRTCPerf'
  if api.runtime.is_experimental:
    perf_bot_group = 'Experimental' + perf_bot_group

  for perf_results in results_to_upload:
    args = [
        '--build-url', api.webrtc.build_url,
        '--name', name,
        '--perf-id', api.webrtc.c.PERF_ID,
        '--output-json-file', api.json.output(),
        '--results-file', api.json.input(perf_results),
        '--results-url', DASHBOARD_UPLOAD_URL,
        '--commit-position', api.webrtc.revision_number,
        '--got-webrtc-revision', api.webrtc.revision,
        '--perf-dashboard-machine-group', perf_bot_group,
    ]

    api.build.python(
        '%s Dashboard Upload' % name,
        api.webrtc.resource('upload_perf_dashboard_results.py'),
        args,
        step_test_data=lambda: api.json.test_api.output({}),
        infra_step=True)


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
        api.python(self._test, self._script, self._args)


class AndroidTest(SwarmingGTestTest):
  def __init__(self, test, **kwargs):
    super(AndroidTest, self).__init__(test, override_isolate_target=test,
                                      cipd_packages=ANDROID_CIPD_PACKAGES,
                                      **kwargs)

  def validate_task_results(self, api, step_result):
    valid = super(AndroidTest, self).validate_task_results(api, step_result)

    task_output_dir = api.step.active_result.raw_io.output_dir
    logcats = _MergeFiles(task_output_dir, 'logcats')
    step_result.presentation.logs['logcats'] = logcats.splitlines()

    return valid


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
    return api.swarming.task(
        title=self._step_name(suffix),
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

    _UploadToPerfDashboard(self.name, api, step_result)

    # There currently exists no validation logic for the results generated by
    # swarming android perf tests. This should be fixed.
    return True, None, 0, None

  def compile_targets(self, api): # pragma: no cover
    return []


class SwarmingPerfTest(SwarmingIsolatedScriptTest):
  def __init__(self, *args, **kwargs):
    # Perf tests are not idempotent, because for almost all tests the binary
    # will not return the exact same perf result each time. We want to get those
    # results so the dashboard can properly determine the variance of the test.
    kwargs.setdefault('idempotent', False)
    super(SwarmingPerfTest, self).__init__(*args, **kwargs)

  def validate_task_results(self, api, step_result):
    valid = super(SwarmingPerfTest, self).validate_task_results(
        api, step_result)

    _UploadToPerfDashboard(self.name, api, step_result)

    return valid


class AndroidJunitTest(Test):
  """Runs an Android Junit test."""

  def run(self, api, suffix):
    api.chromium_android.run_java_unit_test_suite(self._name)
