# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class WebRTCApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(WebRTCApi, self).__init__(**kwargs)
    self._env = {}

  COMMON_TESTS = [
      'audio_decoder_unittests',
      'common_audio_unittests',
      'common_video_unittests',
      'modules_tests',
      'modules_unittests',
      'neteq_unittests',
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

  def add_normal_tests(self):
    c = self.m.chromium

    for test in self.NORMAL_TESTS:
      yield c.runtest(test)

    if self.m.platform.is_mac and self.m.platform.bits == 64:
      yield c.runtest(('libjingle_peerconnection_objc_test.app/Contents/MacOS/'
                       'libjingle_peerconnection_objc_test'),
                      name='libjingle_peerconnection_objc_test'),

  def add_baremetal_tests(self):
    """Adds baremetal tests, which are different depending on the platform."""
    c = self.m.chromium

    if self.m.platform.is_win or self.m.platform.is_mac:
      yield c.runtest('audio_device_tests')
    elif self.m.platform.is_linux:
      yield (
        c.runtest('audioproc', name='audioproc_perf',
                  args=['-aecm', '-ns', '-agc', '--fixed_digital', '--perf',
                        '-pb', self.m.path['checkout'].join(
                          'resources/audioproc.aecdump')]),
        c.runtest('iSACFixtest', name='isac_fixed_perf',
                  args=['32000', self.m.path['checkout'].join(
                          'resources/speech_and_misc_wb.pcm'),
                        'isac_speech_and_misc_wb.pcm']),
        c.runtest('libjingle_peerconnection_java_unittest',
                  env={'LD_PRELOAD':
                       '/usr/lib/x86_64-linux-gnu/libpulse.so.0'}),
      )

    yield (
      c.runtest('vie_auto_test', args=[
        '--automated',
        '--capture_test_ensure_resolution_alignment_in_capture_device=false']),
      c.runtest('voe_auto_test', args=['--automated']),
      c.runtest('video_capture_tests'),
      c.runtest('webrtc_perf_tests'),
    )

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
