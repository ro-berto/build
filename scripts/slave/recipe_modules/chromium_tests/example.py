# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'chromium_tests',
  'json',
  'properties',
]


def GenSteps(api):
  api.chromium.set_config('chromium')
  api.bot_update.ensure_checkout(force=True)
  api.chromium_tests.analyze(['base_unittests'], ['all'], 'foo.json')


def GenTests(api):
  yield (
    api.test('basic') +
    api.properties.tryserver() +
    api.override_step_data('read filter exclusion spec', api.json.output({
        'base': {
          'exclusions': ['f.*'],
        },
        'chromium': {
          'exclusions': [],
        },
     })
    )
  )
