# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_tests',
  'recipe_engine/properties',
]

def RunSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')

  bot_config = api.chromium_tests.create_bot_config_object(
      mastername, buildername)
  api.chromium_tests.configure_build(bot_config)
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)
  #api.chromium_tests.compile(mastername, buildername, update_step, bot_db,
  #                           out_dir='/tmp')
  api.chromium.compile(targets=['All'], out_dir='/tmp')

def GenTests(api):
  yield api.test('basic_out_dir') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder (dbg)',
      slavename='build1-a1',
      buildnumber='77457',
  )
