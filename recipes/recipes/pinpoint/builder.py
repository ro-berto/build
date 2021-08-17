# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/python',
]

# Name of pinpoint try builder -> (perf builder group, perf builder name)
_PINPOINT_MAPPING = {
    'Android Compile Perf': ('chromium.perf', 'android-builder-perf'),
    'Android arm64 Compile Perf':
        ('chromium.perf', 'android_arm64-builder-perf'),
    'Chromecast Linux Builder Perf':
        ('chromium.perf', 'chromecast-linux-builder-perf'),
    'Chromeos Amd64 Generic Lacros Builder Perf':
        ('chromium.perf', 'chromeos-amd64-generic-lacros-builder-perf'),
    'Fuchsia Builder Perf': ('chromium.perf.fyi', 'fuchsia-builder-perf-fyi'),
    'Linux Builder Perf': ('chromium.perf', 'linux-builder-perf'),
    'Mac Builder Perf': ('chromium.perf', 'mac-builder-perf'),
    'Mac arm Builder Perf': ('chromium.perf', 'mac-arm-builder-perf'),
    'mac-10_13_laptop_high_end-perf':
        ('chromium.perf', 'mac-10_13_laptop_high_end-perf'),
    'Win Builder Perf': ('chromium.perf', 'win32-builder-perf'),
    'Win x64 Builder Perf': ('chromium.perf', 'win64-builder-perf'),
}


def RunSteps(api):
  pinpoint_builder = api.buildbucket.builder_name
  perf_builder = _PINPOINT_MAPPING.get(pinpoint_builder)
  if perf_builder is None:
    api.python.infra_failing_step(
        'no pinpoint mapping',
        ('No pinpoint mapping is configured for {!r}.\n'
         'Please update pinpoint/builder.py').format(pinpoint_builder))

  with api.chromium.chromium_layout():
    builder_id = chromium.BuilderId.create_for_group(*perf_builder)
    _, builder_config = api.chromium_tests_builder_config.lookup_builder(
        builder_id, use_try_db=False)

    api.chromium_tests.configure_build(builder_config)
    update_step, targets_config = (
        api.chromium_tests.prepare_checkout(builder_config))
    return api.chromium_tests.compile_specific_targets(
        builder_id, builder_config, update_step, targets_config,
        targets_config.compile_targets, targets_config.all_tests)


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
      'bad_builder',
      api.chromium.generic_build(
          builder_group='tryserver.chromium.perf',
          builder='Nonexistent Compile Perf'),
      api.post_check(post_process.MustRun, 'no pinpoint mapping'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
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
