# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_tests',
  'recipe_engine/json',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
]


def RunSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  use_goma_module = api.properties.get('use_goma_module', False)
  out_dir = api.properties.get('out_dir', None)
  failfast = api.properties.get('failfast', False);
  ninja_confirm_noop = api.properties.get('ninja_confirm_noop', False)

  bot_config = api.chromium_tests.create_bot_config_object(
      mastername, buildername)
  api.chromium_tests.configure_build(bot_config)

  if failfast:
    api.chromium.apply_config('goma_failfast')

  if ninja_confirm_noop:
    api.chromium.apply_config('ninja_confirm_noop')

  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)

  api.chromium.run_mb(mastername, buildername, use_goma=True,
                      android_version_code=3,
                      android_version_name="example")

  env = {}
  api.chromium.compile(
      targets=['All'], out_dir=out_dir,
      use_goma_module=use_goma_module,
      env=env)


def GenTests(api):
  yield api.test('basic_out_dir') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      out_dir='/tmp',
  )

  yield api.test('basic_out_dir_without_compile_py') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      out_dir='/tmp',
  )

  yield api.test('basic_out_dir_with_goma_module') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      use_goma_module=True,
      out_dir='/tmp',
  )

  yield api.test('basic_no_out_dir_with_goma_module') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      bot_id='build1-a1',
      buildnumber='77457',
      use_goma_module=True,
  )

  yield (api.test('basic_out_dir_goma_module_build_failure') +
         api.properties(
             mastername='chromium.linux',
             buildername='Android Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             failfast=True,
         ) + api.step_data('compile', retcode=1) +
         api.override_step_data(
             'postprocess_for_goma.goma_jsonstatus',
             stdout=api.json.output({
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
             mastername='chromium.linux',
             buildername='Android Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=False,
         ) + api.step_data('compile', retcode=1))

  yield (api.test('basic_out_dir_ninja_no_op_failure') +
         api.properties(
             mastername='chromium.linux',
             buildername='Android Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             ninja_confirm_noop=True,
         ) + api.override_step_data(
             'compile confirm no-op',
             stdout=api.raw_io.output(
                 "ninja explain: chrome is dirty\n")))

  yield (api.test('basic_out_dir_goma_module_start_failure') +
         api.properties(
             mastername='chromium.linux',
             buildername='Android Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             failfast=True,
         ) + api.step_data('preprocess_for_goma.start_goma', retcode=1) +
         api.override_step_data(
             'preprocess_for_goma.goma_jsonstatus',
             stdout=api.json.output({
                 'notice': [
                     {
                         "compile_error": "COMPILER_PROXY_UNREACHABLE",
                     },
                 ],
             })))

  yield (api.test('basic_out_dir_goma_module_ping_failure') +
         api.properties(
             mastername='chromium.linux',
             buildername='Android Builder (dbg)',
             bot_id='build1-a1',
             buildnumber='77457',
             out_dir='/tmp',
             use_goma_module=True,
             failfast=True,
         ) + api.step_data('preprocess_for_goma.start_goma', retcode=1) +
         api.override_step_data(
             'preprocess_for_goma.goma_jsonstatus',
             stdout=api.json.output({
                 'notice': [
                     {
                         'infra_status': {
                             'ping_status_code': 408,
                         },
                     },
                 ],
             })))
