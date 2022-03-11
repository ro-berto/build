# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe to compare reclient based builds against a goma based build.

Waterfall page: https://build.chromium.org/p/chromium.swarm/waterfall

"""

from recipe_engine import post_process
from recipe_engine.engine_types import freeze
from recipe_engine.recipe_api import Property
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'builder_group',
    'chromium',
    'chromium_checkout',
    'depot_tools/gclient',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
]

COMPARISON_BUILDERS = freeze({
    'Comparison Android (reclient)': {
        'chromium_config': 'android',
        'gclient_config': 'chromium',
        'chromium_apply_config': [
            'mb', 'goma_enable_cache_silo', 'goma_large_cache_file',
            'download_vr_test_apks'
        ],
        'gclient_apply_config': ['android', 'enable_reclient', 'reclient_test'],
        'chromium_config_kwargs': {
            'BUILD_CONFIG': 'Debug',
            'TARGET_BITS': 32,
            'TARGET_PLATFORM': 'android',
        },
        'android_config': 'main_builder_mb',
        'simulation_platform': 'linux',
        'platform': 'linux',
        'targets': ['all'],
    },
    'Comparison Linux (reclient)': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'chromium_apply_config': [
            'mb', 'goma_enable_cache_silo', 'goma_large_cache_file'
        ],
        'gclient_apply_config': ['enable_reclient', 'reclient_test'],
        'platform': 'linux',
        'targets': ['all'],
    },
    'Comparison Windows (reclient)': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'chromium_apply_config': [
            'mb', 'goma_enable_cache_silo', 'goma_large_cache_file'
        ],
        'gclient_apply_config': ['enable_reclient', 'reclient_test'],
        'platform': 'win',
        'targets': ['all'],
    },
    'Comparison Windows (8 cores) (reclient)': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'chromium_apply_config': [
            'mb', 'goma_enable_cache_silo', 'goma_large_cache_file'
        ],
        'gclient_apply_config': ['enable_reclient', 'reclient_test'],
        'platform': 'win',
        'targets': ['all'],
    },
    'Comparison Simple Chrome (reclient)': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'chromium_apply_config': [
            'mb', 'goma_enable_cache_silo', 'goma_large_cache_file'
        ],
        'gclient_apply_config': [
            'chromeos', 'enable_reclient', 'reclient_test'
        ],
        'platform': 'linux',
        'chromium_config_kwargs': {
            'TARGET_BITS': 64,
            'TARGET_PLATFORM': 'chromeos',
            'CROS_BOARDS_WITH_QEMU_IMAGES': 'amd64-generic:amd64-generic-vm',
        },
        'simulation_platform': 'linux',
        'targets': ['chrome'],
    },
})


def ConfigureChromiumBuilder(api, recipe_config):
  api.chromium.set_config(
      recipe_config['chromium_config'],
      **recipe_config.get('chromium_config_kwargs',
                          {'BUILD_CONFIG': 'Release'}))
  api.gclient.set_config(recipe_config['gclient_config'],
                         **recipe_config.get('gclient_config_kwargs', {}))

  for c in recipe_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)

  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if api.chromium.c.CROS_BOARDS_WITH_QEMU_IMAGES:
    gclient_solution = api.gclient.c.solutions[0]
    gclient_solution.custom_vars['cros_boards_with_qemu_images'] = (
        api.chromium.c.CROS_BOARDS_WITH_QEMU_IMAGES)
  # Checkout chromium.
  api.chromium_checkout.ensure_checkout()


def RunSteps(api):
  buildername = api.buildbucket.builder_name
  recipe_config = COMPARISON_BUILDERS[buildername]

  # Set up a named cache so runhooks doesn't redownload everything on each run.
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)

  with api.context(cwd=solution_path):
    ConfigureChromiumBuilder(api, recipe_config)

  # Since disk lacks in Mac, we need to remove files before build.
  # In check_different_build_dirs, only the .2 build dir exists here.
  for ext in '12':
    p = str(api.chromium.output_dir).rstrip('\\/') + '.' + ext
    api.file.rmtree('rmtree %s' % p, p)

  targets = recipe_config['targets']

  api.chromium.ensure_goma()
  with api.context(cwd=solution_path):
    api.chromium.runhooks()

  # Do a first build and move the build artifact to the temp directory.
  builder_id = chromium.BuilderId.create_for_group(
      api.builder_group.for_current, buildername)
  api.chromium.mb_gen(builder_id, phase='goma', recursive_lookup=True)

  raw_result = api.chromium.compile(
      targets, name='Goma build', use_goma_module=True)
  if raw_result.status != common_pb.SUCCESS:
    return raw_result

  # Do the second build and move the build artifact to the temp directory.
  build_dir, target = None, None

  api.chromium.mb_gen(
      builder_id, build_dir=build_dir, phase='reclient', recursive_lookup=True)

  raw_result = api.chromium.compile(
      targets,
      name='Reclient build',
      use_goma_module=False,
      use_reclient=True,
      target=target)
  if raw_result.status != common_pb.SUCCESS:
    return raw_result


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  builder_group = 'chromium.swarm'
  for buildername in COMPARISON_BUILDERS:
    test_name = 'full_%s_%s' % (_sanitize_nonalpha(builder_group),
                                _sanitize_nonalpha(buildername))
    yield api.test(
        test_name,
        api.chromium.ci_build(builder_group=builder_group, builder=buildername),
        api.platform(COMPARISON_BUILDERS[buildername]['platform'], 64),
        api.properties(
            buildername=buildername, buildnumber=571, configuration='Release'),
        api.post_process(post_process.StatusSuccess),
        api.post_process(post_process.DropExpectation),
    )

  yield api.test(
      'first_build_compile_fail',
      api.chromium.ci_build(
          builder_group=builder_group, builder='Comparison Linux (reclient)'),
      api.properties(
          buildername='Comparison Linux (reclient)', buildnumber=571),
      api.platform(
          COMPARISON_BUILDERS['Comparison Linux (reclient)']['platform'], 64),
      api.properties(configuration='Release'),
      api.step_data('Goma build', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'second_build_compile_fail',
      api.chromium.ci_build(
          builder_group=builder_group, builder='Comparison Linux (reclient)'),
      api.properties(
          buildername='Comparison Linux (reclient)', buildnumber=571),
      api.platform(
          COMPARISON_BUILDERS['Comparison Linux (reclient)']['platform'], 64),
      api.properties(configuration='Release'),
      api.step_data('Reclient build', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
