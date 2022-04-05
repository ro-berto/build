# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building and running tests for WebRTC stand-alone.

from __future__ import absolute_import

import functools
from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

from RECIPE_MODULES.build import chromium

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests_builder_config',
    'recipe_engine/step',
    'webrtc',
]


def RunSteps(api):
  webrtc = api.webrtc
  builder_config = None
  builder_id = chromium.BuilderId.create_for_group(
      webrtc.BUILDERS[webrtc.bucketname]['settings']['builder_group'],
      webrtc.buildername)
  if builder_id in webrtc.BUILDERS_DB:
    builder_config = api.chromium_tests_builder_config.lookup_builder(
        builder_db=webrtc.BUILDERS_DB)[1]
  webrtc.apply_bot_config(webrtc.BUILDERS, webrtc.RECIPE_CONFIGS,
                          builder_config)

  update_step = api.chromium_checkout.ensure_checkout()

  webrtc.configure_swarming()

  if webrtc.should_download_audio_quality_tools():
    webrtc.download_audio_quality_tools()
  if webrtc.should_download_video_quality_tools():
    webrtc.download_video_quality_tools()

  api.chromium.ensure_goma()
  api.chromium.ensure_toolchains()
  api.chromium.runhooks()

  for phase in webrtc.bot.phases:
    tests, compile_targets = webrtc.get_tests_and_compile_targets(
        phase, builder_config, update_step)
    if not compile_targets:
      step_result = api.step('No further steps are necessary.', cmd=None)
      step_result.presentation.status = api.step.SUCCESS
      return

    webrtc.run_mb(phase, tests)
    raw_result = api.chromium.compile(compile_targets, use_goma_module=True)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result
    webrtc.isolate(tests)

    if webrtc.bot.config.get('binary_size_files'):
      webrtc.get_binary_sizes(webrtc.bot.config['binary_size_files'])
    if webrtc.bot.config.get('build_android_archive'):
      webrtc.build_android_archive()
    if webrtc.bot.config.get('archive_apprtc'):
      webrtc.package_apprtcmobile()

    test_failure_summary = webrtc.run_tests(tests)
    if test_failure_summary:
      return test_failure_summary

  webrtc.trigger_child_builds()


def GenTests(api):
  builders = api.webrtc.BUILDERS
  generate_builder = functools.partial(api.webrtc.generate_builder, builders)

  for bucketname in builders.keys():
    group_config = builders[bucketname]
    for buildername in group_config['builders'].keys():
      yield generate_builder(bucketname, buildername, revision='a' * 40)

  bucketname = 'luci.webrtc.ci'
  buildername = 'Linux64 Debug'
  yield generate_builder(
      bucketname,
      buildername,
      revision='a' * 40,
      failing_test='rtc_unittests',
      suffix='_failing_test')
  yield generate_builder(
      bucketname,
      buildername,
      revision=None,
      tags=[{
          'key': 'pinpoint_job_id',
          'value': ''
      }],
      suffix='_pinpoint')
  yield (
    generate_builder(
      bucketname,
      buildername,
      revision='b' * 40,
      suffix='_fail_compile',
      fail_compile=True
    ) +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )
  yield generate_builder(bucketname, 'Android32 (M Nexus5X)', revision='a' * 40,
                         fail_android_archive=True, suffix='_failing_archive')

  yield generate_builder(
      'luci.webrtc.perf',
      'Perf Linux Bionic',
      is_experimental=True,
      suffix='_experimental',
      revision='a' * 40)

  gn_analyze_no_deps_output = {'status': ['No dependency']}
  yield generate_builder(
      'luci.webrtc.try',
      'linux_compile_arm_rel',
      revision='a' * 40,
      suffix='_gn_analyze_no_dependency',
      gn_analyze_output=gn_analyze_no_deps_output)
