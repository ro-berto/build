# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building and running tests for WebRTC stand-alone.

from __future__ import absolute_import

import functools
from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.webrtc import builders

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
  builder_id, builder_config = api.chromium_tests_builder_config.lookup_builder(
      builder_db=builders.BUILDERS_DB)
  webrtc.apply_bot_config(builder_id, builder_config)

  update_step = api.chromium_checkout.ensure_checkout()

  webrtc.configure_swarming(builder_id)

  if webrtc.should_download_audio_quality_tools(builder_id):
    webrtc.download_audio_quality_tools()
  if webrtc.should_download_video_quality_tools(builder_id):
    webrtc.download_video_quality_tools()

  api.chromium.ensure_goma()
  api.chromium.ensure_toolchains()
  api.chromium.runhooks()

  builder_spec = builders.BUILDERS_DB[builder_id]
  for phase in builder_spec.phases:
    tests, compile_targets = webrtc.get_tests_and_compile_targets(
        builder_id, builder_config, phase, update_step)
    if not compile_targets:
      step_result = api.step('No further steps are necessary.', cmd=None)
      step_result.presentation.status = api.step.SUCCESS
      return

    webrtc.run_mb(builder_id, phase, tests)
    raw_result = api.chromium.compile(compile_targets, use_goma_module=True)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result
    webrtc.isolate(builder_id, tests)

    if builder_spec.binary_size_files:
      webrtc.get_binary_sizes(builder_spec.binary_size_files)
    if builder_spec.build_android_archive:
      webrtc.build_android_archive()
    if builder_spec.archive_apprtc:
      webrtc.package_apprtcmobile()

    test_failure_summary = webrtc.run_tests(builder_id, tests)
    if test_failure_summary:
      return test_failure_summary

  webrtc.trigger_child_builds()


def GenTests(api):
  builders_db = builders.BUILDERS_DB
  generate_builder = functools.partial(api.webrtc.generate_builder, builders_db)

  for builder_id in builders_db:
    yield generate_builder(builder_id, revision='a' * 40)

  builder_id = chromium.BuilderId.create_for_group('client.webrtc',
                                                   'Linux64 Debug')
  yield generate_builder(
      builder_id,
      revision='a' * 40,
      failing_test='common_audio_unittests',
      suffix='_failing_test')
  yield generate_builder(
      builder_id,
      revision=None,
      tags=[{
          'key': 'pinpoint_job_id',
          'value': ''
      }],
      suffix='_pinpoint')
  yield (generate_builder(
      builder_id, revision='b' * 40, suffix='_fail_compile',
      fail_compile=True) + api.post_process(post_process.StatusFailure) +
         api.post_process(post_process.DropExpectation))

  builder_id = chromium.BuilderId.create_for_group('client.webrtc',
                                                   'Android32 (M Nexus5X)')
  yield generate_builder(
      builder_id,
      revision='a' * 40,
      fail_android_archive=True,
      suffix='_failing_archive')

  builder_id = chromium.BuilderId.create_for_group('client.webrtc.perf',
                                                   'Perf Linux Bionic')
  yield generate_builder(
      builder_id,
      is_experimental=True,
      suffix='_experimental',
      revision='a' * 40)

  builder_id = chromium.BuilderId.create_for_group('tryserver.webrtc',
                                                   'linux_compile_arm_rel')
  gn_analyze_no_deps_output = {'status': ['No dependency']}
  yield generate_builder(
      builder_id,
      revision='a' * 40,
      suffix='_gn_analyze_no_dependency',
      gn_analyze_output=gn_analyze_no_deps_output)
