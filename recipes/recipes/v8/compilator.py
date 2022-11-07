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

import json

from recipe_engine.post_process import DropExpectation, StatusFailure
from recipe_engine.recipe_api import Property

DEPS = [
  'builder_group',
  'chromium',
  'recipe_engine/buildbucket',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
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


# TODO(https://crbug.com/890222): Deprecate this mapping after migration to
# orchestrator + 4 milestones (2023/Q3).
def legacy_builder_name(api, triggered):
  """Map given builder names from infra/config to names used for look-ups
  in source configurations.

  This maps compilator builder names to legacy names to ease the roll-out and
  for backwards-compatibility on release branches.
  """
  builder_name = api.buildbucket.builder_name
  triggered_suffix = '_triggered' if triggered else ''
  if builder_name.endswith('_compile_rel'):
    builder_name = builder_name.replace(
        '_compile_rel', '_rel_ng' + triggered_suffix)
  if builder_name.endswith('_compile_dbg'):
    builder_name = builder_name.replace(
        '_compile_dbg', '_dbg_ng' + triggered_suffix)
  return builder_name


# TODO(https://crbug.com/890222): Remove this after M111.
def orchestrator_names(api):
  """Temporary mapping of legacy trybot names to look up V8-side test configs.

  Remove after V8-side mapping changes have reached extended stable.
  This changes builder-name config keys, e.g.
  v8_linux_rel into legacy name v8_linux_rel_ng_triggered.
  """
  builder_name = api.buildbucket.builder_name
  if builder_name.endswith('_compile_rel'):
    builder_name = builder_name.replace('_compile_rel', '_rel')
  if builder_name.endswith('_compile_dbg'):
    builder_name = builder_name.replace('_compile_dbg', '_dbg')
  return [
    legacy_builder_name(api, triggered=True),
    builder_name,
  ]


# TODO(https://crbug.com/890222): Remove after M111.
def mb_override(api):
  """Temporary override of mb_config.pyl until V8-side builder name changes
  have reached extended stable."""

  mb_config_data = api.file.read_text(
      'read MB config (compilator)',
      api.path['checkout'].join('infra', 'mb', 'mb_config.pyl'),
      test_data=api.v8.test_api.example_compilator_mb_config(),
  )

  # Replace legacy name in config with new/current name.
  # E.g. linux_rel_ng with linux_compile_rel.
  mb_config_data = mb_config_data.replace(
      legacy_builder_name(api, triggered=False),
      api.buildbucket.builder_name)

  new_mb_config_path = api.path['tmp_base'].join('mb_config.pyl')
  api.file.write_text(
      'tweak MB config (compilator)',
      new_mb_config_path,
      mb_config_data,
  )
  return new_mb_config_path


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

  with api.step.nest('initialization'):
    if api.platform.is_win:
      api.chromium.taskkill()

    v8.checkout()
    api.v8_tests.set_up_swarming()
    v8.runhooks()

    # Dynamically load test specifications from all discovered test roots.
    for test_root in v8.get_test_roots():
      test_spec.update(v8.read_test_spec(test_root, orchestrator_names(api)))

  with api.step.nest('build'):
    compile_failure = v8.compile(test_spec, mb_override(api))
    if compile_failure:
      return compile_failure

  properties = dict(test_spec.as_properties_dict_single())
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

  test_spec = json.dumps({'tests': [{'name': 'v8testing'}]}, indent=2)

  yield (
      test('basic') +
      api.v8.test_spec_in_checkout(
          'v8_foobar_rel_ng', test_spec, 'v8_foobar_rel_ng_triggered')
  )

  yield (
      test('windows', 'v8_foobar_compile_dbg') +
      api.v8.test_spec_in_checkout(
          'v8_foobar_dbg_ng', test_spec, 'v8_foobar_dbg_ng_triggered') +
      api.platform('win', 64) +
      api.post_process(DropExpectation)
  )

  yield (
      test('compile_failure') +
      api.step_data('build.compile', retcode=1) +
      api.post_process(StatusFailure) +
      api.post_process(DropExpectation)
  )
