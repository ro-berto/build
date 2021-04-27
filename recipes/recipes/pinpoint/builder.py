# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
]


def RunSteps(api):
  with api.chromium.chromium_layout():
    builder_id, builder_config = (
        api.chromium_tests_builder_config.lookup_builder(use_try_db=True))

    api.chromium_tests.configure_build(builder_config)
    update_step, build_config = (
        api.chromium_tests.prepare_checkout(builder_config))
    compile_targets = build_config.get_compile_targets(build_config.all_tests())
    return api.chromium_tests.compile_specific_targets(builder_id,
                                                       builder_config,
                                                       update_step,
                                                       build_config,
                                                       compile_targets,
                                                       build_config.all_tests())


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.generic_build(
          builder_group='tryserver.chromium.perf',
          builder='Android Compile Perf'),
      api.chromium_tests.read_source_side_spec(
          'chromium.perf', {
              'Android One Perf': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_perf_tests',
                      'name': 'benchmark',
                  },],
              },
          }),
  )

  yield api.test(
      'compile_failure',
      api.chromium.generic_build(
          builder_group='tryserver.chromium.perf',
          builder='Android Compile Perf'),
      api.chromium_tests.read_source_side_spec(
          'chromium.perf', {
              'Android One Perf': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_perf_tests',
                      'name': 'benchmark',
                  },],
              },
          }),
      api.step_data('compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
