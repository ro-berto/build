# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building and running tests for WebRTC stand-alone.

import functools


DEPS = [
  'archive',
  'depot_tools/bot_update',
  'chromium',
  'chromium_android',
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'recipe_engine/buildbucket',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'swarming',
  'test_utils',
  'webrtc',
]


def RunSteps(api):
  webrtc = api.webrtc
  webrtc.apply_bot_config(webrtc.BUILDERS, webrtc.RECIPE_CONFIGS)

  # TODO(kjellander): Remove when https://bugs.webrtc.org/7413 is fixed.
  if api.buildbucket.builder_name == 'Linux32 Release':
    step_result = api.step('Disabled: see https://bugs.webrtc.org/7413',
                           cmd=None)
    step_result.presentation.status = api.step.WARNING
    return

  webrtc.configure_swarming()
  if api.platform.is_win:
    api.chromium.taskkill()

  webrtc.checkout()
  if webrtc.should_download_audio_quality_tools:
    webrtc.download_audio_quality_tools()
  if webrtc.should_download_video_quality_tools:
    webrtc.download_video_quality_tools()
  webrtc.cleanup()

  if webrtc.bot.should_build:
    api.chromium.ensure_goma()
  if webrtc.bot.should_build or not webrtc.c.enable_swarming:
    api.chromium.runhooks()
  webrtc.check_swarming_version()
  webrtc.configure_isolate()

  if webrtc.bot.should_build:
    webrtc.compile()

  webrtc.get_binary_sizes()

  if webrtc.bot.should_upload_build:
    webrtc.package_build()
  if webrtc.bot.should_download_build:
    webrtc.extract_build()

  if webrtc.bot.should_test:
    webrtc.runtests()

  webrtc.maybe_trigger()


def GenTests(api):
  builders = api.webrtc.BUILDERS
  generate_builder = functools.partial(api.webrtc.generate_builder, builders)

  for bucketname in builders.keys():
    master_config = builders[bucketname]
    for buildername in master_config['builders'].keys():
      yield generate_builder(bucketname, buildername, revision='a' * 40)

  bucketname = 'luci.webrtc.try'
  buildername = 'linux_compile_rel'
  yield generate_builder(bucketname, buildername, revision=None,
                         is_chromium=True, suffix='_chromium')

  # Forced builds (not specifying any revision) and test failures.
  bucketname = 'luci.webrtc.ci'
  buildername = 'Linux64 Debug'
  yield generate_builder(bucketname, buildername, revision=None,
                         suffix='_forced')
  yield generate_builder(bucketname, buildername, revision='a' * 40,
                         failing_test='rtc_unittests',
                         suffix='_failing_test')
  yield generate_builder(bucketname, 'Android32 (M Nexus5X)', revision='a' * 40,
                         fail_android_archive=True, suffix='_failing_archive')

  yield generate_builder('client.webrtc.perf', 'Android32 Builder',
                         suffix='_forced', revision=None)

  yield generate_builder('client.webrtc.perf', 'Android32 Tests (L Nexus5)',
                         suffix='_forced',
                         parent_got_revision='a' * 40, revision=None)
  yield generate_builder('client.webrtc.perf', 'Android32 Tests (L Nexus5)',
                         suffix='_forced_invalid', revision=None)

  yield generate_builder('luci.webrtc.perf', 'Perf Linux Trusty',
                         failing_test='webrtc_perf_tests',
                         suffix='_failing_test', revision='a' * 40)

  yield generate_builder('luci.webrtc.perf', 'Perf Android32 (L Nexus5)',
                         failing_test='webrtc_perf_tests on Android',
                         suffix='_failing_test', revision='a' * 40)
