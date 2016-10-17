# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_tests',
  'recipe_engine/platform',
  'recipe_engine/properties',
]

def RunSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  use_goma_module = api.properties.get('use_goma_module', False)
  out_dir = api.properties.get('out_dir', None)
  bot_config = api.chromium_tests.create_bot_config_object(
      mastername, buildername)
  api.chromium_tests.configure_build(bot_config)
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)

  if api.platform.is_win:
    api.chromium.run_mb(mastername, buildername, use_goma=True)
  else:
    api.chromium.run_mb(mastername, buildername, use_goma=True,
                        android_version_code=3,
                        android_version_name="example")

  env = {}
  if api.properties.get('goma_disable', False):
    env.update({'GOMA_DISABLED': 'true'})

  api.chromium.compile(targets=['All'], out_dir=out_dir,
                       use_goma_module=use_goma_module,
                       env=env)

def GenTests(api):
  yield api.test('basic_out_dir') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      slavename='build1-a1',
      buildnumber='77457',
      out_dir='/tmp',
  )

  yield api.test('basic_out_dir_with_goma_module') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      slavename='build1-a1',
      buildnumber='77457',
      use_goma_module=True,
      out_dir='/tmp',
  )

  yield api.test('basic_no_out_dir_with_goma_module') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      slavename='build1-a1',
      buildnumber='77457',
      use_goma_module=True,
  )

  yield (api.test('basic_no_out_dir_with_goma_module_goma_disabled_win') +
         api.properties(
             mastername='chromium.win',
             buildername='Win Builder',
             slavename='build1-a1',
             buildnumber='77457',
             use_goma_module=True,
             goma_disable=True,
         ) + api.platform.name('win'))
