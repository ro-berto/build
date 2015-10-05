# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


def generate_tests(api, test_suite):
  tests = []
  if test_suite in ('webrtc', 'webrtc_parallel'):
    parallel = test_suite.endswith('_parallel')
    for test in api.NORMAL_TESTS:
      tests.append(WebRTCTest(test, parallel=parallel))

    if api.m.platform.is_mac and api.m.chromium.c.TARGET_BITS == 64:
      executable = api.m.path.join('libjingle_peerconnection_objc_test.app',
                                   'Contents', 'MacOS',
                                   'libjingle_peerconnection_objc_test')
      tests.append(WebRTCTest(name='libjingle_peerconnection_objc_test',
                              custom_executable=executable, parallel=parallel,
                              disable_swarming=True))
  elif test_suite == 'webrtc_baremetal':
    # Add baremetal tests, which are different depending on the platform.
    if api.m.platform.is_win or api.m.platform.is_mac:
      tests.append(BaremetalTest('audio_device_tests'))
    elif api.m.platform.is_linux:
      f = api.m.path['checkout'].join
      tests.extend([
          BaremetalTest('audioproc',
                        args=['-aecm', '-ns', '-agc', '--fixed_digital',
                              '--perf', '-pb',
                              f('resources', 'audioproc.aecdump')],
                        perf_test=True),
          BaremetalTest('isac_fix_test',
                        args=['32000', f('resources', 'speech_and_misc_wb.pcm'),
                              'isac_speech_and_misc_wb.pcm'],
                        perf_test=True),
          WebCamTest('libjingle_peerconnection_java_unittest',
              env={'LD_PRELOAD': '/usr/lib/x86_64-linux-gnu/libpulse.so.0'}),
      ])

    tests.extend([
        BaremetalTest('voe_auto_test', args=['--automated']),
        WebCamTest('video_capture_tests'),
        BaremetalTest('webrtc_perf_tests',
                      perf_test=True),
    ])
  elif test_suite == 'chromium':
    # Add WebRTC-specific browser tests that don't run in the main Chromium
    # waterfalls (marked as MANUAL_) since they rely on special setup and/or
    # physical audio/video devices.
    tests.extend([
        WebRTCTest('content_browsertests',
                   args=['--gtest_filter=WebRtc*', '--run-manual',
                         '--test-launcher-print-test-stdio=always',
                         '--test-launcher-bot-mode'],
                   perf_test=True),
        WebRTCTest('browser_tests',
            # These tests needs --test-launcher-jobs=1 since some of them are
            # not able to run in parallel (due to the usage of the
            # peerconnection server).
            # TODO(phoglund): increasing timeout for the HD video quality test.
            # The original timeout was 300000. See http://crbug.com/476865.
            args = ['--gtest_filter=%s' % api.BROWSER_TESTS_GTEST_FILTER,
                    '--run-manual', '--ui-test-action-max-timeout=350000',
                    '--test-launcher-jobs=1',
                    '--test-launcher-bot-mode',
                    '--test-launcher-print-test-stdio=always'],
            # The WinXP tester doesn't run the audio quality perf test.
            perf_test='xp' not in api.c.PERF_ID),
        WebRTCTest('content_unittests'),
    ])
  elif test_suite == 'android':
    for test, isolate_file_path in sorted(api.ANDROID_APK_TESTS.iteritems()):
      tests.append(AndroidTest(test, isolate_path=isolate_file_path))
    for test, isolate_file_path in sorted(
        api.ANDROID_APK_PERF_TESTS.iteritems()):
      tests.append(AndroidPerfTest(test, isolate_path=isolate_file_path,
                                   perf_id=api.c.PERF_ID))
    for test, apk_under_test in api.ANDROID_INSTRUMENTATION_TESTS.items():
      tests.append(AndroidInstrumentationTest(test, apk_under_test))

  return tests


# TODO(kjellander): Continue refactoring an integrate the classes in the
# chromium_tests recipe module instead (if possible).
class WebRTCTest(object):
  """A normal WebRTC desktop test."""
  def __init__(self, name, parallel=False, perf_test=False,
               custom_executable=None, disable_swarming=False,
               **runtest_kwargs):
    self.name = name
    self.parallel = parallel
    self.custom_executable = custom_executable
    self.perf_test = perf_test
    self.disable_swarming = disable_swarming
    self.runtest_kwargs = runtest_kwargs

  def run(self, api, suffix):
    self.runtest_kwargs['test'] = self.custom_executable or self.name
    api.add_test(name=self.name, parallel=self.parallel,
                 perf_test=self.perf_test,
                 disable_swarming=self.disable_swarming, **self.runtest_kwargs)


class BaremetalTest(WebRTCTest):
  """A WebRTC desktop test that uses audio and/or video devices."""
  def __init__(self, name, perf_test=False, **runtest_kwargs):
    # Tests accessing hardware devices shouldn't be run in parallel.
    super(BaremetalTest, self).__init__(name, parallel=False,
                                        perf_test=perf_test, **runtest_kwargs)


class WebCamTest(WebRTCTest):
  def __init__(self, name, **runtest_kwargs):
    # Tests accessing the Webcam shouldn't be run in parallel.
    super(WebCamTest, self).__init__(name, parallel=False, **runtest_kwargs)

  def run(self, api, suffix):
    api.virtual_webcam_check()
    super(WebCamTest, self).run(api, suffix)


class AndroidTest(object):
  def __init__(self, name, isolate_path):
    self.name = name
    self.isolate_path = isolate_path

  def run(self, api, suffix):
    # Use absolute path here to avoid the Chromium hardcoded fallback in
    # src/build/android/pylib/base/base_setup.py.
    isolate_path = api.m.path['checkout'].join(self.isolate_path)
    api.m.chromium_android.run_test_suite(self.name,
                                          isolate_file_path=isolate_path)


class AndroidInstrumentationTest(object):
  """Installs the APK on the device and runs the test."""
  def __init__(self, name, apk_under_test=None):
    self.name = name
    self.apk_under_test = apk_under_test

  def run(self, api, suffix):
    if self.apk_under_test:
      api._adb_install_apk(self.apk_under_test)
    api.m.chromium_android.run_instrumentation_suite(test_apk=self.name,
                                                     verbose=True)


class AndroidPerfTest(object):
  """A performance test to run on Android devices.

    Basically just wrap what happens in chromium_android.run_test_suite to run
    inside runtest.py so we can scrape perf data. This way we can get perf data
    from the gtest binaries since the way of running perf tests with telemetry
    is entirely different.
    """
  def __init__(self, name, isolate_path, perf_id=None):
    self.name = name
    self.isolate_path = isolate_path
    self.perf_id = perf_id

  def run(self, api, suffix):
    # Use absolute path here to avoid the Chromium hardcoded fallback in
    # src/build/android/pylib/base/base_setup.py.
    isolate_path = api.m.path['checkout'].join(self.isolate_path)

    if not self.perf_id or api.m.chromium.c.BUILD_CONFIG == 'Debug':
      # Run as a normal test for trybots and Debug, without perf data scraping.
      api.m.chromium_android.run_test_suite(self.name,
                                            isolate_file_path=isolate_path)
    else:
      args = ['gtest', '-s', self.name, '--verbose', '--release',
              '--isolate-file-path', isolate_path]
      api.add_test(name=self.name, test=api.m.chromium_android.c.test_runner,
                   args=args,
                   perf_test=True,
                   perf_dashboard_id=self.name)

