# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

DEPS = [
  'chromium',
  'chromium_tests',
  'recipe_engine/json',
  'recipe_engine/platform',
 'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
]

from recipe_engine import post_process

def RunSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  use_goma_module = api.properties.get('use_goma_module', False)
  out_dir = api.properties.get('out_dir', None)
  failfast = api.properties.get('failfast', False);
  ninja_confirm_noop_warn = api.properties.get('ninja_confirm_noop_warn', False)
  configs = api.properties.get('configs', [])

  with api.chromium.chromium_layout():
    bot_config = api.chromium_tests.create_bot_config_object(
        [api.chromium_tests.create_bot_id(mastername, buildername)])
    api.chromium_tests.configure_build(bot_config)

    if failfast:
      api.chromium.apply_config('goma_failfast')

    if ninja_confirm_noop_warn:
      api.chromium.apply_config('ninja_confirm_noop_warn')

    for config in configs:
      api.chromium.apply_config(config)

    api.chromium_tests.prepare_checkout(bot_config)

    mb_config_path = api.properties.get('mb_config_path')

    api.chromium.mb_gen(mastername, buildername, use_goma=True,
                        mb_config_path=mb_config_path,
                        android_version_code=3,
                        android_version_name="example")

    api.chromium.compile(
        targets=['All'], out_dir=out_dir,
        use_goma_module=use_goma_module)


def GenTests(api):
  yield api.test('basic_out_dir') + api.properties(
      mastername='chromium.android',
      buildername='Android arm Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      out_dir='/tmp',
  )

  yield api.test('basic_out_dir_with_custom_mb_config') + api.properties(
      mastername='chromium.android',
      buildername='Android arm Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      out_dir='/tmp',
      mb_config_path='/custom/config.pyl',
  )

  yield api.test('basic_out_dir_without_compile_py') + api.properties(
      mastername='chromium.android',
      buildername='Android arm Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      out_dir='/tmp',
  )

  yield api.test('basic_out_dir_with_goma_module') + api.properties(
      mastername='chromium.android',
      buildername='Android arm Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      use_goma_module=True,
      out_dir='/tmp',
  )

  yield api.test('basic_no_out_dir_with_goma_module') + api.properties(
      mastername='chromium.android',
      buildername='Android arm Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      use_goma_module=True,
  )

  yield (api.test('basic_out_dir_goma_module_build_failure') +
         api.properties(
             mastername='chromium.android',
             buildername='Android arm Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             failfast=True,
         ) + api.step_data('compile', retcode=1) +
         api.step_data(
             'postprocess_for_goma.goma_jsonstatus',
             api.json.output(
                 data={
                     'notice': [
                         {
                             'infra_status': {
                                 'ping_status_code': 200,
                                 'num_user_error': 1,
                             },
                         },
                     ],
                 })))

  yield (api.test('basic_out_dir_ninja_build_failure') +
         api.properties(
             mastername='chromium.android',
             buildername='Android arm Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=False,
         ) + api.step_data('compile', retcode=1))

  yield (api.test('basic_out_dir_ninja_no_op_failure') +
         api.properties(
             mastername='chromium.android',
             buildername='Android arm Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             ninja_confirm_noop=True,
         ) + api.override_step_data(
             'compile confirm no-op',
             stdout=api.raw_io.output(
                 "ninja explain: chrome is dirty\n")))

  yield (api.test('basic_out_dir_ninja_no_op_warning') +
         api.properties(
             mastername='chromium.android',
             buildername='Android arm Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             ninja_confirm_noop_warn=True,
         ) + api.override_step_data(
             'compile confirm no-op',
             stdout=api.raw_io.output(
                 "ninja explain: chrome is dirty\n")) +
         api.post_process(post_process.AnnotationContains,
                          'compile confirm no-op', ['confirm no-op failure']) +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (api.test('basic_out_dir_goma_module_start_failure') +
         api.properties(
             mastername='chromium.android',
             buildername='Android arm Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             failfast=True,
         ) + api.step_data('preprocess_for_goma.start_goma', retcode=1) +
         api.step_data(
             'preprocess_for_goma.goma_jsonstatus',
             api.json.output(
                 data={
                     'notice': [
                         {
                             "compile_error": "COMPILER_PROXY_UNREACHABLE",
                         },
                     ],
                 })))

  yield (api.test('basic_out_dir_goma_module_ping_failure') +
         api.properties(
             mastername='chromium.android',
             buildername='Android arm Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             failfast=True,
         ) + api.step_data('preprocess_for_goma.start_goma', retcode=1) +
         api.step_data(
             'preprocess_for_goma.goma_jsonstatus',
             api.json.output(
                 data={
                     'notice': [
                         {
                             'infra_status': {
                                 'ping_status_code': 408,
                             },
                         },
                     ],
                 })))

  yield (api.test('mac_basic') +
         api.platform('mac', 64) +
         api.properties(
             mastername='chromium.mac',
             buildername='Mac Builder',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             target_platform='mac',
         )
  )

  yield (api.test('mac_basic_luci') +
         api.platform('mac', 64) +
         api.properties(
             mastername='chromium.mac',
             buildername='Mac Builder',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             target_platform='mac',
         ) +
         api.runtime(is_luci=True, is_experimental=False) +
         api.post_process(Filter('gclient runhooks'))
  )

  yield (api.test('mac_toolchain') +
         api.platform('mac', 64) +
         api.properties(
             mastername='chromium.mac',
             buildername='Mac Builder',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             target_platform='mac',
             configs=['mac_toolchain'],
         )
  )

  yield (api.test('chromeos_simplechrome') +
         api.platform('linux', 64) +
         api.properties(
             mastername='chromium.chromiumos',
             buildername='chromeos-amd64-generic-rel',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
         )
  )
