# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools
import os
import sys

from recipe_engine.types import freeze
from recipe_engine.recipe_api import composite_step

THIS_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(THIS_DIR)))

from chromium_tests.steps import SwarmingGTestTest
from chromium_tests.steps import SwarmingIsolatedScriptTest

from webrtc.api import WEBRTC_GS_BUCKET

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
  'ortc_unittests': {},
  'peerconnection_unittests': {
    'shards': 4,
  },
  'rtc_media_unittests': {},
  'rtc_pc_unittests': {},
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
  'ortc_unittests': {},
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
  'AppRTCMobileTest': {},
  'libjingle_peerconnection_android_unittest': {},
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
    # TODO(ehmaldonado): Add low_bandwidth_audio_perf_test and
    # video_quality_loopback_test.
    'webrtc_perf_tests': {},
    'low_bandwidth_audio_perf_test': {
        'add_adb_path': True,
        'args': [
            '--android',
        ]
    },
    'video_quality_loopback_test': {
        'add_adb_path': True,
    },
})


def generate_tests(api, test_suite, phase, revision,
                   baremetal_swarming_dimensions, recipe_config, perf_id,
                   revision_number,
                   should_test_android_studio_project_generation):
  tests = []
  build_out_dir = api.path['checkout'].join(
      'out', api.chromium.c.build_config_fs)

  if test_suite in ('webrtc', 'webrtc_and_baremetal'):
    for test, extra_args in sorted(NORMAL_TESTS.items()):
      tests.append(SwarmingWebRtcGtestTest(test, **extra_args))

    if api.properties['mastername'] == 'client.webrtc.fyi' and (
        api.platform.is_win):
      tests.append(BaremetalTest(
          'modules_tests',
          name='modules_tests (screen capture disabled tests)',
          gtest_args=['--gtest_filter=ScreenCapturerIntegrationTest.*',
                      '--gtest_also_run_disabled_tests'],
          parallel=True))

  if test_suite == 'webrtc_and_baremetal':
    def add_test(name):
      tests.append(SwarmingWebRtcGtestTest(
          name,
          dimensions=baremetal_swarming_dimensions,
          **BAREMETAL_TESTS[name]))

    # TODO(bugs.webrtc.org/9292): enable on linux when webcams work.
    if not api.platform.is_linux:
      add_test('video_capture_tests')

    # Cover tests only running on perf tests on our trybots:
    if api.tryserver.is_tryserver:
      if api.platform.is_linux:
        add_test('isac_fix_test')

      is_win_clang = (api.platform.is_win and 'clang' in recipe_config)

      # TODO(kjellander): Enable on Mac when bugs.webrtc.org/7322 is fixed.
      # TODO(oprypin): Enable on MSVC when bugs.webrtc.org/9290 is fixed.
      if api.platform.is_linux or is_win_clang:
        add_test('webrtc_perf_tests')

  if test_suite == 'desktop_perf_swarming':
    for test, extra_args in sorted(PERF_TESTS.items()):
      tests.append(SwarmingPerfTest(test, **extra_args))
  if test_suite == 'android_perf_swarming' and perf_id:
    for test, extra_args in sorted(ANDROID_PERF_TESTS.items()):
      tests.append(SwarmingAndroidPerfTest(test, **extra_args))
  if test_suite == 'android_perf' and perf_id:
    # TODO(kjellander): Fix the Android ASan bot so we can have an assert here.
    tests.append(AndroidPerfTest(
        'webrtc_perf_tests',
        args=['--save_worst_frame'],
        revision=revision,
        revision_number=revision_number,
        perf_id=perf_id,
        upload_test_artifacts=True))

    tests.append(PerfTest(
        str(api.path['checkout'].join('audio', 'test',
                                        'low_bandwidth_audio_test.py')),
        name='low_bandwidth_audio_test',
        args=[api.chromium.output_dir, '--remove',
              '--android', '--adb-path', api.adb.adb_path()],
        revision=revision, revision_number=revision_number,
        perf_id=perf_id))

    # Skip video_quality_loopback_test on Android K bot (not supported).
    # TODO(oprypin): Re-enable on Nexus 4 once webrtc:7724 is fixed.
    if 'kitkat' not in perf_id and 'nexus4' not in perf_id:
      tests.append(PerfTest(
          str(api.path['checkout'].join('examples', 'androidtests',
                                          'video_quality_loopback_test.py')),
          name='video_quality_loopback_test',
          args=['--adb-path', api.adb.adb_path(), build_out_dir],
          revision=revision, revision_number=revision_number, perf_id=perf_id))

  if test_suite == 'android':
    for test, extra_args in sorted(ANDROID_DEVICE_TESTS.items() +
                                   ANDROID_INSTRUMENTATION_TESTS.items()):
      tests.append(AndroidTest(test, **extra_args))
    for test, extra_args in sorted(ANDROID_JUNIT_TESTS.items()):
      if api.properties['mastername'] == 'client.webrtc.fyi':
        tests.append(AndroidTest(test, **extra_args))
      else:
        tests.append(AndroidJunitTest(test))

    if should_test_android_studio_project_generation:
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
      tests.append(SwarmingWebRtcGtestTest(
          'bwe_simulations_tests',
          args=['--gtest_filter=VideoSendersTest/'
                'BweSimulation.Choke1000kbps500kbps1000kbps/1']))
    if 'no_sctp' in phase:
      tests.append(SwarmingWebRtcGtestTest('peerconnection_unittests'))

  return tests


def _MergeFiles(output_dir, suffix):
  result = ""
  for file_name, contents in output_dir.iteritems():
    if file_name.endswith(suffix): # pragma: no cover
      result += contents
  return result


@composite_step
def _UploadToPerfDashboard(name, api, task_output_dir):
  if api.webrtc._test_data.enabled:
    perf_results = {
      "format_version": "1.0",
      "charts": {
        "warm_times": {
          "http://www.google.com/": {
            "type": "list_of_scalar_values",
            "values": [9, 9, 8, 9],
            "units": "sec"
          },
        },
        "html_size": {
          "http://www.google.com/": {
            "type": "scalar",
            "value": 13579,
            "units": "bytes"
          }
        },
        "load_times": {
          "http://www.google.com/": {
            "type": "list_of_scalar_values",
            "value": [4.2],
            "std": 1.25,
            "units": "sec"
          }
        }
      }
    }
  else:  # pragma: no cover
    perf_results = api.json.loads(
        task_output_dir[api.path.join('0', 'perftest-output.json')])

  perf_results['benchmark_name'] = name

  args = [
      '--build-dir', api.path['checkout'].join('out'),
      '--buildername', api.properties['buildername'],
      '--buildnumber', api.properties['buildnumber'],
      '--name', name,
      '--perf-id', api.webrtc.c.PERF_ID,
      '--output-json-file', api.json.output(),
      '--results-file', api.json.input(perf_results),
      '--results-url', DASHBOARD_UPLOAD_URL,
  ]

  if 'git_revision' in api.properties:
    # This is the WebRTC hash we built at.
    revision = api.properties['git_revision']
    args.extend(['--got-webrtc-revision', revision])

  args.append('--output-json-dashboard-url')
  args.append(api.json.output(add_json_log=False, name='dashboard_url'))

  step_result = api.build.python(
      '%s Dashboard Upload' % name,
      api.chromium.package_repo_resource(
          'scripts', 'slave', 'upload_perf_dashboard_results.py'),
      args,
      step_test_data=(
          lambda: api.json.test_api.output('chromeperf.appspot.com',
                                           name='dashboard_url') +
          api.json.test_api.output({})))

  step_result.presentation.links['Results Dashboard'] = (
      step_result.json.outputs.get('dashboard_url', ''))


# TODO(kjellander): Continue refactoring an integrate the classes in the
# chromium_tests recipe module instead (if possible).
class Test(object):
  def __init__(self, test, name=None):
    self._test = test
    self._name = name or test

  def pre_run(self, api, suffix):
    return []

  def run(self, api, suffix): # pragma: no cover:
    raise NotImplementedError()

  def post_run(self, api, suffix):
    return []


class BaremetalTest(Test):
  """A WebRTC test that uses audio and/or video devices."""
  def __init__(self, test, name=None, revision=None, parallel=False,
               gtest_args=None, **runtest_kwargs):
    super(BaremetalTest, self).__init__(test, name)
    self._parallel = parallel
    self._gtest_args = gtest_args or []
    self._revision = revision
    self._runtest_kwargs = runtest_kwargs

  def run(self, api, suffix):
    test_type = self._test
    test = api.path['checkout'].join('tools_webrtc',
                                       'gtest-parallel-wrapper.py')
    test_ext = '.exe' if api.platform.is_win else ''
    test_executable = api.chromium.c.build_dir.join(
      api.chromium.c.build_config_fs, self._test + test_ext)

    args = [test_executable]
    if not self._parallel: args.append('--workers=1')
    args += self._gtest_args

    api.chromium.runtest(
        test=test, args=args, name=self._name, annotate=None, xvfb=True,
        python_mode=True, revision=self._revision, test_type=test_type,
        **self._runtest_kwargs)


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

  def post_run(self, api, suffix):
    try:
      super(SwarmingGTestTest, self).post_run(api, suffix)
    finally:
      step_result = api.step.active_result
      task_output_dir = api.step.active_result.raw_io.output_dir
      logcats = _MergeFiles(task_output_dir, 'logcats')
      step_result.presentation.logs['logcats'] = logcats.splitlines()

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
          source = api.json.input(parsed_gtest_data)
          api.test_results.upload(
              source,
              chrome_revision=chrome_revision,
              test_type=step_result.step['name'],
              test_results_server='test-results.appspot.com')


class SwarmingAndroidPerfTest(AndroidTest):
  def __init__(self, test, args=None, add_adb_path=False, **kwargs):
    args = list(args or [])
    args.extend([
        '--isolated-script-test-perf-output',
        '${ISOLATED_OUTDIR}/perftest-output.json',
        # Disable retries, since retrying will re-invoke the binary, which in
        # turn overwrites the perf result .json file.
        '--num-retries=0',
    ])
    if add_adb_path:
      args.extend([
          '--adb-path', ADB_PATH
      ])
    super(SwarmingAndroidPerfTest, self).__init__(test, args=args)

  def create_task(self, api, suffix, isolated_hash):
    return api.swarming.task(
        title=self._step_name(suffix),
        isolated_hash=isolated_hash,
        shards=self._shards,
        cipd_packages=self._cipd_packages,
        extra_args=self._args,
        build_properties=api.chromium.build_properties)

  def post_run(self, api, suffix):
    try:
      super(SwarmingGTestTest, self).post_run(api, suffix)
    finally:
      step_result = api.step.active_result
      task_output_dir = api.step.active_result.raw_io.output_dir
      logcats = _MergeFiles(task_output_dir, 'logcats')
      step_result.presentation.logs['logcats'] = logcats.splitlines()

      if not api.runtime.is_experimental:
        _UploadToPerfDashboard(self.name, api, task_output_dir)


class SwarmingPerfTest(SwarmingIsolatedScriptTest):
  def _output_perf_results_if_present(self, api, step_result):
    # We use our own custom upload mechanism.
    # TODO(phoglund): investigate if we can move off our custom mechanism.
    task_output_dir = step_result.raw_io.output_dir
    if not api.runtime.is_experimental:
      _UploadToPerfDashboard(self.name, api, task_output_dir)


class SwarmingWebRtcGtestTest(SwarmingIsolatedScriptTest):
  def _output_perf_results_if_present(self, api, step_result):
    # TODO(phoglund): find out why our regular tests use
    # SwarmingIsolatedScriptTest rather than SwarmingGTestTest. For now, stop
    # it from trying to perf report, at least.
    pass


class PerfTest(Test):
  """A WebRTC test that needs consistent hardware performance."""
  def __init__(self, test, name=None, args=None, revision=None,
               revision_number=None, perf_id=None, upload_test_artifacts=False,
               python_mode=False):
    super(PerfTest, self).__init__(test, name)
    assert revision, 'Revision is mandatory for perf tests'
    assert revision_number, (
        'A revision number must be specified for perf tests as they upload '
        'data to the perf dashboard.')
    assert perf_id

    self._revision_number = revision_number
    self._perf_id = perf_id
    self._args = args or []
    self._python_mode = python_mode

    self._should_upload_test_artifacts = upload_test_artifacts
    self._test_artifacts_path = None
    self._test_artifacts_name = self._name + '_test_artifacts'

    self._perf_config= PERF_CONFIG
    self._perf_config['r_webrtc_git'] = revision

  def run(self, api, suffix):
    # Some of the perf tests depend on depot_tools for
    # download_from_google_storage and gsutil usage.
    with api.depot_tools.on_path():
      api.chromium.runtest(
          test=self._test, name=self._name, args=self._args,
          results_url=DASHBOARD_UPLOAD_URL, annotate='graphing', xvfb=True,
          perf_dashboard_id=self._name, test_type=self._name,
          revision=self._revision_number, perf_id=self._perf_id,
          perf_config=self._perf_config, python_mode=self._python_mode)


class AndroidJunitTest(Test):
  """Runs an Android Junit test."""

  def run(self, api, suffix):
    api.chromium_android.run_java_unit_test_suite(self._name)


class AndroidPerfTest(PerfTest):
  """A performance test to run on Android devices.

    Basically just wrap what happens in chromium_android.run_test_suite to run
    inside runtest.py so we can scrape perf data. This way we can get perf data
    from the gtest binaries since the way of running perf tests with telemetry
    is entirely different.
  """

  def __init__(self, test, name=None, args=None, revision=None,
               revision_number=None, perf_id=None, upload_test_artifacts=False):
    args = (args or []) + ['--verbose']
    super(AndroidPerfTest, self).__init__(
        test, name, args=args, revision=revision,
        revision_number=revision_number, perf_id=perf_id,
        upload_test_artifacts=upload_test_artifacts, python_mode=True)

  def _prepare_test_artifacts_upload(self, api):
    gtest_results_file = api.test_utils.gtest_results(add_json_log=False)
    self._args.extend(['--gs-test-artifacts-bucket', WEBRTC_GS_BUCKET,
                       '--json-results-file', gtest_results_file])

  def _upload_test_artifacts(self, api):
    step_result = api.step.active_result
    if (hasattr(step_result, 'test_utils') and
        hasattr(step_result.test_utils, 'gtest_results')):
      json_results = api.json.input(step_result.test_utils.gtest_results.raw)
      details_link = api.chromium_android.create_result_details(
          self._name, json_results)
      api.step.active_result.presentation.links['result_details'] = (
          details_link)

  @composite_step
  def run(self, api, suffix):
    wrapper_script = api.chromium.output_dir.join('bin',
                                                    'run_%s' % self._name)
    self._test = wrapper_script
    if self._should_upload_test_artifacts:
      self._prepare_test_artifacts_upload(api)
    try:
      super(AndroidPerfTest, self).run(api, suffix)
    finally:
      if self._should_upload_test_artifacts:
        self._upload_test_artifacts(api)
