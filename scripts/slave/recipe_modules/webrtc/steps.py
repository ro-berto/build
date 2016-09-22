# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


def generate_tests(api, test_suite, revision, enable_swarming=False):
  tests = []
  if test_suite == 'webrtc':
    for test in api.NORMAL_TESTS:
      tests.append(WebRTCTest(test, revision,
                              enable_swarming=enable_swarming))
    tests.append(WebRTCTest('webrtc_nonparallel_tests', revision,
                            parallel=False,
                            enable_swarming=False))
  elif test_suite == 'webrtc_baremetal':
    if api.m.platform.is_linux:
      f = api.m.path['checkout'].join
      tests.extend([
          BaremetalTest('audioproc',
                        revision,
                        args=['-aecm', '-ns', '-agc', '--fixed_digital',
                              '--perf', '-pb',
                              f('resources', 'audioproc.aecdump')],
                        perf_test=True),
          BaremetalTest('isac_fix_test',
                        revision,
                        args=['32000', f('resources', 'speech_and_misc_wb.pcm'),
                              'isac_speech_and_misc_wb.pcm'],
                        perf_test=True),
      ])

    api.virtual_webcam_check()  # Needed for video_capture_tests below.

    # This test currently fails on Trusty Linux due to pulseaudio issues. See
    # http://crbug.com/589101
    if api.m.platform.is_mac or api.m.platform.is_win:
      tests.append(BaremetalTest('audio_device_tests', revision))

    tests.extend([
        BaremetalTest('voe_auto_test', revision, args=['--automated']),
        BaremetalTest('video_capture_tests', revision),
    ])
    if not api.m.tryserver.is_tryserver:
      tests.append(BaremetalTest('webrtc_perf_tests', revision, perf_test=True))

  elif test_suite == 'android':
    for test in api.ANDROID_APK_TESTS:
      tests.append(AndroidTest(test, enable_swarming))
    if (not api.m.tryserver.is_tryserver and api.c.PERF_ID and
        api.m.chromium.c.BUILD_CONFIG == 'Release'):
      tests.append(AndroidPerfTest('webrtc_perf_tests', revision,
                                   perf_id=api.c.PERF_ID))
    for test_name in api.ANDROID_INSTRUMENTATION_TESTS:
      tests.append(AndroidInstrumentationTest(test_name))

  return tests


# TODO(kjellander): Continue refactoring an integrate the classes in the
# chromium_tests recipe module instead (if possible).
class Test(object):
  def __init__(self, name, enable_swarming=False):
    self._name = name
    self._enable_swarming = enable_swarming
    self._swarming_task = None

  @property
  def name(self):  # pragma: no cover
    return self._name

  @property
  def enable_swarming(self):
    return self._enable_swarming

  @property
  def swarming_task(self):
    return self._swarming_task

  def run_nonswarming(self, api, suffix): # pragma: no cover:
    raise NotImplementedError()

  def run(self, api, suffix):
    if self._enable_swarming:
      isolated_hash = api.m.isolate.isolated_tests[self._name]
      self._swarming_task = api.m.swarming.task(self._name, isolated_hash)
      api.m.swarming.trigger_task(self._swarming_task)
    else:
      self.run_nonswarming(api, suffix)

class WebRTCTest(Test):
  """A normal WebRTC desktop test."""
  def __init__(self, name, revision, parallel=True, perf_test=False,
               custom_executable=None, enable_swarming=False,
               **runtest_kwargs):
    super(WebRTCTest, self).__init__(name, enable_swarming)
    self._revision = revision
    self._parallel = parallel
    self._custom_executable = custom_executable
    self._perf_test = perf_test
    self._runtest_kwargs = runtest_kwargs

  def run_nonswarming(self, api, suffix):
    self._runtest_kwargs['test'] = self._custom_executable or self._name
    api.add_test(name=self._name, revision=self._revision,
                 parallel=self._parallel, perf_test=self._perf_test,
                 **self._runtest_kwargs)


class BaremetalTest(WebRTCTest):
  """A WebRTC desktop test that uses audio and/or video devices."""
  def __init__(self, name, revision, perf_test=False, **runtest_kwargs):
    # Tests accessing hardware devices shouldn't be run in parallel.
    super(BaremetalTest, self).__init__(name, revision, parallel=False,
                                        perf_test=perf_test, **runtest_kwargs)


def get_android_tool(api):
  if api.m.chromium.c.gyp_env.GYP_DEFINES.get('asan', 0) == 1:
    return 'asan'
  return None


class AndroidTest(Test):
  def __init__(self, name, enable_swarming=False):
    super(AndroidTest, self).__init__(name, enable_swarming)
    self._swarming_task = None

  def run_nonswarming(self, api, suffix):
    api.m.chromium_android.run_test_suite(self._name,
                                          tool=get_android_tool(api))


class AndroidInstrumentationTest(Test):
  """Installs the APK on the device and runs the test."""

  def run_nonswarming(self, api, suffix):
    api.m.chromium_android.run_instrumentation_suite(
        name=self._name,
        wrapper_script_suite_name=self._name,
        tool=get_android_tool(api),
        verbose=True)


class AndroidPerfTest(Test):
  """A performance test to run on Android devices.

    Basically just wrap what happens in chromium_android.run_test_suite to run
    inside runtest.py so we can scrape perf data. This way we can get perf data
    from the gtest binaries since the way of running perf tests with telemetry
    is entirely different.
  """

  def __init__(self, name, revision, perf_id):
    super(AndroidPerfTest, self).__init__(name)
    self._revision = revision
    self._perf_id = perf_id
    assert perf_id, 'You must specify a Perf ID for builders running perf tests'

  def run_nonswarming(self, api, suffix):
    assert api.m.chromium.c.BUILD_CONFIG == 'Release', (
        'Perf tests should only be run with Release builds.')
    wrapper_script = api.m.chromium.output_dir.join('bin',
                                                    'run_%s' % self._name)
    args = ['--verbose']
    api.add_test(name=self._name,
                 test=wrapper_script,
                 args=args,
                 revision=self._revision,
                 python_mode=True,
                 perf_test=True,
                 perf_dashboard_id=self._name)

