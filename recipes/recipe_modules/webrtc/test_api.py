# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

from __future__ import absolute_import

from recipe_engine import post_process
from recipe_engine import recipe_test_api
from . import builders


def _sanitize_builder_name(name):
  safe_with_spaces = ''.join(c if c.isalnum() else ' ' for c in name.lower())
  return '_'.join(safe_with_spaces.split())


def _run_tests(builder_id):
  # Decides which builder run tests based on the builder's name. It represents
  # the builders that have a 'test_suites' section in waterfalls.pyl.
  buildername = builder_id.builder.lower()
  return not any(b in buildername for b in ('builder', 'fuzzer', 'compile'))


class WebRTCTestApi(recipe_test_api.RecipeTestApi):

  def example_binary_sizes(self):
    return self.m.json.output({'some_binary': 123456})

  def generate_builder(self,
                       builders_db,
                       builder_id,
                       failing_test=False,
                       fail_compile=False,
                       suffix='',
                       fail_android_archive=False,
                       is_experimental=False,
                       gn_analyze_output=None,
                       tags=None):
    builder_config = builders_db[builder_id]
    project = 'webrtc-internal' if 'internal' in builder_id.group else 'webrtc'
    bucketname = builders.BUCKET_NAME[builder_id.group]
    test_target = 'dummy_test'

    chromium_kwargs = builder_config.chromium_config_kwargs
    test = self.test(
        '%s_%s%s' % (_sanitize_builder_name(bucketname),
                     _sanitize_builder_name(builder_id.builder), suffix),
        self.m.builder_group.for_current(builder_id.group),
        self.m.properties(
            buildername=builder_id.builder,
            bot_id='bot_id',
            BUILD_CONFIG=chromium_kwargs['BUILD_CONFIG']),
        self.m.platform(builder_config.simulation_platform or 'linux',
                        chromium_kwargs.get('TARGET_BITS', 64)),
        self.m.runtime(is_experimental=is_experimental),
    )

    if 'mac_toolchain' in builder_config.chromium_apply_config:
      test += self.m.properties(xcode_build_version='dummy_xcode')
    test += self.m.properties(
        revision='a' * 40,
        got_revision='a' * 40,
        got_revision_cp='refs/heads/main@{#1337}')
    if builder_config.parent_buildername:
      parent_buildername = builder_config.parent_buildername
      parent_rev = 'a' * 40
      test += self.m.properties(parent_buildername=parent_buildername)
      test += self.m.properties(parent_got_revision=parent_rev)
      test += self.m.properties(
          swarming_command_lines={test_target: ['./dummy_cmd']})

    if fail_compile:
      test += self.step_data('compile', retcode=1)
      test += self.post_process(post_process.StatusFailure)
      test += self.post_process(post_process.DropExpectation)

    if failing_test:
      test += self.override_step_data(
          'collect tasks.%s results' % test_target,
          stdout=self.m.raw_io.output_text(
              self.m.test_utils.rdb_results(
                  test_target, failing_tests=[test_target])))

    if fail_android_archive:
      step_test_data = recipe_test_api.StepTestData()
      step_test_data.retcode = 1
      test += self.override_step_data('build android archive', step_test_data)

    git_repo = 'https://webrtc.googlesource.com/src'
    nb_phase = 1
    if 'more_configs' in _sanitize_builder_name(builder_id.builder):
      nb_phase = 3
    if 'try' in builder_id.group:
      if 'fuzzer' not in builder_id.builder:
        for i in range(nb_phase):
          run_tests = _run_tests(builder_id) and (nb_phase == 1 or i == 2)
          json_output = self.m.json.output(
              gn_analyze_output or {
                  'compile_targets': ['all'],
                  'status': 'Found dependency',
                  'test_targets': [test_target] if run_tests else [],
              })
          suffix = '' if i == 0 else ' (%d)' % (i + 1)
          test += self.override_step_data('analyze' + suffix, json_output)

      test += self.m.buildbucket.try_build(
          project=project,
          bucket='try',
          builder=builder_id.builder,
          git_repo=git_repo,
          revision='a' * 40,
          tags=tags)
    else:
      test += self.m.buildbucket.ci_build(
          project=project,
          bucket='perf' if 'perf' in builder_id.group else 'ci',
          builder=builder_id.builder,
          git_repo=git_repo,
          revision='a' * 40,
          tags=tags)
    test += self.m.properties(buildnumber=1337)

    if _run_tests(builder_id):
      test += self.m.chromium_tests.read_source_side_spec(
          builder_id.group,
          contents={
              builder_id.builder: {
                  'gtest_tests': [{
                      'test': test_target,
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      }
                  }]
              }
          })

    return test
