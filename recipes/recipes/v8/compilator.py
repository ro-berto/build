# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Compilator recipe.

Triggered by the orchestrator recipe to perform all
check-out-related tasks: sync, hooks, compile, isolate and read all
configs from check-out: MB for building and builders.pyl for testing.

All properties needed by the orchestrator are returned at the end of the
build: CAS digests and test configurations.

The compilator is only used in a trybot setting.
"""

from recipe_engine.post_process import DropExpectation, StatusFailure
from recipe_engine.recipe_api import Property

DEPS = [
  'builder_group',
  'chromium',
  'recipe_engine/buildbucket',
  'recipe_engine/json',
  'recipe_engine/platform',
  'recipe_engine/step',
  'v8',
  'v8_tests',
]

PROPERTIES = {
    # Mapping of custom dependencies to sync (dependency name as in DEPS
    # file -> deps url).
    'custom_deps': Property(default=None, kind=dict),
    # Optional list of default targets. If not specified the implicit "all"
    # target will be built.
    'default_targets': Property(default=None, kind=list),
    # Mapping of additional gclient variables to set (map name -> value).
    'gclient_vars': Property(default=None, kind=dict),
    # One of intel|arm|mips.
    'target_arch': Property(default=None, kind=str),
    # One of android|fuchsia|linux|mac|win.
    'target_platform': Property(default=None, kind=str),
    # Weather to use goma for compilation.
    'use_goma': Property(default=True, kind=bool),
}


# TODO(https://crbug.com/890222): Wrap and ensure we return state cancelled
# on cancellation.
def RunSteps(api, custom_deps, default_targets, gclient_vars, target_arch,
             target_platform, use_goma):
  v8 = api.v8
  api.v8_tests.load_static_test_configs()
  bot_config = v8.update_bot_config(
      v8.bot_config_by_buildername(use_goma=use_goma),
      binary_size_tracking=None,
      clusterfuzz_archive=None,
      coverage=None,
      enable_swarming=True,
      target_arch=target_arch,
      target_platform=target_platform,
      track_build_dependencies=None,
      triggers=None,
      triggers_proxy=None,
  )
  v8.apply_bot_config(bot_config)
  v8.set_gclient_custom_vars(gclient_vars)
  v8.set_gclient_custom_deps(custom_deps)
  v8.set_chromium_configs(clobber=False, default_targets=default_targets)

  test_spec = api.v8_tests.TEST_SPEC()
  tests = []

  with api.step.nest('initialization'):
    if api.platform.is_win:
      api.chromium.taskkill()

    v8.checkout()
    api.v8_tests.set_up_swarming()
    v8.runhooks()

    # Dynamically load test specifications from all discovered test roots.
    for test_root in v8.get_test_roots():
      test_spec.update(v8.read_test_spec(test_root))
      # Tests from dynamic test roots have precedence.
      tests = v8.dedupe_tests(v8.extra_tests_from_test_spec(test_spec), tests)

  with api.step.nest('build'):
    compile_failure = v8.compile(test_spec)
    if compile_failure:
      return compile_failure

  properties = dict(test_spec.as_properties_dict(
      v8.normalized_builder_name(triggered=True)))
  properties['swarm_hashes'] = api.v8_tests.isolated_tests
  properties['gn_args'] = api.v8_tests.gn_args

  properties_step = api.step('compilator properties', [])
  properties_step.presentation.properties['compilator_properties'] = properties
  properties_step.presentation.logs['compilator_properties'] = api.json.dumps(
      properties, indent=2)


def GenTests(api):
  def test(name, builder_name='v8_foobar_compile_rel'):
    return (
        api.test(name) +
        api.builder_group.for_current('tryserver.v8') +
        api.platform('linux', 64) +
        api.buildbucket.try_build(
            project='v8',
            revision='deadbeef'*5,
            builder=builder_name,
            git_repo='https://chromium.googlesource.com/v8/v8',
            change_number=456789,
            patch_set=12,
            tags=api.buildbucket.tags(
                user_agent='cq',
                buildset='patch/gerrit/chromium-review.googlesource.com/456789/12'
            ),
        ) +
        api.v8.example_test_roots('test_checkout') +
        api.v8.hide_infra_steps()
    )

  yield test('basic')

  yield (
      test('windows', 'v8_foobar_compile_dbg') +
      api.platform('win', 64) +
      api.post_process(DropExpectation)
  )

  # TODO(https://crbug.com/890222): Two tests just for legacy compilator names.
  # Remove after the rename.
  yield (
      test('legacy_dbg', 'v8_foobar_compile_ng_dbg') +
      api.post_process(DropExpectation)
  )

  yield (
      test('legacy_rel', 'v8_foobar_compile_ng_rel') +
      api.post_process(DropExpectation)
  )

  yield (
      test('compile_failure') +
      api.step_data('build.compile', retcode=1) +
      api.post_process(StatusFailure) +
      api.post_process(DropExpectation)
  )
