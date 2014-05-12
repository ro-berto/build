# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave.recipe_modules.webrtc import builders


class WebRTCApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(WebRTCApi, self).__init__(**kwargs)
    self._env = {}

  BUILDERS = builders.BUILDERS
  RECIPE_CONFIGS = builders.RECIPE_CONFIGS

  COMMON_TESTS = [
      'audio_decoder_unittests',
      'common_audio_unittests',
      'common_video_unittests',
      'modules_tests',
      'modules_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_engine_core_unittests',
      'voice_engine_unittests',
  ]

  ANDROID_APK_TESTS = COMMON_TESTS

  NORMAL_TESTS = sorted(COMMON_TESTS + [
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_sound_unittest',
    'libjingle_unittest',
    'video_engine_tests',
  ])

  DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'

  def runtests(self, test_suite='default'):
    """Generate a list of tests to run."""
    steps = []
    if test_suite == 'default':
      for test in self.NORMAL_TESTS:
        steps.append(self.add_test(test))

      if self.m.platform.is_mac and self.m.chromium.c.TARGET_BITS == 64:
        test = self.m.path.join('libjingle_peerconnection_objc_test.app',
                                'Contents', 'MacOS',
                                'libjingle_peerconnection_objc_test')
        steps.append(self.add_test(test,
                                    name='libjingle_peerconnection_objc_test'))
    elif test_suite == 'baremetal':
      # Add baremetal tests, which are different depending on the platform.
      if self.m.platform.is_win or self.m.platform.is_mac:
        steps.append(self.add_test('audio_device_tests'))
      elif self.m.platform.is_linux:
        f = self.m.path['checkout'].join
        steps.append(self.add_test(
            'audioproc', name='audioproc_perf',
            args=['-aecm', '-ns', '-agc', '--fixed_digital', '--perf', '-pb',
                  f('resources', 'audioproc.aecdump')]))
        steps.append(self.add_test(
            'iSACFixtest', name='isac_fixed_perf',
            args=['32000', f('resources', 'speech_and_misc_wb.pcm'),
                  'isac_speech_and_misc_wb.pcm']))
        steps.append(self.virtual_webcam_check())
        steps.append(self.add_test(
            'libjingle_peerconnection_java_unittest',
            env={'LD_PRELOAD': '/usr/lib/x86_64-linux-gnu/libpulse.so.0'}))

      steps.append(self.virtual_webcam_check())
      steps.append(self.add_test('vie_auto_test',
          args=['--automated',
                '--capture_test_ensure_resolution_alignment_in_capture_device='
                'false']))
      steps.append(self.add_test('voe_auto_test', args=['--automated']))
      steps.append(self.virtual_webcam_check())
      steps.append(self.add_test('video_capture_tests'))
      steps.append(self.add_test('webrtc_perf_tests'))

    return steps

  def add_test(self, test, name=None, args=None, env=None):
    args = args or []
    env = env or {}

    if self.c.MEASURE_PERF:
      return self.m.chromium.runtest(
          test=test, args=args, name=name,
          results_url=self.DASHBOARD_UPLOAD_URL, annotate='graphing',
          xvfb=True, perf_dashboard_id=test, test_type=test, env=env,
          revision=self.m.properties['revision'])
    else:
      return self.m.chromium.runtest(
          test=test, args=args, name=name, annotate='gtest', xvfb=True,
              test_type=test, env=env)

  def apply_svn_patch(self):
    script = self.m.path['build'].join('scripts', 'slave', 'apply_svn_patch.py')
    # Use the SVN mirror as the slaves only have authentication setup for that.
    patch_url = self.m.properties['patch_url'].replace(
        'svn://svn.chromium.org', 'svn://svn-mirror.golo.chromium.org')
    args = ['-p', patch_url,
            '-r', self.c.patch_root_dir]

    # Allow manipulating patches for try jobs.
    if self.c.patch_filter_script and self.c.patch_path_filter:
      args += ['--filter-script', self.c.patch_filter_script,
               '--strip-level', self.c.patch_strip_level,
               '--', '--path-filter', self.c.patch_path_filter]
    return self.m.python('apply_patch', script, args)

  def virtual_webcam_check(self):
    return self.m.python(
      'webcam_check',
      self.m.path['build'].join('scripts', 'slave', 'webrtc',
                                'ensure_webcam_is_running.py'))
