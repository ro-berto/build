# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe to compare builds with different reclient configurations.

"""

from recipe_engine import post_process
from recipe_engine.engine_types import freeze
from recipe_engine.recipe_api import Property
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium

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
    'recipe_engine/step',
    'reclient',
]

COMPARISON_BUILDERS = freeze({
    'Comparison Linux (reclient vs reclient remote links)': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'chromium_apply_config': [
            'mb', 'goma_enable_cache_silo', 'goma_large_cache_file'
        ],
        'gclient_apply_config': ['enable_reclient', 'reclient_test'],
        'platform': 'linux',
        'targets': ['all'],
    },
})


def configure_chromium_builder(api, recipe_config):
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

  # Checkout chromium.
  api.chromium_checkout.ensure_checkout()


def RunSteps(api):
  buildername = api.buildbucket.builder_name
  recipe_config = COMPARISON_BUILDERS[buildername]

  # Set up a named cache so runhooks doesn't redownload everything on each run.
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)

  with api.context(cwd=solution_path):
    configure_chromium_builder(api, recipe_config)

  base_out_dir = str(api.chromium.output_dir).rstrip('\\/')

  out_dirs = [base_out_dir] + [base_out_dir + '.' + ext for ext in '12']

  # Clear output directories for build
  clean_output_dirs(api, out_dirs)

  targets = recipe_config['targets']

  api.chromium.ensure_toolchains()
  with api.context(cwd=solution_path):
    api.chromium.runhooks()
  try:
    # Do first reclient build .1 out directory
    target = '%s.1' % api.chromium.c.build_config_fs
    build_dir = '//out/%s' % target

    builder_id = chromium.BuilderId.create_for_group(
        api.builder_group.for_current, buildername)
    api.chromium.mb_gen(
        builder_id, build_dir=build_dir, phase='build1', recursive_lookup=True)

    raw_result = api.chromium.compile(
        targets,
        name='Build 1',
        use_goma_module=False,
        use_reclient=True,
        target=target)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result

    # Clear output directories for build
    clean_output_dirs(api, out_dirs)

    # Do second reclient build in .2 out directory
    target = '%s.2' % api.chromium.c.build_config_fs
    build_dir = '//out/%s' % target

    api.chromium.mb_gen(
        builder_id, build_dir=build_dir, phase='build2', recursive_lookup=True)

    raw_result = api.chromium.compile(
        targets,
        name='Build 2',
        use_goma_module=False,
        use_reclient=True,
        target=target)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result
  finally:
    # Always clean output directories after build
    clean_output_dirs(api, out_dirs)


def clean_output_dirs(api, out_dirs):
  with api.step.nest('clean_output_dirs'):
    for out_dir in out_dirs:
      api.file.rmtree('rmtree %s' % out_dir, out_dir)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  builder_group = 'chromium.swarm'
  for buildername in COMPARISON_BUILDERS:
    test_name = 'full_%s_%s' % (_sanitize_nonalpha(builder_group),
                                _sanitize_nonalpha(buildername))
    mac_test_props = {
        'xcode_build_version': '12345',
        'configs': ['mac_toolchain']
    } if COMPARISON_BUILDERS[buildername]['platform'] == 'mac' else {}
    yield api.test(
        test_name,
        api.chromium.ci_build(builder_group=builder_group, builder=buildername),
        api.reclient.properties(),
        api.platform(COMPARISON_BUILDERS[buildername]['platform'], 64),
        api.properties(
            buildername=buildername,
            buildnumber=571,
            configuration='Release',
            **mac_test_props),
        api.post_process(post_process.StatusSuccess),
        api.post_process(post_process.DropExpectation),
    )

  yield api.test(
      'first_build_compile_fail',
      api.chromium.ci_build(
          builder_group=builder_group,
          builder='Comparison Linux (reclient vs reclient remote links)'),
      api.reclient.properties(),
      api.properties(
          buildername='Comparison Linux (reclient vs reclient remote links)',
          buildnumber=571),
      api.platform(
          COMPARISON_BUILDERS[
              'Comparison Linux (reclient vs reclient remote links)']
          ['platform'], 64),
      api.properties(configuration='Release'),
      api.step_data('Build 1', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'second_build_compile_fail',
      api.chromium.ci_build(
          builder_group=builder_group,
          builder='Comparison Linux (reclient vs reclient remote links)'),
      api.reclient.properties(),
      api.properties(
          buildername='Comparison Linux (reclient vs reclient remote links)',
          buildnumber=571),
      api.platform(
          COMPARISON_BUILDERS[
              'Comparison Linux (reclient vs reclient remote links)']
          ['platform'], 64),
      api.properties(configuration='Release'),
      api.step_data('Build 2', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
