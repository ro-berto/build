# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

from __future__ import absolute_import

import os
import base64
import json

import six

from recipe_engine import recipe_test_api
from recipe_engine import config_types
from . import api
from . import builders as webrtc_builders
from . import steps


class WebRTCTestApi(recipe_test_api.RecipeTestApi):
  BUILDERS = webrtc_builders.BUILDERS
  RECIPE_CONFIGS = webrtc_builders.RECIPE_CONFIGS

  def example_binary_sizes(self):
    return self.m.json.output({'some_binary': 123456})

  def example_patch(self):
    return self.m.json.output({
        'value':
            six.ensure_str(
                base64.b64encode(b'diff --git a/a b/a\nnew file mode 100644\n'))
    })

  def generate_builder(self,
                       builders,
                       bucketname,
                       buildername,
                       revision,
                       parent_got_revision=None,
                       failing_test=None,
                       fail_compile=False,
                       suffix='',
                       is_chromium=False,
                       fail_android_archive=False,
                       is_experimental=False,
                       gn_analyze_output=None,
                       phases=None,
                       tags=None):
    builder_group = builders[bucketname]['settings'].get(
        'builder_group', bucketname)
    bot_config = builders[bucketname]['builders'][buildername]
    bot_type = bot_config.get('bot_type', 'builder_tester')

    if bot_type in ('builder', 'builder_tester'):
      assert bot_config.get('parent_buildername') is None, (
          'Unexpected parent_buildername for builder %r on bucket %r.' %
              (buildername, bucketname))

    chromium_kwargs = bot_config.get('chromium_config_kwargs', {})
    test = self.test(
        '%s_%s%s' % (_sanitize_builder_name(bucketname),
                     _sanitize_builder_name(buildername), suffix),
        self.m.builder_group.for_current(builder_group),
        self.m.properties(
            buildername=buildername,
            bot_id='bot_id',
            BUILD_CONFIG=chromium_kwargs['BUILD_CONFIG']),
        self.m.platform(bot_config['testing']['platform'],
                        chromium_kwargs.get('TARGET_BITS', 64)),
        self.m.runtime(is_experimental=is_experimental),
    )

    if bot_config.get('parent_buildername'):
      test += self.m.properties(
          parent_buildername=bot_config['parent_buildername'])
    if revision:
      test += self.m.properties(
          revision=revision,
          got_revision='a' * 40,
          got_revision_cp='refs/heads/main@{#1337}')
    if bot_type == 'tester':
      parent_rev = parent_got_revision or revision
      test += self.m.properties(parent_got_revision=parent_rev)
      test += self.m.properties(
          swarming_command_lines={'webrtc_perf_tests': ['./dummy_cmd']})

    if fail_compile:
      test += self.step_data('compile', retcode=1)

    if failing_test:
      # Unfortunately, we have no idea what type of test this is and what would
      # be appropriate test data to pass. We guess that this is a swarmed gtest.
      custom_os = bot_config.get('swarming_dimensions', {}).get('os', '')
      swarming_result = self.m.chromium_swarming.canned_summary_output_raw(
          failure=True)
      swarming_result['shards'][0]['output'] = "Tests failed"
      swarming_result['shards'][0]['exit_code'] = 1

      test_step_data = self.m.chromium_swarming.summary(
          dispatched_task_step_test_data=None, data=swarming_result)

      test += self.override_step_data('%s on %s' % (failing_test, custom_os),
                                      test_step_data)
      test += self.override_step_data(
          '%s results' % failing_test,
          stdout=self.m.raw_io.output_text(
              self.m.test_utils.rdb_results(
                  failing_test, failing_tests=[failing_test])))

    if fail_android_archive:
      step_test_data = recipe_test_api.StepTestData()
      step_test_data.retcode = 1
      test += self.override_step_data('build android archive', step_test_data)

    git_repo = 'https://webrtc.googlesource.com/src'
    if is_chromium:
      git_repo = 'https://chromium.googlesource.com/chromium/src'
    _, project, short_bucket = bucketname.split('.')
    if 'try' in bucketname:
      if 'fuzzer' not in buildername:
        phase_suffix = ''
        test += self.override_gn_analyze(gn_analyze_output, phase_suffix)
        if phases:
          for phase_number in range(1, len(phases)):
            phase_suffix = ' (%s)' % (phase_number + 1)
            test += self.override_gn_analyze(gn_analyze_output, phase_suffix)

      test += self.m.buildbucket.try_build(
          project=project,
          bucket=short_bucket,
          builder=buildername,
          git_repo=git_repo,
          revision=revision or None,
          tags=tags)
    else:
      test += self.m.buildbucket.ci_build(
          project=project,
          bucket=short_bucket,
          builder=buildername,
          git_repo=git_repo,
          revision=revision or 'a' * 40,
          tags=tags)
    test += self.m.properties(buildnumber=1337)

    return test

  def override_gn_analyze(self,
                          gn_analyze_output,
                          phase_suffix=''):
    if gn_analyze_output is None:
      gn_analyze_output = {
          'compile_targets': ['default'],
          'status': 'Found dependency',
          'test_targets': ['common_audio_unittests'],
      }
    return self.override_step_data('analyze' + phase_suffix,
                                   self.m.json.output(gn_analyze_output))

  def example_proto(self):
    # Tip: to see what's in the proto, use the tracing/bin/proto2json tool
    # in the Catapult repo.
    this_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    proto = os.path.join(this_dir, 'testdata', 'perftest-output.json')
    with open(proto, "rb") as f:
      return f.read()


def _sanitize_builder_name(name):
  return api.sanitize_file_name(name.lower())
