# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Launches the gatekeeper."""


DEPS = [
  'depot_tools/infra_paths',
  'gatekeeper',
  'recipe_engine/path',
]


def RunSteps(api):
  api.gatekeeper.set_config('basic')
  api.gatekeeper.c.use_new_logic = True

  api.gatekeeper(
    api.path['build'].join('scripts', 'slave', 'gatekeeper.json'),
    api.path['build'].join('scripts', 'slave', 'gatekeeper_trees.json'),
  )


def GenTests(api):
  yield (
    api.test('basic')
    + api.step_data(
      'reading gatekeeper_trees.json',
      api.gatekeeper.fake_test_data(),
    )
  )

  yield (
    api.test('keep_going')
    + api.step_data(
      'reading gatekeeper_trees.json',
      api.gatekeeper.fake_test_data(),
    )
    + api.step_data('gatekeeper: chromium', retcode=1)
  )

  bad_data = api.gatekeeper.fake_test_json()
  bad_data['blink']['masters'][
      'https://build.chromium.org/p/chromium.webkit'].append('foobar')

  yield (
    api.test('bad_config')
    + api.step_data(
        'reading gatekeeper_trees.json',
        api.gatekeeper.fake_test_data(bad_data)
    )
  )
