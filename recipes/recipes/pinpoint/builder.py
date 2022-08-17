# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
]

# Name of pinpoint try builder -> (perf builder group, perf builder name)
_PINPOINT_MAPPING = {
    'Android Compile Perf': ('chromium.perf', 'android-builder-perf'),
    'Android Compile Perf PGO': ('chromium.perf', 'android-builder-perf-pgo'),
    'Android arm64 Compile Perf':
        ('chromium.perf', 'android_arm64-builder-perf'),
    'Android arm64 Compile Perf PGO':
        ('chromium.perf', 'android_arm64-builder-perf-pgo'),
    'Chromecast Linux Builder Perf':
        ('chromium.perf', 'chromecast-linux-builder-perf'),
    'Chromeos Amd64 Generic Lacros Builder Perf':
        ('chromium.perf', 'chromeos-amd64-generic-lacros-builder-perf'),
    'Fuchsia Builder Perf': ('chromium.perf.fyi', 'fuchsia-builder-perf-fyi'),
    'Fuchsia Builder Perf x64':
        ('chromium.perf.fyi', 'fuchsia-builder-perf-x64'),
    'Linux Builder Perf': ('chromium.perf', 'linux-builder-perf'),
    'Linux Builder Perf PGO': ('chromium.perf', 'linux-builder-perf-pgo'),
    'Mac Builder Perf': ('chromium.perf', 'mac-builder-perf'),
    'Mac Builder Perf PGO': ('chromium.perf', 'mac-builder-perf-pgo'),
    'Mac arm Builder Perf': ('chromium.perf', 'mac-arm-builder-perf'),
    'Mac arm Builder Perf PGO': ('chromium.perf', 'mac-arm-builder-perf-pgo'),
    'mac-laptop_high_end-perf': ('chromium.perf', 'mac-laptop_high_end-perf'),
    'Win x64 Builder Perf': ('chromium.perf', 'win64-builder-perf'),
    'Win x64 Builder Perf PGO': ('chromium.perf', 'win64-builder-perf-pgo'),
}


def RunSteps(api):
  pinpoint_builder = api.buildbucket.builder_name
  perf_builder = _PINPOINT_MAPPING.get(pinpoint_builder)
  if perf_builder is None:
    api.step.empty(
        'no pinpoint mapping',
        status=api.step.INFRA_FAILURE,
        step_text=(
            'No pinpoint mapping is configured for {!r}.\n'
            'Please update pinpoint/builder.py').format(pinpoint_builder))

  with api.chromium.chromium_layout():
    builder_id = chromium.BuilderId.create_for_group(*perf_builder)
    _, builder_config = api.chromium_tests_builder_config.lookup_builder(
        builder_id, use_try_db=False)

    # crbug/1291250: We cannot simply add the old tester config back, as builder
    # on perf waterfall will try to trigger them and failed. We hacked there to
    # only add them on pinpoint context, by:
    #  - load the spec mapping of 'chromium.perf' from builder_config
    #  - add the old testers to the mapping, and regenerate the builder config.
    builder_dict = dict(builder_config.builder_db.builders_by_group)
    spec_dict = dict(builder_dict['chromium.perf'])
    spec_dict.update(ctbc.builders.chromium_perf.PINPOINT_SPEC)
    builder_dict['chromium.perf'] = spec_dict
    new_builder_db = ctbc.builder_db.BuilderDatabase.create(builder_dict)
    _, builder_config = api.chromium_tests_builder_config.lookup_builder(
        builder_id, builder_db=new_builder_db, use_try_db=False)

    api.chromium_tests.configure_build(builder_config)
    for key, value in api.gclient.c.repo_path_map.items():
      if value[1] == 'HEAD':
        # Pinpoint should use the exact revision given in DEPS, instead of HEAD.
        api.gclient.c.repo_path_map[key] = (value[0], None)
    update_step, targets_config = (
        api.chromium_tests.prepare_checkout(builder_config))
    return api.chromium_tests.compile_specific_targets(
        builder_id, builder_config, update_step, targets_config,
        targets_config.compile_targets, targets_config.all_tests)[0]


def GenTests(api):
  from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

  # Data used in tests.
  builder = {
      'builder_group': 'tryserver.chromium.perf',
      'builder': 'Android Compile Perf',
  }
  source_side_spec = ('chromium.perf', {
      'android-go-perf': {
          'isolated_scripts': [{
              'isolate_name': 'performance_test_suite_android_clank_chrome',
              'name': 'performance_test_suite',
          },],
      },
  })

  yield api.test(
      'basic',
      api.chromium.generic_build(**builder),
      api.chromium_tests.read_source_side_spec(*source_side_spec),
  )

  yield api.test(
      'with_patch',
      api.chromium.try_build(
          revision='0cd310e5609606ca9c8531313142a1a9f16ae860',
          gerrit_changes=[
              common_pb2.GerritChange(
                  host='chromium-review.googlesource.com',
                  project='v8/v8',
                  change=3592345,
                  patchset=1)
          ],
          **builder),
      api.chromium_tests.read_source_side_spec(*source_side_spec),
      api.post_process(post_process.Filter('bot_update')),
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
      api.chromium.generic_build(**builder),
      api.chromium_tests.read_source_side_spec(*source_side_spec),
      api.step_data('compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
