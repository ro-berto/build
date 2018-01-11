# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

from recipe_engine.types import freeze
from recipe_engine.recipe_api import composite_step

THIS_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(THIS_DIR)))

from chromium_tests.steps import SwarmingGTestTest
from chromium_tests.steps import SwarmingIsolatedScriptTest


PERF_CONFIG = {'a_default_rev': 'r_webrtc_git'}
DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'

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
  'voice_engine_unittests': {},
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
  'voice_engine_unittests': {},
  'webrtc_nonparallel_tests': {},
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
            '--store-test-artifacts',
            '--save_worst_frame',
        ],
    },
})

ANDROID_PERF_TESTS = freeze({
    # TODO(ehmaldonado): Add low_bandwidth_audio_perf_test and
    # video_quality_loopback_test.
    'webrtc_perf_tests': {
        'args': [
           '--gtest_filter='
           'AudioEncoderOpusComplexityAdaptationTest.AdaptationOn',
        ],
    },
})


def generate_tests(api, test_suite, revision):
  tests = []
  build_out_dir = api.m.path['checkout'].join(
      'out', api.m.chromium.c.build_config_fs)

  if test_suite == 'webrtc':
    for test, extra_args in sorted(NORMAL_TESTS.items()):
      tests.append(SwarmingIsolatedScriptTest(test, **extra_args))
    if api.mastername == 'client.webrtc.fyi' and api.m.platform.is_win:
      tests.append(BaremetalTest(
          'modules_tests',
          name='modules_tests (screen capture disabled tests)',
          gtest_args=['--gtest_filter=ScreenCapturerIntegrationTest.*',
                      '--gtest_also_run_disabled_tests'],
          parallel=True))
  elif test_suite == 'webrtc_baremetal':
    api.virtual_webcam_check()  # Needed for video_capture_tests below.

    tests.extend([
        BaremetalTest('video_capture_tests', revision=revision),
    ])

    # Cover tests only running on perf tests on our trybots:
    if api.m.tryserver.is_tryserver:
      if api.m.platform.is_linux:
        tests.append(BaremetalTest(
            'isac_fix_test',
            revision=revision,
            args=[
                '32000', api.m.path['checkout'].join(
                    'resources', 'speech_and_misc_wb.pcm'),
                'isac_speech_and_misc_wb.pcm']))

      # TODO(kjellander): Enable on Mac when bugs.webrtc.org/7322 is fixed.
      if not api.m.platform.is_mac:
        tests.append(BaremetalTest('webrtc_perf_tests', revision=revision,
            args=['--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/']))
  elif test_suite == 'desktop_perf_swarming':
    for test, extra_args in sorted(PERF_TESTS.items()):
      tests.append(SwarmingPerfTest(test, api, **extra_args))
  elif test_suite == 'android_perf_swarming' and api.c.PERF_ID:
    for test, extra_args in sorted(ANDROID_PERF_TESTS.items()):
      tests.append(SwarmingAndroidPerfTest(test, **extra_args))
  elif test_suite == 'android_perf' and api.c.PERF_ID:
    # TODO(kjellander): Fix the Android ASan bot so we can have an assert here.
    tests.append(AndroidPerfTest(
        'webrtc_perf_tests',
        args=['--save_worst_frame'],
        revision=revision,
        revision_number=api.revision_number,
        perf_id=api.c.PERF_ID,
        upload_test_artifacts=True))

    tests.append(PerfTest(
        str(api.m.path['checkout'].join('audio', 'test',
                                        'low_bandwidth_audio_test.py')),
        name='low_bandwidth_audio_test',
        args=[api.m.chromium.output_dir, '--remove',
              '--android', '--adb-path', api.m.adb.adb_path()],
        revision=revision,
        revision_number=api.revision_number,
        perf_id=api.c.PERF_ID))

    # Skip video_quality_loopback_test on Android K bot (not supported).
    # TODO(oprypin): Re-enable on Nexus 4 once webrtc:7724 is fixed.
    if 'kitkat' not in api.c.PERF_ID and 'nexus4' not in api.c.PERF_ID:
      tests.append(PerfTest(
          str(api.m.path['checkout'].join('examples', 'androidtests',
                                          'video_quality_loopback_test.py')),
          name='video_quality_loopback_test',
          args=['--adb-path', api.m.adb.adb_path(), build_out_dir],
          revision=revision,
          revision_number=api.revision_number,
          perf_id=api.c.PERF_ID))

  elif test_suite == 'android':
    for test, extra_args in sorted(ANDROID_DEVICE_TESTS.items() +
                                   ANDROID_INSTRUMENTATION_TESTS.items()):
      tests.append(AndroidTest(test, **extra_args))
    for test, extra_args in sorted(ANDROID_JUNIT_TESTS.items()):
      if api.mastername == 'client.webrtc.fyi':
        tests.append(AndroidTest(test, **extra_args))
      else:
        tests.append(AndroidJunitTest(test))

    # TODO(bugs.webrtc.org/8724): Re-enable when gradle mirror is fixed.
    # if api.should_test_android_studio_project_generation:
    #    tests.append(PythonTest(
    #       test='gradle_project_test',
    #       script=str(api.m.path['checkout'].join('examples',  'androidtests',
    #                                              'gradle_project_test.py')),
    #       args=[build_out_dir],
    #       env={'GOMA_DISABLED': True}))
    if api.m.tryserver.is_tryserver:
      tests.append(AndroidTest(
          'webrtc_perf_tests',
          args=['--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/']))

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

  def pre_run(self, api, suffix):
    return []

  def run(self, api, suffix): # pragma: no cover:
    raise NotImplementedError()

  def post_run(self, api, suffix):
    return []


class BaremetalTest(Test):
  """A WebRTC test that uses audio and/or video devices."""
  def __init__(self, test, name=None, revision=None, parallel=False,
               gtest_args=None, args=None, **runtest_kwargs):
    super(BaremetalTest, self).__init__(test, name)
    self._parallel = parallel
    self._args = args or []
    self._gtest_args = gtest_args or []
    self._revision = revision
    self._runtest_kwargs = runtest_kwargs

  def run(self, api, suffix):
    test_type = self._test
    test = api.m.path['checkout'].join('tools_webrtc',
                                       'gtest-parallel-wrapper.py')
    test_ext = '.exe' if api.m.platform.is_win else ''
    test_executable = api.m.chromium.c.build_dir.join(
      api.m.chromium.c.build_config_fs, self._test + test_ext)

    args = [test_executable]
    if not self._parallel:
      args.append('--workers=1')
    args += self._gtest_args
    if self._args:
      args += ['--'] + self._args

    api.m.chromium.runtest(
        test=test, args=args, name=self._name, annotate=None, xvfb=True,
        flakiness_dash=False, python_mode=True, revision=self._revision,
        test_type=test_type, **self._runtest_kwargs)


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
  def __init__(self, test, args=None, **kwargs):
    args = list(args or [])
    args.append('--chartjson-result-file=${ISOLATED_OUTDIR}/perf_result.json')
    super(SwarmingAndroidPerfTest, self).__init__(test, args=args)

  def _get_perf_data(self, api, task_output_dir):
    if api.webrtc._test_data.enabled:
      return {
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
      return api.json.loads(task_output_dir['0/perf_result.json'])

  @composite_step
  def _upload_to_perf_dashboard(self, api, perf_results):
    perf_results['benchmark_name'] = self.name

    args = [
        '--build-dir', api.path['checkout'].join('out'),
        '--buildername', api.properties['buildername'],
        '--buildnumber', api.properties['buildnumber'],
        '--name', self.name,
        '--perf-id', api.webrtc.c.PERF_ID,
        '--results-file', api.json.input(perf_results),
        '--results-url', DASHBOARD_UPLOAD_URL,
    ]

    if 'got_revision_cp' in api.properties:
      args.extend(['--got-revision-cp', api.properties['got_revision_cp']])
    if 'git_revision' in api.properties:
      args.extend(['--git-revision', api.properties['git_revision']])

    args.append('--output-json-dashboard-url')
    args.append(api.json.output(add_json_log=False, name='dashboard_url'))

    step_result = api.build.python(
        '%s Dashboard Upload' % self.name,
        api.chromium.package_repo_resource(
            'scripts', 'slave', 'upload_perf_dashboard_results.py'),
        args,
        step_test_data=(
            lambda: api.json.test_api.output('chromeperf.appspot.com',
                                             name='dashboard_url') +
            api.json.test_api.output({})))

    step_result.presentation.links['Results Dashboard'] = (
        step_result.json.outputs.get('dashboard_url', ''))

  def post_run(self, api, suffix):
    try:
      super(SwarmingGTestTest, self).post_run(api, suffix)
    finally:
      step_result = api.step.active_result
      task_output_dir = api.step.active_result.raw_io.output_dir
      logcats = _MergeFiles(task_output_dir, 'logcats')
      step_result.presentation.logs['logcats'] = logcats.splitlines()

      self._upload_to_perf_dashboard(api,
                                     self._get_perf_data(api, task_output_dir))

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


class SwarmingPerfTest(SwarmingIsolatedScriptTest):
  def __init__(self, name, api, **kwargs):
    super(SwarmingPerfTest, self).__init__(name, **kwargs)
    self._buildername = api.m.properties.get('buildername')
    self._buildnumber = api.m.properties.get('buildnumber')
    self._perf_config = PERF_CONFIG.copy()
    self._perf_config['r_webrtc_git'] = api.revision
    self._perf_config = api.m.json.dumps(self._perf_config)
    self._perf_id = api.c.PERF_ID
    self._revision = api.revision_number
    self._name = name
    self._upload_script = api.resource('upload_to_perf_dashboard.py')

  def post_run(self, api, suffix):
    try:
      # We have to call super of SwarmingIsolatedScriptTest since we need access
      # to the swarming collect step's output_dir data.
      super(SwarmingIsolatedScriptTest, self).post_run(api, suffix)
    finally:
      task_output_dir = api.step.active_result.raw_io.output_dir
      logs_file = api.raw_io.input_text(
          _MergeFiles(task_output_dir, 'passed-tests.log'))
      api.python('Upload perf results',
                 script=self._upload_script,
                 args=[
                     '--buildername', self._buildername,
                     '--buildnumber', self._buildnumber,
                     '--perf_id', self._perf_id,
                     '--perf_config', self._perf_config,
                     '--revision', self._revision,
                     '--test_name', self._name,
                     '--url', DASHBOARD_UPLOAD_URL,
                     '--logs_file', logs_file,
                 ])

      # Copied from SwarmingIsolatedScriptTest.post_run
      results = self._isolated_script_results
      if results and self._upload_test_results:
        self.results_handler.upload_results(
            api, results, self._step_name(suffix), suffix)


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
    with api.m.depot_tools.on_path():
      api.m.chromium.runtest(
          test=self._test, name=self._name, args=self._args,
          results_url=DASHBOARD_UPLOAD_URL, annotate='graphing', xvfb=True,
          perf_dashboard_id=self._name, test_type=self._name,
          revision=self._revision_number, perf_id=self._perf_id,
          perf_config=self._perf_config, python_mode=self._python_mode)


class AndroidJunitTest(Test):
  """Runs an Android Junit test."""

  def run(self, api, suffix):
    api.m.chromium_android.run_java_unit_test_suite(self._name)


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
    gtest_results_file = api.m.test_utils.gtest_results(add_json_log=False)
    self._args.extend(['--gs-test-artifacts-bucket', api.WEBRTC_GS_BUCKET,
                       '--json-results-file', gtest_results_file])

  def _upload_test_artifacts(self, api):
    step_result = api.m.step.active_result
    if (hasattr(step_result, 'test_utils') and
        hasattr(step_result.test_utils, 'gtest_results')):
      json_results = api.m.json.input(step_result.test_utils.gtest_results.raw)
      details_link = api.m.chromium_android.create_result_details(
          self._name, json_results)
      api.m.step.active_result.presentation.links['result_details'] = (
          details_link)

  @composite_step
  def run(self, api, suffix):
    wrapper_script = api.m.chromium.output_dir.join('bin',
                                                    'run_%s' % self._name)
    self._test = wrapper_script
    if self._should_upload_test_artifacts:
      self._prepare_test_artifacts_upload(api)
    try:
      super(AndroidPerfTest, self).run(api, suffix)
    finally:
      if self._should_upload_test_artifacts:
        self._upload_test_artifacts(api)
