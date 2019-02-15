# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Launches the gatekeeper."""


DEPS = [
  'depot_tools/infra_paths',
  'gatekeeper',
  'recipe_engine/path',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.gatekeeper.set_config('basic')
  api.gatekeeper.c.use_new_logic = True

  api.gatekeeper(
    api.repo_resource('scripts', 'slave', 'gatekeeper.json'),
    api.repo_resource('scripts', 'slave', 'gatekeeper_trees.json'),
  )


def GenTests(api):
  yield (
    api.test('basic')
    + api.properties.generic(
        buildername='Chromium Gatekeeper', path_config='kitchen')
    + api.step_data(
      'reading gatekeeper_trees.json',
      api.gatekeeper.fake_test_data(),
    )
  )

  yield (
    api.test('keep_going')
    + api.properties.generic(
        buildername='Chromium Gatekeeper', path_config='kitchen')
    + api.step_data(
      'reading gatekeeper_trees.json',
      api.gatekeeper.fake_test_data(),
    )
    + api.step_data('gatekeeper: chromium', retcode=1)
  )

  whitelist_data = api.gatekeeper.fake_test_json()
  whitelist_data['blink']['masters'][
      'https://build.chromium.org/p/chromium.webkit'] = ['foobar', 'coolbar']

  yield (
    api.test('whitelist_config')
    + api.properties.generic(
        buildername='Chromium Gatekeeper', path_config='kitchen')
    + api.step_data(
        'reading gatekeeper_trees.json',
        api.gatekeeper.fake_test_data(whitelist_data)
    )
  )

  yield (
    api.test('production_data')
    + api.properties.generic(
        buildername='Chromium Gatekeeper', path_config='kitchen')
    + api.step_data(
      'reading gatekeeper_trees.json',
      api.gatekeeper.production_data(),
    )
  )
