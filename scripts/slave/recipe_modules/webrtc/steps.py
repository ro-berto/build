# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

from recipe_engine.types import freeze
from recipe_engine.recipe_api import composite_step

THIS_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(THIS_DIR)))

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
    'swarming_shards': 2,
  },
  'modules_unittests': {
    'swarming_shards': 6,
  },
  'ortc_unittests': {},
  'peerconnection_unittests': {
    'swarming_shards': 4,
  },
  'rtc_stats_unittests': {},
  'rtc_unittests': {
    'swarming_shards': 6,
  },
  'system_wrappers_unittests': {},
  'test_support_unittests': {},
  'tools_unittests': {},
  'video_engine_tests': {
    'swarming_shards': 4,
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

PERF_TESTS = (
  # TODO(ehmaldonado): Add isac_fix_test and low_bandwidth_audio_test. See
  # http://crbug.com/755660.
  'webrtc_perf_tests',
)


def generate_tests(api, test_suite, revision, enable_swarming=False):
  tests = []
  build_out_dir = api.m.path['checkout'].join(
      'out', api.m.chromium.c.build_config_fs)
  GTestTest = api.m.chromium_tests.steps.GTestTest

  SwarmingTest = api.m.chromium_tests.steps.SwarmingIsolatedScriptTest
  if test_suite == 'webrtc':
    for test, extra_args in sorted(NORMAL_TESTS.items()):
      tests.append(SwarmingTest(test, **extra_args))
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
        BaremetalTest('voe_auto_test', revision=revision, args=['--automated']),
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
    for test in sorted(PERF_TESTS):
      tests.append(SwarmingPerfTest(test, api))
      # TODO(ehmaldonado): Collect and upload perf results
  elif test_suite == 'desktop_perf':
    assert api.c.PERF_ID
    if api.m.platform.is_linux:
      tests.append(PerfTest(
          'isac_fix_test',
          revision=revision,
          args=[
              '32000', api.m.path['checkout'].join(
                  'resources', 'speech_and_misc_wb.pcm'),
              'isac_speech_and_misc_wb.pcm']))
    tests.append(PerfTest('webrtc_perf_tests', revision=revision,
                          args=['--save_worst_frame'],
                          upload_test_output=True))

    # TODO(kjellander): Re-enable when https://crbug.com/731717 is fixed.
    if not api.m.platform.is_win:
      tests.append(PerfTest(
          str(api.m.path['checkout'].join('webrtc', 'audio', 'test',
                                          'low_bandwidth_audio_test.py')),
          name='low_bandwidth_audio_test',
          args=[api.m.chromium.output_dir, '--remove'],
          revision=revision))
  elif test_suite == 'android_perf' and api.c.PERF_ID:
    # TODO(kjellander): Fix the Android ASan bot so we can have an assert here.
    tests.append(AndroidPerfTest('webrtc_perf_tests', revision=revision))

    tests.append(PerfTest(
        str(api.m.path['checkout'].join('webrtc', 'audio', 'test',
                                        'low_bandwidth_audio_test.py')),
        name='low_bandwidth_audio_test',
        args=[api.m.chromium.output_dir, '--remove',
              '--android', '--adb-path', api.m.adb.adb_path()],
        revision=revision))

    # Skip video_quality_loopback_test on Android K bot (not supported).
    # TODO(oprypin): Re-enable on Nexus 4 once webrtc:7724 is fixed.
    if 'kitkat' not in api.c.PERF_ID and 'nexus4' not in api.c.PERF_ID:
      tests.append(PerfTest(
          str(api.m.path['checkout'].join('webrtc', 'examples', 'androidtests',
                                          'video_quality_loopback_test.py')),
          name='video_quality_loopback_test',
          args=['--adb-path', api.m.adb.adb_path(), build_out_dir],
          revision=revision))

  elif test_suite == 'android':
    for test, extra_args in sorted(ANDROID_DEVICE_TESTS.items() +
                                   ANDROID_INSTRUMENTATION_TESTS.items()):
      tests.append(GTestTest(test, enable_swarming=enable_swarming,
                             override_isolate_target=test,
                             cipd_packages=ANDROID_CIPD_PACKAGES, **extra_args))
    for test, extra_args in sorted(ANDROID_JUNIT_TESTS.items()):
      if api.mastername == 'client.webrtc.fyi':
        tests.append(GTestTest(test, enable_swarming=enable_swarming,
                               override_isolate_target=test, **extra_args))
      else:
        tests.append(AndroidJunitTest(test))

    if api.should_test_android_studio_project_generation:
       tests.append(PythonTest(
          test='gradle_project_test',
          script=str(api.m.path['checkout'].join(
            'webrtc', 'examples',  'androidtests', 'gradle_project_test.py')),
          args=[build_out_dir],
          env={'GOMA_DISABLED': True}))
    if api.m.tryserver.is_tryserver:
      tests.append(GTestTest(
          'webrtc_perf_tests',
          enable_swarming=enable_swarming,
          override_isolate_target='webrtc_perf_tests',
          cipd_packages=ANDROID_CIPD_PACKAGES,
          args=['--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/']))

  return tests


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


class PythonTest(Test):
  def __init__(self, test, script, args, env):
    super(PythonTest, self).__init__(test)
    self._script = script
    self._args = args
    self._env = env or {}

  def run(self, api, suffix):
    with api.m.context(env=self._env):
      api.m.python(self._test, self._script, self._args)


class SwarmingPerfTest(SwarmingIsolatedScriptTest):
  def __init__(self, name, api, shards=1):
    super(SwarmingPerfTest, self).__init__(name, shards=shards)
    self._buildername = api.m.properties.get('buildername')
    self._buildnumber = api.m.properties.get('buildnumber')
    self._perf_config = PERF_CONFIG.copy()
    self._perf_config['r_webrtc_git'] = api.revision
    self._perf_config = api.m.json.dumps(self._perf_config)
    self._perf_id = api.c.PERF_ID
    self._revision = api.revision_number
    self._name = name
    self._upload_script = api.resource('upload_to_perf_dashboard.py')

  def _merge_test_logs(self, task_output_files):
    all_logs = ""
    for file_name, contents in task_output_files.iteritems():
      # TODO(ehmaldonado): Make it possible to add custom test data to the
      # collected task dir.
      if file_name.endswith('passed-tests.log'): # pragma: no cover
        all_logs += contents
    return all_logs

  def post_run(self, api, suffix):
    try:
      # We have to call super of SwarmingIsolatedScriptTest since we need access
      # to the swarming collect step's output_dir data.
      super(SwarmingIsolatedScriptTest, self).post_run(api, suffix)
    finally:
      task_output_dir = api.step.active_result.raw_io.output_dir
      logs_file = api.raw_io.input_text(self._merge_test_logs(task_output_dir))
      api.python('Upload perf results',
                 script=self._upload_script,
                 args=[
                     '--buildername', self._buildername,
                     '--buildnumber', self._buildnumber,
                     '--perf_id', self._perf_id,
                     '--perf_config', self._perf_config,
                     '--revision', self._revision,
                     '--shards', self._shards,
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
               upload_test_output=False, **runtest_kwargs):
    super(PerfTest, self).__init__(test, name)
    assert revision, 'Revision is mandatory for perf tests'
    self._revision = revision
    self._args = args or []
    self._runtest_kwargs = runtest_kwargs
    self._upload_test_output = upload_test_output

  @composite_step
  def run(self, api, suffix):
    perf_dashboard_id = self._name
    assert api.revision_number, (
        'A revision number must be specified for perf tests as they upload '
        'data to the perf dashboard.')
    perf_config = PERF_CONFIG
    perf_config['r_webrtc_git'] = api.revision
    test_output_name = self._name + '_test_output'
    upload_url = '%s/%s/%s_%s.zip' % (
        api.mastername, api.buildername, test_output_name, api.revision_number)
    with api.m.tempfile.temp_dir(test_output_name) as test_output_path:
      if self._upload_test_output:
        self._args.extend(['--test_output_dir', test_output_path])
      api.m.chromium.runtest(
          test=self._test, name=self._name, args=self._args,
          results_url=DASHBOARD_UPLOAD_URL, annotate='graphing', xvfb=True,
          perf_dashboard_id=perf_dashboard_id, test_type=perf_dashboard_id,
          revision=api.revision_number, perf_id=api.c.PERF_ID,
          perf_config=perf_config, **self._runtest_kwargs)
      if (self._upload_test_output and
          api.m.file.listdir('listdir ' + test_output_name, test_output_path)):
        zip_path = api.m.path['tmp_base'].join(test_output_name + '.zip')
        api.m.zip.directory('zip ' + test_output_name, test_output_path,
                            zip_path)
        api.m.gsutil.upload(zip_path, api.WEBRTC_GS_BUCKET, upload_url,
                            args=['-a', 'public-read'],
                            unauthenticated_url=True)


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

  def __init__(self, test, name=None, revision=None):
    super(AndroidPerfTest, self).__init__(test, name, args=['--verbose'],
                                          revision=revision, python_mode=True)

  def run(self, api, suffix):
    wrapper_script = api.m.chromium.output_dir.join('bin',
                                                    'run_%s' % self._name)
    self._test = wrapper_script
    super(AndroidPerfTest, self).run(api, suffix)
