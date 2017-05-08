# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/properties',
  'syzygy',
]


def RunSteps(api):
  api.gclient.set_config(api.properties.get('gclient_config', 'chromium'))
  api.chromium.set_config(api.properties.get('chromium_config', 'chromium'))
  api.syzygy.set_config(api.properties.get('syzygy_config', 'syzygy'))


def GenTests(api):
  yield (
      api.test('kasko_official') +
      api.properties(
          gclient_config='kasko_official',
          chromium_config='kasko_official',
          syzygy_config='kasko_official') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('syzygy_x64') +
      api.properties(
          gclient_config='syzygy_x64',
          chromium_config='syzygy_x64',
          syzygy_config='syzygy_x64') +
      api.post_process(post_process.DropExpectation)
  )
