# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

from recipe_engine import post_process

def RunSteps(api):
  use_goma_module = api.properties.get('use_goma_module', False)
  use_reclient = api.properties.get('use_reclient', False)
  out_dir = api.properties.get('out_dir', None)
  failfast = api.properties.get('failfast', False)
  configs = api.properties.get('configs', [])

  with api.chromium.chromium_layout():
    builder_id, builder_config = (
        api.chromium_tests_builder_config.lookup_builder())
    api.chromium_tests.configure_build(builder_config)

    api.chromium.get_build_target_arch()

    if failfast:
      api.chromium.apply_config('goma_failfast')

    for config in configs:
      api.chromium.apply_config(config)

    api.chromium_tests.prepare_checkout(builder_config)

    mb_config_path = api.properties.get('mb_config_path')

    api.chromium.mb_gen(
        builder_id,
        use_goma=True,
        mb_config_path=mb_config_path,
        android_version_code=3,
        android_version_name="example")

    return api.chromium.compile(
        targets=['All'],
        out_dir=out_dir,
        use_goma_module=use_goma_module,
        use_reclient=use_reclient)


def GenTests(api):
  yield api.test(
      'basic_out_dir',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(out_dir='/tmp'),
  )

  yield api.test(
      'basic_out_dir_with_custom_mb_config',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          mb_config_path='/custom/config.pyl',
      ),
  )

  yield api.test(
      'basic_out_dir_without_compile_py',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(out_dir='/tmp'),
  )

  yield api.test(
      'basic_out_dir_with_goma_module',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          use_goma_module=True,
          out_dir='/tmp',
      ),
  )

  yield api.test(
      'basic_out_dir_with_reclient',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ), api.properties(
          use_reclient=True,
          out_dir='/tmp',
      ),
      api.post_check(lambda check, steps: check('RBE_server_address' in steps[
          'compile'].env)), api.post_process(post_process.DropExpectation))

  yield api.test(
      'basic_no_out_dir_with_goma_module',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(use_goma_module=True),
  )

  yield api.test(
      'goma_module_with_cache_silo',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Builder',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(use_goma_module=True, configs=['goma_enable_cache_silo']),
      api.post_check(lambda check, steps: check(steps['compile'].env[
          'RBE_cache_silo'] == 'Linux Builder')),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'basic_out_dir_goma_module_build_failure',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          use_goma_module=True,
          failfast=True,
      ),
      api.step_data('compile', retcode=1),
      api.step_data(
          'postprocess_for_goma.goma_jsonstatus',
          api.json.output(
              data={
                  'notice': [{
                      'infra_status': {
                          'ping_status_code': 200,
                          'num_user_error': 1,
                      },
                  },],
              })),
  )

  yield api.test(
      'basic_out_dir_ninja_build_failure',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          use_goma_module=False,
      ),
      api.step_data('compile', retcode=1),
  )

  yield api.test(
      'basic_out_dir_ninja_no_op_failure',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          use_goma_module=True,
      ),
      api.override_step_data(
          'compile confirm no-op',
          stdout=api.raw_io.output("ninja explain: chrome is dirty\n")),
  )

  yield api.test(
      'basic_out_dir_goma_module_start_failure',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          use_goma_module=True,
          failfast=True,
      ),
      api.step_data('preprocess_for_goma.start_goma', retcode=1),
      api.step_data(
          'preprocess_for_goma.goma_jsonstatus',
          api.json.output(data={
              'notice': [{
                  "compile_error": "COMPILER_PROXY_UNREACHABLE",
              },],
          })),
  )

  yield api.test(
      'basic_out_dir_goma_module_ping_failure',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          use_goma_module=True,
          failfast=True,
      ),
      api.step_data('preprocess_for_goma.start_goma', retcode=1),
      api.step_data(
          'preprocess_for_goma.goma_jsonstatus',
          api.json.output(data={
              'notice': [{
                  'infra_status': {
                      'ping_status_code': 408,
                  },
              },],
          })),
  )

  yield api.test(
      'mac_basic',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.mac',
          builder='Mac Builder',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          target_platform='mac',
      ),
  )

  yield api.test(
      'mac_toolchain',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.mac',
          builder='Mac Builder',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          target_platform='mac',
          configs=['mac_toolchain'],
      ),
  )

  yield api.test(
      'mac_toolchain_properties',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.mac',
          builder='Mac Builder',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          out_dir='/tmp',
          target_platform='mac',
          configs=['mac_toolchain'],
          xcode_build_version='12345',
      ),
  )

  yield api.test(
      'chromeos_simplechrome',
      api.platform('linux', 64),
      api.chromium.ci_build(
          builder_group='chromium.chromiumos',
          builder='chromeos-amd64-generic-rel',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(out_dir='/tmp'),
  )

  yield api.test(
      'basic_out_dir_with_goma_cache_silo',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Android arm Builder (dbg)',
          bot_id='build1-a1',
          build_number=77457,
      ),
      api.properties(
          **{
              'use_goma_module': True,
              'out_dir': '/tmp',
              '$build/chromium': {
                  'goma_cache_silo': True,
              },
          }),
      api.post_check(lambda check, steps: check(steps['compile'].env[
          'RBE_cache_silo'] == 'Android arm Builder (dbg)')),
      api.post_process(post_process.DropExpectation),
  )
