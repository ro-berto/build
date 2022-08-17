# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_android',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/path',
    'recipe_engine/step',
]


def RunSteps(api):
  if api.properties['denylist_exists']:
    api.path.mock_add_paths(api.chromium_android.denylist_file)
  api.chromium_android._devices = ['serial1', 'serial2']
  available_devices = api.chromium_android.non_denylisted_devices()
  api.step('print devices', ['echo'] + available_devices)


def GenTests(api):
  yield api.test(
      'denylisted_device',
      api.properties(denylist_exists=True),
      api.override_step_data('read_denylist_file',
                             api.json.output({'serial1': {}})),
  )
  yield api.test(
      'no_denylist',
      api.properties(denylist_exists=False),
  )
