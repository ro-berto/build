# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe to measure build step performance.
   See also go/build-perf-builder
"""

from recipe_engine import post_process
from recipe_engine.engine_types import freeze
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'builder_group',
    'chromium',
    'chromium_android',
    'chromium_checkout',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'reclient',
]

BUILD_PERF_BUILDERS = freeze({
    'Build Perf Linux': {
        'chromium_config': 'chromium',
        'chromium_apply_config': ['mb'],
        'gclient_config': 'chromium',
        'gclient_apply_config': ['enable_reclient'],
        'platform': 'linux',
        'targets': [['all'], ['chrome']],
    },
    'Build Perf Android': {
        'chromium_config': 'android',
        'chromium_apply_config': ['mb'],
        'chromium_config_kwargs': {
            'BUILD_CONFIG': 'Release',
            'TARGET_BITS': 64,
            'TARGET_PLATFORM': 'android',
        },
        'gclient_config': 'chromium',
        'gclient_apply_config': ['android', 'enable_reclient'],
        'android_config': 'main_builder',
        'platform': 'linux',
        'targets': [['all'], ['chrome_public_apk']],
    },
    'Build Perf Windows': {
        'chromium_config': 'chromium',
        'chromium_apply_config': ['mb'],
        'gclient_config': 'chromium',
        'gclient_apply_config': ['enable_reclient'],
        'platform': 'win',
        'targets': [['all'], ['chrome']],
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

  if recipe_config.get('android_config'):
    api.chromium_android.configure_from_properties(
        recipe_config.get('android_config'),
        **recipe_config.get('chromium_config_kwargs', {}))

  # Checkout chromium.
  api.chromium_checkout.ensure_checkout()


def _rm_build_dir(api):
  api.file.rmtree('rmtree %s' % str(api.chromium.output_dir),
                  str(api.chromium.output_dir))


def Compile(api, targets):
  buildername = api.buildbucket.builder_name
  builder_id = chromium.BuilderId.create_for_group(
      api.builder_group.for_current, buildername)
  phase = 'build %s' % ','.join(targets)
  api.chromium.mb_gen(builder_id, phase=phase, recursive_lookup=True)
  try:
    return api.chromium.compile(
        targets,
        name=phase.capitalize(),
        use_goma_module=False,
        use_reclient=True)
  finally:
    _rm_build_dir(api)


def RunSteps(api):
  buildername = api.buildbucket.builder_name
  recipe_config = BUILD_PERF_BUILDERS[buildername]

  # Set up a named cache so runhooks doesn't redownload everything on each run.
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)

  with api.context(cwd=solution_path):
    ConfigureChromiumBuilder(api, recipe_config)

  with api.context(cwd=solution_path):
    api.chromium.runhooks()

  _rm_build_dir(api)

  for targets in recipe_config['targets']:
    # TODO(b/234807316): specify remote_accept_cache=false.
    raw_result = Compile(api, targets)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result

    raw_result = Compile(api, targets)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  builder_group = 'chromium.fyi'
  for buildername, recipe_config in BUILD_PERF_BUILDERS.items():
    test_name = 'full_%s_%s' % (_sanitize_nonalpha(builder_group),
                                _sanitize_nonalpha(buildername))
    yield api.test(
        test_name,
        api.chromium.ci_build(builder_group=builder_group, builder=buildername),
        api.reclient.properties(),
        api.platform(recipe_config['platform'], 64),
        api.properties(
            buildername=buildername, buildnumber=571, configuration='Release'),
        api.post_process(post_process.StatusSuccess),
    )

  buildername = 'Build Perf Linux'
  for step in [
      'Build all', 'Build all (2)', 'Build chrome', 'Build chrome (2)'
  ]:
    yield api.test(
        '%s_compile_fail' % (_sanitize_nonalpha(step)),
        api.chromium.ci_build(builder_group=builder_group, builder=buildername),
        api.reclient.properties(),
        api.properties(buildername=buildername, buildnumber=571),
        api.platform(BUILD_PERF_BUILDERS[buildername]['platform'], 64),
        api.properties(configuration='Release'),
        api.step_data(step, retcode=1),
        api.post_process(post_process.StatusFailure),
        api.post_process(post_process.DropExpectation),
    )
