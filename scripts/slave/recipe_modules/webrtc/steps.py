# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze


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

ANDROID_DEVICE_TESTS = (
  'audio_decoder_unittests',
  'common_audio_unittests',
  'common_video_unittests',
  'modules_tests',
  'modules_unittests',
  'ortc_unittests',
  'peerconnection_unittests',
  'rtc_stats_unittests',
  'rtc_unittests',
  'system_wrappers_unittests',
  'test_support_unittests',
  'tools_unittests',
  'video_engine_tests',
  'voice_engine_unittests',
  'webrtc_nonparallel_tests',
)

ANDROID_INSTRUMENTATION_TESTS = (
  'AppRTCMobileTest',
  'libjingle_peerconnection_android_unittest',
)

ANDROID_JUNIT_TESTS = (
  'android_junit_tests',
)

ANDROID_EXPERIMENTAL_TESTS = (
  'AppRTCMobileTestStubbedVideoIO',
)

ANDROID_CIPD_PACKAGES = [
    ("bin",
     "infra/tools/luci/logdog/butler/${platform}",
     "git_revision:ff387eadf445b24c935f1cf7d6ddd279f8a6b04c",
    )
]


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
      tests.append(WebRTCTest(
          'modules_tests',
          name='modules_tests (screen capture disabled tests)',
          args=['--gtest_filter=ScreenCapturerIntegrationTest.*',
                '--gtest_also_run_disabled_tests'],
          parallel=True))
  elif test_suite == 'webrtc_baremetal':
    api.virtual_webcam_check()  # Needed for video_capture_tests below.

    tests.extend([
        BaremetalTest('voe_auto_test', revision=revision, args=['--automated']),
        BaremetalTest('video_capture_tests', revision=revision),
    ])

    if api.m.tryserver.is_tryserver and not api.m.platform.is_mac:
      tests.append(BaremetalTest('webrtc_perf_tests', revision=revision,
          args=['--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/']))
  elif test_suite == 'desktop_perf':
    assert api.c.PERF_ID
    if api.m.platform.is_linux:
      f = api.m.path['checkout'].join
      tests.append(
          PerfTest('isac_fix_test',
                   revision=revision,
                   args=['32000', f('resources', 'speech_and_misc_wb.pcm'),
                         'isac_speech_and_misc_wb.pcm']),
      )

    tests.append(PerfTest('webrtc_perf_tests', revision=revision))

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
    if 'kitkat' not in api.c.PERF_ID:
      tests.append(PerfTest(
          str(api.m.path['checkout'].join('webrtc', 'examples', 'androidtests',
                                          'video_quality_loopback_test.py')),
          name='video_quality_loopback_test',
          args=['--adb-path', api.m.adb.adb_path(), build_out_dir],
          revision=revision))

  elif test_suite == 'android':
    for test in (ANDROID_DEVICE_TESTS +
                 ANDROID_INSTRUMENTATION_TESTS):
      tests.append(GTestTest(test, enable_swarming=enable_swarming,
                             override_isolate_target=test,
                             cipd_packages=ANDROID_CIPD_PACKAGES))
    for test in ANDROID_JUNIT_TESTS:
      if api.mastername == 'client.webrtc.fyi':
        tests.append(GTestTest(test, enable_swarming=enable_swarming,
                               override_isolate_target=test))
      else:
        tests.append(AndroidJunitTest(test))

    if api.should_test_android_studio_project_generation:
       tests.append(WebRTCTest(
          name='gradle_project_test',
          test=str(api.m.path['checkout'].join(
            'webrtc', 'examples',  'androidtests', 'gradle_project_test.py')),
          args=[build_out_dir],
          parallel=False))
    if api.m.tryserver.is_tryserver:
      tests.append(GTestTest(
          'webrtc_perf_tests',
          enable_swarming=enable_swarming,
          override_isolate_target='webrtc_perf_tests',
          cipd_packages=ANDROID_CIPD_PACKAGES,
          args=['--force_fieldtrials=WebRTC-QuickPerfTest/Enabled/']))
  elif test_suite == 'android_experimental':
    for test in ANDROID_EXPERIMENTAL_TESTS:
      tests.append(GTestTest(test, enable_swarming=enable_swarming,
                             override_isolate_target=test,
                             cipd_packages=ANDROID_CIPD_PACKAGES))

  return tests


# TODO(kjellander): Continue refactoring an integrate the classes in the
# chromium_tests recipe module instead (if possible).
class Test(object):
  def __init__(self, test, name=None, enable_swarming=False, shards=1):
    self._test = test
    self._name = name or test
    self._enable_swarming = enable_swarming
    self._swarming_task = None
    self._shards = shards

  def pre_run(self, api, suffix):
    return []

  def run(self, api, suffix): # pragma: no cover:
    raise NotImplementedError()

  def post_run(self, api, suffix):
    return []

class WebRTCTest(Test):
  """A normal WebRTC desktop test."""
  def __init__(self, test, name=None, revision=None, enable_swarming=False,
               shards=1, parallel=True, perf_test=False,
               **runtest_kwargs):
    super(WebRTCTest, self).__init__(test, name, enable_swarming, shards)
    self._revision = revision
    self._parallel = parallel
    self._perf_test = perf_test
    self._runtest_kwargs = runtest_kwargs

  def run(self, api, suffix):
    api.add_test(self._test, name=self._name, revision=self._revision,
                 parallel=self._parallel, perf_test=self._perf_test,
                 **self._runtest_kwargs)

class BaremetalTest(WebRTCTest):
  """A WebRTC test that uses audio and/or video devices."""
  def __init__(self, test, name=None, revision=None, perf_test=False, **kwargs):
    # Tests accessing hardware devices shouldn't be run in parallel.
    super(BaremetalTest, self).__init__(test, name, revision=revision,
                                        parallel=False, perf_test=perf_test,
                                        **kwargs)
    if perf_test:
      assert revision, 'Revision is mandatory for perf tests'

class PerfTest(BaremetalTest):
  """A WebRTC test that needs consistent hardware performance."""
  def __init__(self, test, name=None, revision=None, **kwargs):
    super(PerfTest, self).__init__(test, name, revision=revision,
                                   perf_test=True, **kwargs)

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
    super(AndroidPerfTest, self).__init__(test, name, revision)

  def run(self, api, suffix):
    wrapper_script = api.m.chromium.output_dir.join('bin',
                                                    'run_%s' % self._name)
    args = ['--verbose']
    api.add_test(name=self._name,
                 test=wrapper_script,
                 args=args,
                 revision=self._revision,
                 python_mode=True,
                 perf_test=self._perf_test,
                 perf_dashboard_id=self._name)

